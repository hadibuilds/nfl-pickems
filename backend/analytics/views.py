from __future__ import annotations

from typing import Dict, Any, Optional
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat


def parse_window_key(key: str) -> Dict[str, Any]:
    # "YYYY-MM-DD:slot"
    try:
        date_str, slot = key.split(":")
    except ValueError:
        raise ValueError("Invalid window_key. Expected 'YYYY-MM-DD:slot'.")
    return {"date": date_str, "slot": slot}


def get_window_by_key_or_404(window_key: str) -> Window:
    parts = parse_window_key(window_key)
    try:
        return Window.objects.get(date=parts["date"], slot=parts["slot"])
    except Window.DoesNotExist:
        raise ValueError("Window not found.")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_window(request):
    """
    Live snapshot for a window (user-scoped):
      - pending_ml / pending_pb (unlocked & unanswered)
      - my_rank (dense) and my_points (from UserWindowStat for this window)
      - completeness counts (games/props graded vs total)
    Query params: ?window_key=YYYY-MM-DD:slot
    """
    window_key = request.query_params.get("window_key")
    if not window_key:
        return Response({"detail": "window_key is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        win = get_window_by_key_or_404(window_key)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()

    # Window contents
    game_ids = list(Game.objects.filter(window=win).values_list("id", flat=True))
    prop_ids = list(PropBet.objects.filter(game_id__in=game_ids).values_list("id", flat=True))

    # Locked definition (mirror Game.is_locked): locked flag OR start_time <= now
    locked_game_ids = set(
        Game.objects.filter(id__in=game_ids).filter(Q(locked=True) | Q(start_time__lte=now)).values_list("id", flat=True)
    )
    unlocked_game_ids = set(game_ids) - locked_game_ids

    # User’s existing picks
    user_id = request.user.id
    my_ml_game_ids = set(
        MoneyLinePrediction.objects.filter(user_id=user_id, game_id__in=game_ids).values_list("game_id", flat=True)
    )
    my_pb_prop_ids = set(
        PropBetPrediction.objects.filter(user_id=user_id, prop_bet_id__in=prop_ids).values_list("prop_bet_id", flat=True)
    )

    # Pending = unlocked minus what the user has already picked
    pending_ml = len(unlocked_game_ids - my_ml_game_ids)

    unlocked_prop_ids = set(
        PropBet.objects.filter(id__in=prop_ids, game_id__in=unlocked_game_ids).values_list("id", flat=True)
    )
    pending_pb = len(unlocked_prop_ids - my_pb_prop_ids)

    # My current rank/points in this window (from snapshot; recomputed on every grade)
    my_stat: Optional[UserWindowStat] = (
        UserWindowStat.objects.filter(window=win, user_id=user_id).only("rank_dense", "season_cume_points").first()
    )
    my_rank = my_stat.rank_dense if my_stat else None
    my_points = my_stat.season_cume_points if my_stat else 0

    # Completeness (live)
    total_games = len(game_ids)
    completed_games = Game.objects.filter(id__in=game_ids, winner__isnull=False).count()
    total_props = len(prop_ids)
    completed_props = PropBet.objects.filter(id__in=prop_ids, correct_answer__isnull=False).count()

    payload = {
        "window": {
            "id": win.id,
            "season": win.season,
            "date": str(win.date),
            "slot": win.slot,
            "is_complete": win.is_complete,  # snapshot flag
            "updated_at": win.updated_at.isoformat() if hasattr(win, "updated_at") and win.updated_at else None,
        },
        "live": {
            "games_total": total_games,
            "games_completed": completed_games,
            "props_total": total_props,
            "props_completed": completed_props,
            "pending_ml": pending_ml,
            "pending_pb": pending_pb,
        },
        "me": {
            "rank_dense": my_rank,
            "total_points": my_points,
        },
    }
    # For truly live behavior, strongly consider:
    #   Response(..., headers={"Cache-Control": "no-store"})
    return Response(payload, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    """
    Live leaderboard (points) for a window + optional rank-trend vs previous completed window.
    Query params:
      - window_key=YYYY-MM-DD:slot
      - limit (optional, default 10)
      - include_trend (optional, default true)
    """
    window_key = request.query_params.get("window_key")
    limit = int(request.query_params.get("limit", "10") or 10)
    include_trend = request.query_params.get("include_trend", "true").lower() != "false"

    if not window_key:
        return Response({"detail": "window_key is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        win = get_window_by_key_or_404(window_key)
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    # Current window leaderboard (points + dense rank)
    rows = list(
        UserWindowStat.objects
        .filter(window=win)
        .select_related("user")
        .order_by("-season_cume_points", "user_id")[:limit]
        .values("user_id", "user__username", "season_cume_points", "rank_dense")
    )

    # Optional trend arrows vs previous completed window
    trend_map = {}
    if include_trend:
        prev = Window.previous_completed(season=win.season, date=win.date, slot=win.slot)
        if prev:
            prev_ranks = dict(
                UserWindowStat.objects.filter(window=prev).values_list("user_id", "rank_dense")
            )
            for r in rows:
                uid = r["user_id"]
                if uid in prev_ranks:
                    # negative means improved (e.g., 5 -> 3 = -2), positive means worse
                    trend_map[uid] = prev_ranks[uid] - r["rank_dense"]

    # Build payload
    payload = {
        "window": {
            "id": win.id,
            "season": win.season,
            "date": str(win.date),
            "slot": win.slot,
            "updated_at": win.updated_at.isoformat() if hasattr(win, "updated_at") and win.updated_at else None,
        },
        "leaderboard": [
            {
                "user_id": r["user_id"],
                "username": r["user__username"],
                "total_points": r["season_cume_points"],
                "rank_dense": r["rank_dense"],
                **({"trend_delta": trend_map.get(r["user_id"])} if include_trend else {}),
            }
            for r in rows
        ],
    }
    # This can be cached with an ETag based on window.updated_at.
    return Response(payload, status=status.HTTP_200_OK)
