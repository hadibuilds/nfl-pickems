from django.db.models import Window, F, Q
from django.db.models.functions import DenseRank
from django.http import JsonResponse
from django.utils import timezone
from zoneinfo import ZoneInfo

from games.models import Game
from predictions.models import UserSeasonTotals, Top3Snapshot
try:
    from predictions.models import PropBet, CorrectionEvent
except Exception:
    PropBet = None
    CorrectionEvent = None

PACIFIC = ZoneInfo("America/Los_Angeles")

def _slot_for_local_time(dt_local):
    h = dt_local.hour
    if h < 13:
        return "morning"
    if h < 17:
        return "afternoon"
    return "late"


def _current_window_key_pt():
    now_pt = timezone.localtime(timezone.now(), PACIFIC)
    return f"{now_pt.date().isoformat()}:{_slot_for_local_time(now_pt)}"


def _latest_two_snapshots(window_key: str):
    snaps = (
        Top3Snapshot.objects
        .filter(window_key=window_key)
        .order_by("-version")
        .values("version", "created_at", "payload")
    )[:2]
    latest = snaps[0] if snaps else None
    previous = snaps[1] if len(snaps) > 1 else None
    return latest, previous


def _merge_trends(items, latest_snap, previous_snap):
    """
    items: live DB top-3(+ties) [{user_id, ..., rank}, ...]
    latest_snap/past_snap: dicts with payload like {"items":[{user_id, rank, ...}, ...]}
    Returns items with 'trend' and 'rank_change' merged per spec.
    """
    if not latest_snap or not previous_snap:
        return items, None, None  # nothing to compare

    latest_payload = latest_snap.get("payload") or {}
    prev_payload = previous_snap.get("payload") or {}
    prev_rank_by_user = {
        int(row.get("user_id")): int(row.get("rank"))
        for row in (prev_payload.get("items") or [])
        if "user_id" in row and "rank" in row
    }

    merged = []
    for row in items:
        uid = int(row["user_id"])
        if uid not in prev_rank_by_user:
            # new entrant relative to previous snapshot
            row = {**row, "trend": "up", "rank_change": None}
        else:
            before = prev_rank_by_user[uid]
            after = int(row["rank"])
            delta = before - after
            if delta > 0:
                trend = "up"
            elif delta < 0:
                trend = "down"
            else:
                trend = "same"
            row = {**row, "trend": trend, "rank_change": abs(delta)}
        merged.append(row)

    # The trend basis is the window of the snapshots we compared
    last_updated = latest_snap.get("created_at")
    return merged, last_updated, latest_snap.get("version")


def _window_status_debug(window_key: str):
    # Counts for games/props completeness
    try:
        g_qs = Game.objects.filter(window_key=window_key)
        games_total = g_qs.count()
        games_open = g_qs.filter(Q(winner__isnull=True) | Q(winner="")).count()
    except Exception:
        games_total = games_open = None

    props_total = props_open = None
    if PropBet is not None:
        try:
            p_qs = PropBet.objects.filter(window_key=window_key)
            props_total = p_qs.count()
            props_open = p_qs.filter(Q(correct_answer__isnull=True) | Q(correct_answer="")).count()
        except Exception:
            pass

    complete = (
        games_total is not None
        and props_total is not None
        and games_open == 0
        and props_open == 0
    )
    return {
        "window_key": window_key,
        "games": {"total": games_total, "open": games_open},
        "props": {"total": props_total, "open": props_open},
        "complete": bool(complete),
    }


def home_top3_api(request):
    """
    Live Top-3 (+ties) with trend against the most recent snapshot window.
    Behavior mirrors the old predictions.views version:
      - pick the latest snapshot (any window)
      - find the previous snapshot for that same window_key
      - compare ranks to compute trend & rank_change
    """
    # 1) Build live Top-3(+ties) with dense rank and a clean `username` key
    order_by = [
        F("total_points").desc(nulls_last=True),
        F("ml_points").desc(nulls_last=True),
        F("prop_points").desc(nulls_last=True),
        F("user_id").asc(),
    ]
    qs = (
        UserSeasonTotals.objects
        .annotate(rank=Window(expression=DenseRank(), order_by=order_by))
        .order_by(*order_by)
    )

    rows = (
        qs.filter(rank__lte=3)
          .annotate(username=F("user__username"))   # flatten related field
          .values("user_id", "username", "ml_points", "prop_points", "total_points", "rank")
    )
    top3 = [
        {
            "user_id": r["user_id"],
            "username": r["username"],
            "ml_points": r["ml_points"],
            "prop_points": r["prop_points"],
            "total_points": r["total_points"],
            "rank": r["rank"],
        }
        for r in rows
    ]

    # 2) Grab latest snapshot and previous snapshot for the same window_key
    latest = Top3Snapshot.objects.order_by("-created_at").first()
    prev = (
        Top3Snapshot.objects
        .filter(window_key=getattr(latest, "window_key", None))
        .exclude(pk=getattr(latest, "pk", None))
        .order_by("-created_at")
        .first()
    ) if latest else None

    # Helper to read payload items whether it's a list or {"items":[...]}
    def _items(payload):
        if not payload:
            return []
        return payload.get("items") if isinstance(payload, dict) else payload

    # 3) Compute trend & rank_change (or None when no comparison)
    prev_rank = {int(row["user_id"]): int(row["rank"]) for row in _items(getattr(prev, "payload", None))}
    enriched = []
    for row in top3:
        uid, new_rank = int(row["user_id"]), int(row["rank"])
        old_rank = prev_rank.get(uid)
        if old_rank is None:
            trend, rank_change = ("up", None) if prev else (None, None)  # new entrant or no snapshots at all
        elif new_rank < old_rank:
            trend, rank_change = "up", old_rank - new_rank
        elif new_rank > old_rank:
            trend, rank_change = "down", new_rank - old_rank
        else:
            trend, rank_change = "same", 0
        enriched.append({**row, "trend": trend, "rank_change": rank_change})

    return JsonResponse({
        "items": enriched,
        "last_updated": latest.created_at.isoformat() if latest else None,
        "trend_basis_window": latest.window_key if latest else None,
    }, json_dumps_params={"ensure_ascii": False})
