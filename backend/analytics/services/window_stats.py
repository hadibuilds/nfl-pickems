from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat

ML_POINTS = 1
PB_POINTS = 2


@transaction.atomic
def recompute_window(window_id: int) -> None:
    """
    Rebuild UserWindowStat for a window from ground truth (idempotent).
    - Count correct ML and Prop predictions per user
    - Compute total points
    - Dense rank (1,2,2,3)
    - Update Window.is_complete/completed_at based on completeness
    """
    window = Window.objects.select_for_update().get(pk=window_id)

    game_ids = list(Game.objects.filter(window_id=window_id).values_list("id", flat=True))
    prop_ids = list(PropBet.objects.filter(game_id__in=game_ids).values_list("id", flat=True))

    # Aggregate ML correctness
    ml = (
        MoneyLinePrediction.objects.filter(game_id__in=game_ids)
        .values("user_id")
        .annotate(ml_correct=Count("id", filter=Q(is_correct=True)))
    )
    ml_map = {row["user_id"]: row["ml_correct"] for row in ml}

    # Aggregate Prop correctness
    pb = (
        PropBetPrediction.objects.filter(prop_bet_id__in=prop_ids)
        .values("user_id")
        .annotate(pb_correct=Count("id", filter=Q(is_correct=True)))
    )
    pb_map = {row["user_id"]: row["pb_correct"] for row in pb}

    # Union users, compute points
    user_ids = set(ml_map.keys()) | set(pb_map.keys())
    new_stats = []
    for uid in user_ids:
        mlc = ml_map.get(uid, 0)
        pbc = pb_map.get(uid, 0)
        pts = mlc * ML_POINTS + pbc * PB_POINTS
        new_stats.append((uid, mlc, pbc, pts))

    # Replace stats
    UserWindowStat.objects.filter(window_id=window_id).delete()
    if new_stats:
        UserWindowStat.objects.bulk_create([
            UserWindowStat(window_id=window_id, user_id=uid, ml_correct=mlc, pb_correct=pbc, total_points=pts)
            for uid, mlc, pbc, pts in new_stats
        ])

    # Dense rank in Python (fast for small N per window)
    rows = list(UserWindowStat.objects.filter(window_id=window_id).order_by("-total_points", "user_id"))
    rank = 0
    last_pts = None
    seen = 0
    for r in rows:
        seen += 1
        if last_pts is None or r.total_points < last_pts:
            rank = seen
            last_pts = r.total_points
        r.rank_dense = rank
    if rows:
        UserWindowStat.objects.bulk_update(rows, ["rank_dense"])

    # Window completeness: all games graded + all props graded
    total_games = len(game_ids)
    completed_games = Game.objects.filter(id__in=game_ids, winner__isnull=False).count()
    total_props = len(prop_ids)
    completed_props = PropBet.objects.filter(id__in=prop_ids, correct_answer__isnull=False).count()

    is_complete = (total_games == completed_games) and (total_props == completed_props)
    if is_complete and not window.is_complete:
        window.is_complete = True
        window.completed_at = timezone.now()
        window.save(update_fields=["is_complete", "completed_at", "updated_at"])
    elif not is_complete and window.is_complete:
        window.is_complete = False
        window.completed_at = None
        window.save(update_fields=["is_complete", "completed_at", "updated_at"])
