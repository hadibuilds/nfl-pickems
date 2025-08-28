
# analytics/views.py — Consolidated, windowed-first implementation
# Keeps behavior-equivalent endpoints for windowed ranking and trims legacy overlap.
# Safe defaults: if "live_*" overlay isn't available, responses omit those fields (frontend falls back).

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from django.db.models import Count, Sum

from django.contrib.auth import get_user_model
from django.db.models import F, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo
PACIFIC = ZoneInfo("America/Los_Angeles")

# Core models for windowed rankings
from .models import UserWindowCumulative, UserWindowDeltas

# Game/PropBet for window status checks
from games.models import Game, PropBet

# Optional services (used when present)
try:
    from .services.windowed_rankings import (
        process_window,            # (season:int, window_key:str) -> None
        is_window_complete,        # (window_key:str, season:int) -> bool
        get_current_window,        # (season:int) -> dict with {window_key, status, window_seq}
        refresh_materialized_views # () -> None  (optional)
    )
except Exception:  # pragma: no cover - keep endpoints working even if services module moves
    process_window = None
    is_window_complete = None
    get_current_window = None
    refresh_materialized_views = None

User = get_user_model()

SLOT_INDEX = {"morning": 1, "afternoon": 2, "late": 3}

def _clean_window_key(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().strip("/")  # remove any trailing slash you’ve seen in logs

def _seq_from_window_key(window_key: str | None) -> int | None:
    if not window_key:
        return None
    try:
        date_str, slot = window_key.split(":")
        return int(date_str.replace("-", "")) * 10 + SLOT_INDEX[slot]
    except Exception:
        return None

def _fallback_window_standings(season: int, window_key: str):
    """
    Compute per-window standings on the fly when aggregates are missing.
    ML correct = +1, Prop correct = +2. Dense rank by total_points.
    """
    games_done = Game.objects.filter(
        season=season, window_key=window_key, winner__isnull=False
    ).values_list("id", flat=True)

    props_done = PropBet.objects.filter(
        game__season=season, game__window_key=window_key, correct_answer__isnull=False
    ).values_list("id", flat=True)

    # If nothing is actually done, return empty (the status logic will show in-progress/upcoming)
    if not games_done and not props_done:
        return []

    # Aggregate points
    agg = defaultdict(lambda: {"ml_points": 0, "prop_points": 0})

    # Moneyline (+1 each correct)
    for row in (
        Prediction.objects
        .filter(is_correct=True, game_id__in=list(games_done))
        .values("user_id")
        .annotate(cnt=Count("id"))
    ):
        agg[row["user_id"]]["ml_points"] = row["cnt"]

    # Props (+2 each correct)
    for row in (
        PropBetPrediction.objects
        .filter(is_correct=True, prop_bet_id__in=list(props_done))
        .values("user_id")
        .annotate(cnt=Count("id"))
    ):
        agg[row["user_id"]]["prop_points"] = row["cnt"] * 2

    if not agg:
        return []

    users = {u.id: u for u in User.objects.filter(id__in=agg.keys())}

    rows = []
    for uid, pts in agg.items():
        total = pts["ml_points"] + pts["prop_points"]
        rows.append({
            "user_id": uid,
            "username": getattr(users.get(uid), "username", f"user:{uid}"),
            "ml_points": pts["ml_points"],
            "prop_points": pts["prop_points"],
            "total_points": total,
            # fields the frontend may already expect
            "rank_before": None,
            "rank_change": None,
            "trend": None,
            "display_trend": None,
        })

    # Dense rank 1,2,2,3...
    rows.sort(key=lambda r: (-r["total_points"], r["username"]))
    rank = 0
    last_total = None
    for i, r in enumerate(rows, 1):
        if r["total_points"] != last_total:
            rank = i
            last_total = r["total_points"]
        r["rank"] = rank

    return rows


def _clean_key(v): 
    return v.strip().strip("/") if v else None

def _seq_from_key(wk: str | None) -> int | None:
    if not wk: 
        return None
    try:
        d, s = wk.split(":")
        return int(d.replace("-", "")) * 10 + SLOT_INDEX[s]
    except Exception:
        return None

def _dense_ranks(score_map: dict[int, int]) -> dict[int, int]:
    """Return dense ranks (1,2,2,3...) for a {user_id: score} map, highest first."""
    # Sort by score desc then user_id to make ties deterministic
    ordered = sorted(score_map.items(), key=lambda kv: (-kv[1], kv[0]))
    ranks, rank, prev = {}, 0, None
    for i, (uid, sc) in enumerate(ordered, 1):
        if sc != prev:
            rank = i
            prev = sc
        ranks[uid] = rank
    return ranks

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLOT_INDEX = {"morning": 1, "afternoon": 2, "late": 3}
def _seq_from_window_key(window_key: str) -> Optional[int]:
    try:
        date_str, slot = window_key.split(":")
        return int(date_str.replace("-", "")) * 10 + SLOT_INDEX[slot]
    except Exception:
        return None

def parse_int(value, default=None, minimum=None, maximum=None):
    try:
        i = int(value)
        if minimum is not None and i < minimum:
            i = minimum
        if maximum is not None and i > maximum:
            i = maximum
        return i
    except (TypeError, ValueError):
        return default

def get_current_season() -> int:
    # Simple heuristic: use year of "now" in PT; override via ?season=
    now = timezone.now().astimezone(PACIFIC)
    return now.year


def resolve_latest_window(season: int) -> Optional[Tuple[str, int]]:
    row = (
        UserWindowCumulative.objects
        .filter(season=season)
        .order_by("-window_seq")
        .values("window_key", "window_seq")
        .first()
    )
    if row:
        return row["window_key"], row["window_seq"]

    # Fallback: find a window from scheduled games
    g = (
        Game.objects
        .filter(season=season)
        .exclude(window_key__isnull=True)
        .exclude(window_key__exact="")
        .order_by("-start_time")
        .values("window_key")
        .first()
    )
    if not g:
        return None
    seq = _seq_from_window_key(g["window_key"])
    if seq is None:
        return None
    return g["window_key"], seq


def compute_window_status(season: int, window_key: str) -> str:
    """
    "complete" if all games+props resolved,
    "in_progress" if not complete and now >= earliest kickoff,
    else "upcoming".
    Uses services.is_window_complete() when available; otherwise queries Game/PropBet.
    """
    if is_window_complete:
        try:
            if is_window_complete(window_key, season):
                return "complete"
        except Exception:
            pass

    games = Game.objects.filter(season=season, window_key=window_key)
    props = PropBet.objects.filter(game__season=season, game__window_key=window_key)

    if not games.exists():
        return "upcoming"  # nothing scheduled -> treat as not started

    # complete?
    if not games.filter(winner__isnull=True).exists() and not props.filter(correct_answer__isnull=True).exists():
        return "complete"

    # earliest kickoff
    earliest = games.order_by("start_time").values_list("start_time", flat=True).first()
    if earliest:
        st = earliest
        if timezone.is_naive(st):
            st = timezone.make_aware(st, PACIFIC)
        if timezone.now() >= st:
            return "in_progress"
    return "upcoming"


def serialize_cume_row(row: Dict[str, Any], include_user: bool = True) -> Dict[str, Any]:
    """Normalize a UserWindowCumulative values() row to API schema."""
    out = {
        "user_id": row["user_id"],
        "username": row["user__username"] if include_user else row.get("username"),
        "rank": row["rank_after"],
        "total_points": row["cume_total_after"],
        "rank_before": row.get("rank_before"),
        "rank_change": row.get("rank_change", 0),
        "trend": row.get("trend", "same"),
        "display_trend": row.get("display_trend", True),
    }
    return out

# ---------------------------------------------------------------------------
# Windowed endpoints (primary)
# ---------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_windowed_standings(request):
    season = parse_int(request.GET.get("season"), default=get_current_season())
    window_key = _clean_key(request.GET.get("window_key"))
    if not window_key:
        latest = resolve_latest_window(season)
        if latest:
            window_key = latest[0]

    window_seq = _seq_from_key(window_key)

    # ---------- AGGREGATE VIA DELTAS (no rank_* fields on the model) ----------
    # Window points (this window only)
    win_rows = list(
        UserWindowDeltas.objects
        .filter(season=season, window_key=window_key)
        .values("user_id")
        .annotate(
            window_points=Sum("total_delta"),
            ml_points=Sum("ml_points_delta"),
            prop_points=Sum("prop_points_delta"),
        )
    )

    if win_rows:
        user_ids = {r["user_id"] for r in win_rows}

        # Cumulative totals BEFORE and AFTER this window
        before_rows = UserWindowDeltas.objects.filter(
            season=season, window_seq__lt=window_seq
        ).values("user_id").annotate(total_before=Sum("total_delta"))

        after_rows = UserWindowDeltas.objects.filter(
            season=season, window_seq__lte=window_seq
        ).values("user_id").annotate(total_after=Sum("total_delta"))

        # Build maps
        total_before = {r["user_id"]: (r["total_before"] or 0) for r in before_rows}
        total_after  = {r["user_id"]: (r["total_after"] or 0) for r in after_rows}
        # Ensure every user in this window has an entry (default 0)
        for uid in user_ids:
            total_before.setdefault(uid, 0)
            total_after.setdefault(uid, 0)

        # Dense ranks
        rank_before = _dense_ranks(total_before)
        rank_after  = _dense_ranks(total_after)

        # usernames
        users = {u.id: u for u in User.objects.filter(id__in=user_ids)}

        standings = []
        for r in win_rows:
            uid = r["user_id"]
            rb = rank_before.get(uid)
            ra = rank_after.get(uid)
            # positive rank_change means moved UP (e.g., 5 -> 3 => +2)
            rank_change = (rb - ra) if (rb is not None and ra is not None) else None
            trend = "up" if (rank_change and rank_change > 0) else ("down" if (rank_change and rank_change < 0) else "flat")

            standings.append({
                "user_id": uid,
                "username": getattr(users.get(uid), "username", f"user:{uid}"),
                "ml_points": int(r.get("ml_points") or 0),
                "prop_points": int(r.get("prop_points") or 0),
                "total_points": int(r.get("window_points") or 0),  # points earned this window
                "rank_before": rb,
                "rank_change": rank_change,
                "trend": trend,
                "display_trend": trend,  # keep existing frontend key
                "rank": ra,              # current rank after this window
            })
    else:
        # No delta rows for this window → fall back to live compute from Predictions
        standings = _fallback_window_standings(season, window_key)

    # ---------- STATUS (keep yours if you already have a helper) ----------
    g_q = Game.objects.filter(season=season, window_key=window_key)
    p_q = PropBet.objects.filter(game__season=season, game__window_key=window_key)
    status_str = "upcoming" if (not g_q.exists() and not p_q.exists()) else (
        "complete" if (not g_q.filter(winner__isnull=True).exists() and not p_q.filter(correct_answer__isnull=True).exists())
        else "in-progress"
    )

    return Response({
        "standings": standings,
        "current_window": {"season": season, "window_key": window_key, "window_seq": window_seq, "status": status_str},
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_windowed_top3(request):
    """
    Top-3 standings for given/latest window with trend.
    Query params: season (int), window_key (str)
    """
    season = parse_int(request.GET.get("season"), default=get_current_season())
    window_key = request.GET.get("window_key")

    if not window_key:
        latest = resolve_latest_window(season)
        if not latest:
            return Response({"error": "No windowed data available"}, status=status.HTTP_404_NOT_FOUND)
        window_key, window_seq = latest
    else:
        window_seq = (
            UserWindowCumulative.objects
            .filter(season=season, window_key=window_key)
            .values_list("window_seq", flat=True).first()
        )

    rows = (
        UserWindowCumulative.objects
        .filter(season=season, window_key=window_key)
        .select_related("user")
        .values("user_id", "user__username", "rank_after", "cume_total_after",
                "rank_before", "rank_change", "trend", "display_trend")
    )
    items = [serialize_cume_row(r) for r in rows]
    items.sort(key=lambda x: (x["rank"] or 9999, x["username"].lower(), x["user_id"]))
    items = items[:3]

    status_str = compute_window_status(season, window_key)

    return Response({
        "items": items,
        "current_window": {
            "season": season,
            "window_key": window_key,
            "window_seq": window_seq,
            "status": status_str,
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_windowed_history(request):
    """
    History for a user across windows in a season.
    Query params: season (int), username (optional; defaults to request.user)
    """
    season = parse_int(request.GET.get("season"), default=get_current_season())
    username = request.GET.get("username")
    if username:
        user = get_object_or_404(User, username=username)
    else:
        user = request.user

    rows = (
        UserWindowCumulative.objects
        .filter(user=user, season=season)
        .order_by("window_seq")
        .values("window_key", "window_seq", "cume_total_after",
                "rank_after", "rank_before", "rank_change", "trend", "display_trend")
    )
    history = [{
        "window_key": r["window_key"],
        "window_seq": r["window_seq"],
        "total_points": r["cume_total_after"],
        "rank": r["rank_after"],
        "rank_before": r.get("rank_before"),
        "rank_change": r.get("rank_change", 0),
        "trend": r.get("trend", "same"),
        "display_trend": r.get("display_trend", True),
    } for r in rows]

    latest = resolve_latest_window(season)
    status_str = compute_window_status(season, latest[0]) if latest else "upcoming"

    return Response({
        "history": history,
        "current_window": {
            "season": season,
            "window_key": latest[0] if latest else None,
            "window_seq": latest[1] if latest else None,
            "status": status_str,
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_windowed_summary(request):
    """
    Lightweight summary for current window:
    - totals and ranks for everyone (capped to N if ?limit=)
    - optional include 'deltas' for this window (?include=deltas)
    """
    season = parse_int(request.GET.get("season"), default=get_current_season())
    limit = parse_int(request.GET.get("limit"), default=None)
    include = (request.GET.get("include") or "").split(",")

    latest = resolve_latest_window(season)
    if not latest:
        return Response({
        "items": [],
        "current_window": {
            "season": season,
            "window_key": None,
            "window_seq": None,
            "status": "upcoming",
        },
        "message": "No results yet. Check back once the opener finishes."
    })

    window_key, window_seq = latest

    cume_qs = (
        UserWindowCumulative.objects
        .filter(season=season, window_key=window_key)
        .select_related("user")
        .values("user_id", "user__username", "cume_total_after", "rank_after",
                "rank_change", "trend", "display_trend")
    )
    items = [serialize_cume_row(r) for r in cume_qs]
    items.sort(key=lambda x: (x["rank"] or 9999, x["username"].lower(), x["user_id"]))
    if limit:
        items = items[:limit]

    out: Dict[str, Any] = {
        "window_key": window_key,
        "season": season,
        "items": items,
        "current_window": {
            "season": season,
            "window_key": window_key,
            "window_seq": window_seq,
            "status": compute_window_status(season, window_key),
        },
    }

    if "deltas" in include:
        deltas_qs = (
            UserWindowDeltas.objects
            .filter(season=season, window_key=window_key)
            .select_related("user")
            .values("user_id", "user__username", "total_delta", "ml_points_delta", "prop_points_delta")
        )
        out["deltas"] = [
            {
                "user_id": r["user_id"],
                "username": r["user__username"],
                "total_delta": r["total_delta"],
                "ml_points_delta": r["ml_points_delta"],
                "prop_points_delta": r["prop_points_delta"],
            } for r in deltas_qs
        ]

    return Response(out)


# ---------------------------------------------------------------------------
# Admin/maintenance endpoints
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_windowed_data(request):
    """
    Recompute windowed data and optionally refresh MVs.
    Body (JSON): { "season": 2025, "window_key": "...", "force": true|false }
    """
    season = parse_int(request.data.get("season"), default=get_current_season())
    window_key = request.data.get("window_key")
    force = bool(request.data.get("force", False))

    if process_window and window_key:
        try:
            process_window(season, window_key)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    elif process_window and not window_key:
        # Rebuild latest known window
        latest = resolve_latest_window(season)
        if latest:
            try:
                process_window(season, latest[0])
            except Exception as e:
                return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if refresh_materialized_views:
        try:
            refresh_materialized_views()
        except Exception:
            # Not fatal
            pass

    return Response({"success": True, "season": season, "window_key": window_key, "forced": force})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_window_status(request):
    """
    Check completion + status for a window.
    Query params: window_key (required), season (optional)
    """
    window_key = request.GET.get("window_key")
    season = parse_int(request.GET.get("season"), default=get_current_season())
    if not window_key:
        return Response({"error": "window_key required"}, status=status.HTTP_400_BAD_REQUEST)

    games = Game.objects.filter(season=season, window_key=window_key)
    props = PropBet.objects.filter(game__season=season, game__window_key=window_key)

    status_str = compute_window_status(season, window_key)

    return Response({
        "window_key": window_key,
        "season": season,
        "status": status_str,
        "games_total": games.count(),
        "games_completed": games.filter(winner__isnull=False).count(),
        "games_incomplete": list(games.filter(winner__isnull=True).values_list("id", flat=True)),
        "props_total": props.count(),
        "props_completed": props.filter(correct_answer__isnull=False).count(),
        "props_incomplete": list(props.filter(correct_answer__isnull=True).values_list("id", flat=True)),
    })


# ---------------------------------------------------------------------------
# Legacy endpoints (soft-deprecated)
# ---------------------------------------------------------------------------
# If older clients call these, respond with a minimal redirect-style payload.
# Remove once frontend is fully migrated.

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_top3_api(request):
    """Deprecated; use /analytics/api/windowed-top3/"""
    resp = get_windowed_top3(request)
    data = resp.data
    return Response({"items": data.get("items", []), "current_window": data.get("current_window")})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_leaderboard_only(request):
    """Deprecated; use /analytics/api/windowed-standings/"""
    return get_windowed_standings(request)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_standings(request):
    """Deprecated; use /analytics/api/windowed-standings/"""
    return get_windowed_standings(request)

# ---------------------------------------------------------------------------
# New: Cached "single user dashboard" + Compare + Peek endpoints
# ---------------------------------------------------------------------------
from django.core.cache import cache
from predictions.models import Prediction, PropBetPrediction

def _cache_get_or_set(key: str, timeout: int, builder):
    data = cache.get(key)
    if data is not None:
        return data
    data = builder()
    cache.set(key, data, timeout=timeout)
    return data


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_dashboard(request):
    """
    Cached "everything" dashboard for a user.
    Query params:
      - username: optional (defaults to request.user)
      - season: optional (defaults to current)
      - window_key: optional (defaults to latest)
      - include: comma list (history, accuracy, deltas) — all included by default
      - vs: optional username to include comparison block
    Cache: 30s per (username, season, window_key, include, vs)
    """
    season = parse_int(request.GET.get("season"), default=get_current_season())
    username = request.GET.get("username") or request.user.username
    include_flags = (request.GET.get("include") or "history,accuracy,deltas").split(",")
    vs_user = request.GET.get("vs")

    # resolve user
    user = get_object_or_404(User, username=username)

    # latest window
    latest = resolve_latest_window(season)
    if not latest:
        return Response({"error": "No windowed data available"}, status=status.HTTP_404_NOT_FOUND)
    window_key, window_seq = request.GET.get("window_key") or latest

    cache_key = f"userdash:{username}:{season}:{window_key}:{','.join(sorted(include_flags))}:{vs_user or ''}"

    def build():
        # base row for current window
        row = (
            UserWindowCumulative.objects
            .filter(user=user, season=season, window_key=window_key)
            .values("cume_total_after", "rank_after", "rank_change", "trend", "display_trend")
            .first()
        ) or {}

        payload = {
            "user": {"username": user.username, "id": user.id},
            "season": season,
            "current_window": {
                "window_key": window_key,
                "window_seq": window_seq[1] if isinstance(window_seq, tuple) else window_seq,
                "status": compute_window_status(season, window_key),
            },
            "current_row": {
                "total_points": row.get("cume_total_after"),
                "rank": row.get("rank_after"),
                "rank_change": row.get("rank_change", 0),
                "trend": row.get("trend", "same"),
                "display_trend": row.get("display_trend", True),
            },
        }

        if "history" in include_flags:
            hist = (
                UserWindowCumulative.objects
                .filter(user=user, season=season)
                .order_by("window_seq")
                .values("window_key", "window_seq", "cume_total_after", "rank_after",
                        "rank_change", "trend", "display_trend")
            )
            payload["history"] = [{
                "window_key": h["window_key"],
                "window_seq": h["window_seq"],
                "total_points": h["cume_total_after"],
                "rank": h["rank_after"],
                "rank_change": h.get("rank_change", 0),
                "trend": h.get("trend", "same"),
                "display_trend": h.get("display_trend", True),
            } for h in hist]

        if "accuracy" in include_flags:
            # Moneyline accuracy
            ml_total = Game.objects.filter(season=season, winner__isnull=False).count()
            ml_correct = Prediction.objects.filter(
                user=user, game__season=season, game__winner__isnull=False
            ).filter(predicted_winner=F("game__winner")).count()
            ml_picks = Prediction.objects.filter(user=user, game__season=season).count()

            # Prop accuracy
            prop_total = PropBet.objects.filter(game__season=season, correct_answer__isnull=False).count()
            prop_correct = PropBetPrediction.objects.filter(
                user=user, prop_bet__game__season=season, prop_bet__correct_answer__isnull=False
            ).filter(selected_answer=F("prop_bet__correct_answer")).count()
            prop_picks = PropBetPrediction.objects.filter(user=user, prop_bet__game__season=season).count()

            payload["accuracy"] = {
                "moneyline": {"correct": ml_correct, "completed": ml_total, "picks": ml_picks},
                "props": {"correct": prop_correct, "completed": prop_total, "picks": prop_picks},
            }

        if "deltas" in include_flags:
            d = (
                UserWindowDeltas.objects
                .filter(user=user, season=season, window_key=window_key)
                .values("ml_points_delta", "prop_points_delta", "total_delta")
                .first()
            ) or {}
            payload["deltas"] = {
                "ml": d.get("ml_points_delta", 0),
                "prop": d.get("prop_points_delta", 0),
                "total": d.get("total_delta", 0),
            }

        # optional comparison vs another user
        if vs_user:
            other = get_object_or_404(User, username=vs_user)
            a = list(UserWindowCumulative.objects.filter(user=user, season=season).order_by("window_seq")
                     .values("window_seq", "cume_total_after", "rank_after"))
            b = list(UserWindowCumulative.objects.filter(user=other, season=season).order_by("window_seq")
                     .values("window_seq", "cume_total_after", "rank_after"))
            # merge by window_seq
            by_seq = {}
            for r in a:
                by_seq[r["window_seq"]] = {"seq": r["window_seq"], "a_points": r["cume_total_after"], "a_rank": r["rank_after"]}
            for r in b:
                by_seq.setdefault(r["window_seq"], {"seq": r["window_seq"]}).update({"b_points": r["cume_total_after"], "b_rank": r["rank_after"]})
            comp = []
            for seq in sorted(by_seq.keys()):
                row = by_seq[seq]
                ap = row.get("a_points"); bp = row.get("b_points")
                comp.append({
                    "window_seq": seq,
                    "a_points": ap, "b_points": bp,
                    "delta_points": (ap - bp) if (ap is not None and bp is not None) else None,
                    "a_rank": row.get("a_rank"), "b_rank": row.get("b_rank"),
                })
            payload["compare"] = {"a": user.username, "b": other.username, "windows": comp}

        return payload

    data = _cache_get_or_set(cache_key, 30, build)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def compare_users(request):
    """
    Head-to-head comparison for two users across a season.
    Query params: a=<username>, b=<username>, season (default current)
    Cache: 60s
    """
    a = request.GET.get("a"); b = request.GET.get("b")
    if not a or not b:
        return Response({"error": "a and b required"}, status=status.HTTP_400_BAD_REQUEST)
    season = parse_int(request.GET.get("season"), default=get_current_season())

    cache_key = f"compare:{a}:{b}:{season}"

    def build():
        ua = get_object_or_404(User, username=a)
        ub = get_object_or_404(User, username=b)
        a_rows = list(UserWindowCumulative.objects.filter(user=ua, season=season).order_by("window_seq")
                      .values("window_seq", "window_key", "cume_total_after", "rank_after"))
        b_rows = list(UserWindowCumulative.objects.filter(user=ub, season=season).order_by("window_seq")
                      .values("window_seq", "window_key", "cume_total_after", "rank_after"))
        # merge by window_seq
        idx = {}
        for r in a_rows:
            idx[r["window_seq"]] = {"seq": r["window_seq"], "key": r["window_key"], "a_points": r["cume_total_after"], "a_rank": r["rank_after"]}
        for r in b_rows:
            idx.setdefault(r["window_seq"], {"seq": r["window_seq"], "key": r["window_key"]}).update(
                {"b_points": r["cume_total_after"], "b_rank": r["rank_after"]})
        rows = []
        for seq in sorted(idx.keys()):
            row = idx[seq]
            ap = row.get("a_points"); bp = row.get("b_points")
            rows.append({
                "window_seq": seq, "window_key": row["key"],
                "a_points": ap, "b_points": bp,
                "delta_points": (ap - bp) if (ap is not None and bp is not None) else None,
                "a_rank": row.get("a_rank"), "b_rank": row.get("b_rank"),
            })
        return {"a": a, "b": b, "season": season, "windows": rows}

    data = _cache_get_or_set(cache_key, 60, build)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def peek_window(request):
    """
    Reveal who picked what — but ONLY for locked games/props in a window.
    Query params: season (default current), window_key (default latest)
    Cache: 15s
    """
    season = parse_int(request.GET.get("season"), default=get_current_season())
    latest = resolve_latest_window(season)
    if not latest:
        return Response({"error": "No windowed data available"}, status=status.HTTP_404_NOT_FOUND)
    window_key = request.GET.get("window_key") or latest[0]

    cache_key = f"peek:{season}:{window_key}"

    def build():
        # games in window
        games = list(Game.objects.filter(season=season, window_key=window_key)
                     .values("id", "home_team", "away_team", "start_time", "locked", "winner"))
        game_ids = [g["id"] for g in games]

        # predictions for those games
        preds = list(
            Prediction.objects.filter(game_id__in=game_ids)
            .select_related("user", "game")
            .values("game_id", "user__username", "predicted_winner")
        )

        # prop bets in window
        props = list(
            PropBet.objects.filter(game__season=season, game__window_key=window_key)
            .select_related("game")
            .values("id", "game_id", "question", "correct_answer")
        )
        prop_ids = [p["id"] for p in props]
        prop_preds = list(
            PropBetPrediction.objects.filter(prop_bet_id__in=prop_ids)
            .select_related("user", "prop_bet")
            .values("prop_bet_id", "user__username", "selected_answer")
        )

        # build response per game/prop with lock check
        out_games = []
        now = timezone.now()

        def is_locked_row(g):
            st = g["start_time"]
            if st is not None and timezone.is_naive(st):
                st = timezone.make_aware(st, dt_timezone.utc)
            return bool(g.get("locked")) or (st is not None and now >= st)

        # group predictions by game
        by_game = {}
        for p in preds:
            by_game.setdefault(p["game_id"], []).append({"username": p["user__username"], "pick": p["predicted_winner"]})

        for g in games:
            locked = is_locked_row(g)
            row = {
                "game_id": g["id"],
                "home_team": g["home_team"], "away_team": g["away_team"],
                "start_time": g["start_time"],
                "winner": g["winner"],
                "locked": locked,
            }
            if locked:
                picks = by_game.get(g["id"], [])
                row["picks"] = picks
            out_games.append(row)

        # group prop predictions
        by_prop = {}
        for p in prop_preds:
            by_prop.setdefault(p["prop_bet_id"], []).append({"username": p["user__username"], "answer": p["selected_answer"]})

        out_props = []
        for pb in props:
            g = next((x for x in games if x["id"] == pb["game_id"]), None)
            locked = is_locked_row(g) if g else False
            row = {
                "prop_bet_id": pb["id"],
                "game_id": pb["game_id"],
                "question": pb["question"],
                "locked": locked,
            }
            if locked:
                row["answers"] = by_prop.get(pb["id"], [])
            out_props.append(row)

        return {
            "window_key": window_key,
            "season": season,
            "peeked_at": timezone.now(),
            "games": out_games,
            "props": out_props,
        }

    data = _cache_get_or_set(cache_key, 15, build)
    return Response(data)

# Fallback endpoints (NEW)
def calculate_user_realtime_accuracy(user, season: Optional[int] = None):
    games_q = Game.objects.filter(winner__isnull=False)
    props_q = PropBet.objects.filter(correct_answer__isnull=False)
    if season is not None:
        games_q = games_q.filter(season=season)
        props_q = props_q.filter(game__season=season)

    completed_games = games_q
    completed_props = props_q

    correct_ml = Prediction.objects.filter(user=user, is_correct=True, game__in=completed_games).count()
    correct_props = PropBetPrediction.objects.filter(user=user, is_correct=True, prop_bet__in=completed_props).count()

    total_ml = completed_games.count()
    total_props = completed_props.count()

    ml_pct = round((correct_ml / total_ml) * 100, 1) if total_ml else 0.0
    prop_pct = round((correct_props / total_props) * 100, 1) if total_props else 0.0
    overall_pct = round(((correct_ml + correct_props) / (total_ml + total_props)) * 100, 1) if (total_ml + total_props) else 0.0

    return {
        "moneyline_accuracy": ml_pct,
        "prop_accuracy": prop_pct,
        "overall_accuracy": overall_pct,
        "total_points": correct_ml + (2 * correct_props),
        "correct_ml": correct_ml, "correct_props": correct_props,
        "total_ml": total_ml, "total_props": total_props,
    }

def build_realtime_leaderboard(limit=10, season: Optional[int] = None):
    rows = []
    for u in User.objects.all():
        s = calculate_user_realtime_accuracy(u, season=season)
        rows.append({
            "username": u.username,
            "total_points": s["total_points"],
            "overall_accuracy": s["overall_accuracy"],
            "moneyline_accuracy": s["moneyline_accuracy"],
            "prop_accuracy": s["prop_accuracy"],
        })
    rows.sort(key=lambda r: (-r["total_points"], r["username"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows[:limit] if limit is not None else rows

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def realtime_fallback_combined(request):
    season = parse_int(request.GET.get('season'), default=get_current_season())
    limit = parse_int(request.GET.get('limit'), default=10, minimum=1, maximum=50)
    user = request.user
    user_stats = calculate_user_realtime_accuracy(user, season=season)
    leaderboard = build_realtime_leaderboard(limit=limit, season=season)
    ...
    return Response({...})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def realtime_user_stats_only(request):
    season = parse_int(request.GET.get('season'), default=get_current_season())
    user = request.user
    stats = calculate_user_realtime_accuracy(user, season=season)
    return Response({...})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def realtime_leaderboard_only(request):
    season = parse_int(request.GET.get('season'), default=get_current_season())
    limit = parse_int(request.GET.get('limit'), default=10, minimum=1, maximum=50)
    user = request.user
    leaderboard = build_realtime_leaderboard(limit=limit, season=season)
    ...
    return Response({...})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def window_completeness(request):
    """
    Utility endpoint: is a given window complete?
    Query params:
      - window_key (required)
      - season (optional; if omitted, infer from any Game with that window_key)
    """
    window_key = request.GET.get("window_key")
    if not window_key:
        return Response({"error": "window_key required"}, status=status.HTTP_400_BAD_REQUEST)

    # Try season from query first
    season = parse_int(request.GET.get("season"), default=None)

    # If not provided, infer from any game in this window
    base_games = Game.objects.filter(window_key=window_key)
    if season is None:
        season = (
            base_games
            .exclude(season__isnull=True)
            .values_list("season", flat=True)
            .distinct()
            .first()
        )

    games = base_games if season is None else base_games.filter(season=season)
    props = PropBet.objects.filter(game__in=games)

    total_games = games.count()
    total_props = props.count()

    # If nothing scheduled for that (season, window_key), it's not “complete”
    if total_games == 0 and total_props == 0:
        return Response({
            "window_key": window_key,
            "season": season,
            "is_complete": False,
            "games_total": 0,
            "games_completed": 0,
            "games_incomplete": [],
            "props_total": 0,
            "props_completed": 0,
            "props_incomplete": [],
        })

    is_complete = (
        games.filter(winner__isnull=True).count() == 0 and
        props.filter(correct_answer__isnull=True).count() == 0
    )

    return Response({
        "window_key": window_key,
        "season": season,
        "is_complete": is_complete,
        "games_total": total_games,
        "games_completed": games.filter(winner__isnull=False).count(),
        "games_incomplete": list(games.filter(winner__isnull=True).values_list("id", flat=True)),
        "props_total": total_props,
        "props_completed": props.filter(correct_answer__isnull=False).count(),
        "props_incomplete": list(props.filter(correct_answer__isnull=True).values_list("id", flat=True)),
    })
