from django.db.models import Window, F
from django.db.models.functions import DenseRank
from django.db import transaction, connection
from django.utils import timezone

from analytics.models import UserStatHistory, UserSeasonTotals
from games.models import Game, PropBet


def is_window_closable(window_key: str) -> bool:
    # A window is closable iff all games AND prop-bets in that window have winners/results.
    games_qs = Game.objects.filter(window_key=window_key)
    if not games_qs.exists():
        return False
    if games_qs.filter(winner__isnull=True).exists():
        return False
    prop_qs = PropBet.objects.filter(game__window_key=window_key)
    if prop_qs.filter(correct_answer__isnull=True).exists():
        return False
    return True


def snapshot_full_leaderboard_for_window(window_key: str, season: int) -> int:
    """
    When a window closes, snapshot dense ranks for ALL users into UserStatHistory.
    Presence of rows (season, window_key) means the window is CLOSED.
    """
    now = timezone.now()
    qs = (
        UserSeasonTotals.objects.filter(season=season)
        .annotate(rank=Window(
            expression=DenseRank(),
            order_by=[F("total_points").desc(), F("ml_points").desc(), F("user__username").asc()],
        ))
        .values("user_id", "rank")
    )
    rows = [UserStatHistory(user_id=r["user_id"], season=season, window_key=window_key, rank=r["rank"], created_at=now)
            for r in qs]

    with transaction.atomic():
        UserStatHistory.objects.bulk_create(rows, ignore_conflicts=True)
        if connection.vendor == "postgresql":
            with connection.cursor() as cur:
                # If you’ve added an MV for trends, refresh here.
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_rank_trend_mv;")
    return len(rows)


def close_window_if_ready(window_key: str, season: int) -> bool:
    """
    Only mark CLOSED (snapshot) if all results are present; idempotent.
    """
    already_closed = UserStatHistory.objects.filter(season=season, window_key=window_key).exists()
    if already_closed:
        return True
    if not is_window_closable(window_key):
        return False
    snapshot_full_leaderboard_for_window(window_key, season)
    return True


def get_closed_window_keys_for_season(season: int):
    # window_key format "YYYY-MM-DD:morning|afternoon|late" sorts chronologically
    return list(
        UserStatHistory.objects.filter(season=season)
        .values_list("window_key", flat=True).distinct()
        .order_by("window_key")
    )

def get_prev_closed_window(season: int, current_window_key: str):
    keys = get_closed_window_keys_for_season(season)
    if current_window_key not in keys:
        return None
    i = keys.index(current_window_key)
    return keys[i-1] if i > 0 else None

def get_first_closed_window(season: int):
    keys = get_closed_window_keys_for_season(season)
    return keys[0] if keys else None


def compute_window_trend_for_all_users(season: int, current_window_key: str):
    """
    Compare CURRENT CLOSED window to the immediately PREVIOUS CLOSED window.
    Opening window is baseline only (trend/rank_change = null).
    If a prior window is missing (gap), caller should pass the latest *closed* window only.
    """
    # Ensure current is CLOSED
    if not UserStatHistory.objects.filter(season=season, window_key=current_window_key).exists():
        return {}

    # Opening window → baseline (no trend)
    first_key = get_first_closed_window(season)
    if not first_key or current_window_key == first_key:
        return {}

    prev_key = get_prev_closed_window(season, current_window_key)
    if not prev_key:
        return {}

    prev = dict(UserStatHistory.objects.filter(season=season, window_key=prev_key).values_list("user_id", "rank"))
    cur  = dict(UserStatHistory.objects.filter(season=season, window_key=current_window_key).values_list("user_id", "rank"))

    trend_map = {}
    for uid, new_rank in cur.items():
        old_rank = prev.get(uid)
        if old_rank is None:
            trend_map[uid] = (None, None)  # first time this user has a baseline
        elif new_rank < old_rank:
            trend_map[uid] = ("up", old_rank - new_rank)
        elif new_rank > old_rank:
            trend_map[uid] = ("down", new_rank - old_rank)
        else:
            trend_map[uid] = ("same", 0)
    return trend_map
