# analytics/services/window_stats.py
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple, Iterable

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from games.models import Game, Window, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat

ML_POINTS = 1
PB_POINTS = 2

@transaction.atomic
def recompute_window(window_id: int) -> None:
    """
    After any ML/prop grading within a window:
      1) recompute window-level correctness + this-window points for affected users
      2) update season_cume_points at (user, window)
      3) propagate delta forward to all later windows in same season for those users
      4) calculate dense rankings for this window
      5) (optional) flip completeness
    """
    season, affected = _recompute_window_and_get_deltas(window_id)
    _propagate_cume_delta_forward(season, window_id, affected)
    _calculate_dense_ranks(window_id)
    _flip_window_completeness(window_id)  # same helper you already added


def _recompute_window_and_get_deltas(window_id: int) -> Tuple[int, List[Tuple[int, int]]]:
    """
    Returns (season, affected) where affected = [(user_id, delta_cume_at_window), ...]
    delta_cume_at_window = new_cume_at_window - old_cume_at_window.
    """
    # Gather games and season
    game_qs = Game.objects.filter(window_id=window_id).only("id", "season")
    game_ids = list(game_qs.values_list("id", flat=True))
    if not game_ids:
        # no games -> clear rows and signal no affected users
        old_rows = list(UserWindowStat.objects.filter(window_id=window_id).values("user_id", "season_cume_points"))
        UserWindowStat.objects.filter(window_id=window_id).delete()
        # downstream we’ll treat as zero delta (no propagation)
        season = Game.objects.filter(window_id=window_id).values_list("season", flat=True).first() or 0
        return season, []

    season = game_qs.first().season

    # 1) Include ALL users in the system for complete analytics
    from django.contrib.auth import get_user_model
    User = get_user_model()
    affected_user_ids = sorted(User.objects.values_list("id", flat=True))
    
    # 2) window-level correctness for all participating users
    ml = defaultdict(int)
    for (uid,) in MoneyLinePrediction.objects.filter(game_id__in=game_ids, is_correct=True).values_list("user_id"):
        ml[uid] += 1

    pb = defaultdict(int)
    for (uid,) in PropBetPrediction.objects.filter(prop_bet__game_id__in=game_ids, is_correct=True).values_list("user_id"):
        pb[uid] += 1

    # 3) compute TRUE cumulative season points for each user
    # This should be ALL points earned in the season up to this window's date
    current_window = Window.objects.get(id=window_id)
    
    # Get all completed games in the season up to (and including) this window's date
    completed_games_through_window = Game.objects.filter(
        season=season,
        window__date__lte=current_window.date,
        winner__isnull=False
    ).values_list("id", flat=True)
    
    # Calculate total season points for each user from ALL completed games
    season_cume_map: Dict[int, int] = {}
    for uid in affected_user_ids:
        # ML points from all completed games in season
        ml_total = MoneyLinePrediction.objects.filter(
            user_id=uid,
            game_id__in=completed_games_through_window,
            is_correct=True
        ).count() * ML_POINTS
        
        # PB points from all completed prop bets in season
        pb_total = PropBetPrediction.objects.filter(
            user_id=uid,
            prop_bet__game_id__in=completed_games_through_window,
            is_correct=True
        ).count() * PB_POINTS
        
        season_cume_map[uid] = ml_total + pb_total

    # old cume at this window (to get delta for propagation)
    old_cume_map = dict(
        UserWindowStat.objects.filter(window_id=window_id, user_id__in=affected_user_ids)
        .values_list("user_id", "season_cume_points")
    )

    upserts: List[UserWindowStat] = []
    deltas: List[Tuple[int, int]] = []  # (user_id, delta_cume_at_window)
    for uid in affected_user_ids:
        new_cume = season_cume_map[uid]
        old_cume = old_cume_map.get(uid, 0)
        delta = new_cume - old_cume
        deltas.append((uid, delta))

        upserts.append(UserWindowStat(
            user_id=uid,
            window_id=window_id,
            ml_correct=ml.get(uid, 0),  # Still track window-specific correctness
            pb_correct=pb.get(uid, 0),  # Still track window-specific correctness
            season_cume_points=new_cume,  # TRUE cumulative season total
        ))

    if upserts:
        UserWindowStat.objects.bulk_create(
            upserts,
            update_conflicts=True,
            update_fields=["ml_correct", "pb_correct", "season_cume_points"],
            unique_fields=["user", "window"],
        )

    return season, deltas


def _propagate_cume_delta_forward(season: int, from_window_id: int, deltas: Iterable[Tuple[int, int]]) -> None:
    """
    For each (user, delta_at_window), add delta to all later windows' season_cume_points for that user.
    This keeps cumulative values consistent if an earlier window changes.
    """
    if not season or not deltas:
        return

    later_windows = list(
        Window.objects.filter(season=season, id__gt=from_window_id).values_list("id", flat=True)
    )
    if not later_windows:
        return

    for uid, delta in deltas:
        if delta == 0:
            continue
        UserWindowStat.objects.filter(user_id=uid, window_id__in=later_windows).update(season_cume_points=F("season_cume_points") + delta)


def _calculate_dense_ranks(window_id: int) -> None:
    """
    Calculate and assign dense rankings for all users in this window based on season_cume_points.
    Dense ranking: users with same points get same rank, next rank is incremented by 1.
    (e.g., if two users tie for rank 2, next user gets rank 3, not rank 4)
    """
    # Get all user stats for this window, ordered by points descending, then user_id ascending for stability
    user_stats = list(
        UserWindowStat.objects
        .filter(window_id=window_id)
        .order_by('-season_cume_points', 'user_id')
    )
    
    if not user_stats:
        return
    
    # Calculate dense ranks
    current_rank = 1
    prev_points = None
    
    updates = []
    for stat in user_stats:
        # If points are different from previous user, update rank
        if prev_points is not None and stat.season_cume_points < prev_points:
            current_rank += 1
        
        # Only update if rank has changed to avoid unnecessary DB writes
        if stat.rank_dense != current_rank:
            stat.rank_dense = current_rank
            updates.append(stat)
        
        prev_points = stat.season_cume_points
    
    # Bulk update ranks
    if updates:
        UserWindowStat.objects.bulk_update(updates, ['rank_dense'])


# --- completeness flipping (unchanged behavior) ---
def _is_window_complete(window_id: int) -> bool:
    games = Game.objects.filter(window_id=window_id)
    if not games.exists():
        return False
    if games.filter(winner__isnull=True).exists():
        return False
    if PropBet.objects.filter(game__in=games, correct_answer__isnull=True).exists():
        return False
    return True

@transaction.atomic
def _flip_window_completeness(window_id: int) -> None:
    try:
        w = Window.objects.select_for_update().get(pk=window_id)
    except Window.DoesNotExist:
        return
    done = _is_window_complete(window_id)
    if done and not w.is_complete:
        w.is_complete = True
        w.completed_at = timezone.now()
        w.save(update_fields=["is_complete", "completed_at", "updated_at"])
    elif not done and w.is_complete:
        w.is_complete = False
        w.completed_at = None
        w.save(update_fields=["is_complete", "completed_at", "updated_at"])
