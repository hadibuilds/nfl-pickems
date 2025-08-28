
# predictions/views.py — Optimized, logic-preserving, and bulk-friendly

from typing import Dict, Any, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from games.models import Game, PropBet
from .models import Prediction, PropBetPrediction

User = get_user_model()


# =============================================================================
# Helpers
# =============================================================================

def parse_int(value, default: int = 0, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    try:
        iv = int(value)
    except (TypeError, ValueError):
        iv = default
    if minimum is not None and iv < minimum:
        iv = minimum
    if maximum is not None and iv > maximum:
        iv = maximum
    return iv


def game_is_locked(game: Game) -> bool:
    '''True if the game is locked from editing (manual lock or kickoff passed).'''
    # Prefer model property if present
    if hasattr(game, "is_locked"):
        return bool(getattr(game, "is_locked"))
    # Fallback by time + optional boolean flag
    now = timezone.now()
    locked_flag = bool(getattr(game, "locked", False))
    start = getattr(game, "start_time", None)
    if start is not None and timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.utc)
    time_locked = start is not None and now >= start
    return locked_flag or time_locked


def propbet_is_locked(prop: PropBet) -> bool:
    '''True if prop bet should be locked (mirrors its game's lock).'''
    # Prefer model property if present
    if hasattr(prop, "is_locked"):
        return bool(getattr(prop, "is_locked"))
    return game_is_locked(prop.game)


def upsert_prediction(user: User, game: Game, predicted_winner: str) -> Tuple[bool, Dict[str, Any]]:
    '''Create or update a moneyline prediction. Returns (ok, payload).'''
    if game_is_locked(game):
        return False, {"error": "locked", "game_id": game.id}

    obj, created = Prediction.objects.update_or_create(
        user=user,
        game=game,
        defaults={"predicted_winner": predicted_winner},
    )
    return True, {
        "game_id": game.id,
        "predicted_winner": predicted_winner,
        "created": created,
        "id": obj.id,
    }


def upsert_prop_prediction(user: User, prop: PropBet, answer: str) -> Tuple[bool, Dict[str, Any]]:
    '''Create or update a prop bet prediction. Returns (ok, payload).'''
    if propbet_is_locked(prop):
        return False, {"error": "locked", "prop_bet_id": prop.id}

    obj, created = PropBetPrediction.objects.update_or_create(
        user=user,
        prop_bet=prop,
        defaults={"answer": answer},
    )
    return True, {
        "prop_bet_id": prop.id,
        "answer": answer,
        "created": created,
        "id": obj.id,
    }


# =============================================================================
# WRITES
# =============================================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_selection(request):
    '''
    Save ONE selection.
    Accepts either:
      - { "game_id": <int>, "predicted_winner": "<TEAM>" }
      - { "prop_bet_id": <int>, "answer": "<OPTION>" }
    '''
    user = request.user
    game_id = request.data.get("game_id")
    prop_bet_id = request.data.get("prop_bet_id")

    if game_id:
        predicted_winner = request.data.get("predicted_winner")
        if not predicted_winner:
            return Response({"error": "predicted_winner required"}, status=status.HTTP_400_BAD_REQUEST)
        game = get_object_or_404(Game.objects.only("id", "locked", "start_time"), pk=game_id)
        ok, payload = upsert_prediction(user, game, predicted_winner)
        return Response(payload, status=status.HTTP_200_OK if ok else status.HTTP_409_CONFLICT)

    if prop_bet_id:
        answer = request.data.get("answer")
        if not answer:
            return Response({"error": "answer required"}, status=status.HTTP_400_BAD_REQUEST)
        prop = get_object_or_404(
            PropBet.objects.select_related("game").only("id", "game__id", "game__locked", "game__start_time"),
            pk=prop_bet_id,
        )
        ok, payload = upsert_prop_prediction(user, prop, answer)
        return Response(payload, status=status.HTTP_200_OK if ok else status.HTTP_409_CONFLICT)

    return Response({"error": "game_id or prop_bet_id required"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_selections(request):
    '''
    Bulk save selections.
    Body:
    {
      "picks": [{ "game_id": 1, "predicted_winner": "SF" }, ...],
      "props": [{ "prop_bet_id": 10, "answer": "Over" }, ...]
    }
    Returns per-item results; never partial-fails the whole request.
    '''
    user = request.user
    picks: List[Dict[str, Any]] = request.data.get("picks") or []
    props: List[Dict[str, Any]] = request.data.get("props") or []

    # Prefetch targets to cut DB round-trips
    game_ids = [p.get("game_id") for p in picks if p.get("game_id")]
    prop_ids = [p.get("prop_bet_id") for p in props if p.get("prop_bet_id")]

    games_map = {g.id: g for g in Game.objects.filter(id__in=game_ids).only("id", "locked", "start_time")}
    props_qs = PropBet.objects.filter(id__in=prop_ids).select_related("game").only("id", "game__id", "game__locked", "game__start_time")
    props_map = {pb.id: pb for pb in props_qs}

    results = {"picks": [], "props": []}

    with transaction.atomic():
        # Picks
        for item in picks:
            gid = item.get("game_id")
            team = item.get("predicted_winner")
            if not gid or not team:
                results["picks"].append({"game_id": gid, "ok": False, "error": "invalid_payload"})
                continue
            game = games_map.get(gid)
            if not game:
                results["picks"].append({"game_id": gid, "ok": False, "error": "not_found"})
                continue
            ok, payload = upsert_prediction(user, game, team)
            results["picks"].append({"game_id": gid, "ok": ok, **payload})

        # Props
        for item in props:
            pid = item.get("prop_bet_id")
            ans = item.get("answer")
            if not pid or ans is None:
                results["props"].append({"prop_bet_id": pid, "ok": False, "error": "invalid_payload"})
                continue
            prop = props_map.get(pid)
            if not prop:
                results["props"].append({"prop_bet_id": pid, "ok": False, "error": "not_found"})
                continue
            ok, payload = upsert_prop_prediction(user, prop, ans)
            results["props"].append({"prop_bet_id": pid, "ok": ok, **payload})

    # Summaries
    failed = sum(1 for r in results["picks"] if not r.get("ok")) + sum(1 for r in results["props"] if not r.get("ok"))
    http_status = status.HTTP_200_OK if failed == 0 else status.HTTP_207_MULTI_STATUS
    return Response({"success": failed == 0, "failed": failed, "results": results}, status=http_status)


# =============================================================================
# READS
# =============================================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_predictions(request):
    '''
    Return user's selections in a simple mapping format suitable for the React app:
      {
        "picks": { "<game_id>": "<TEAM>" },
        "props": { "<prop_bet_id>": "<ANSWER>" }
      }
    '''
    user = request.user
    predictions = (
        Prediction.objects.filter(user=user)
        .select_related("game")
        .only("id", "predicted_winner", "game__id")
    )
    props = (
        PropBetPrediction.objects.filter(user=user)
        .select_related("prop_bet")
        .only("id", "answer", "prop_bet__id")
    )

    picks_map = {str(p.game_id): p.predicted_winner for p in predictions}
    props_map = {str(pp.prop_bet_id): pp.answer for pp in props}

    return Response({"picks": picks_map, "props": props_map})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_recent_games_only(request):
    '''
    Recent games + user's picks and results.
    Query params:
      - limit: number of games (default 3, max 10)
    '''
    user = request.user
    limit = parse_int(request.GET.get("limit"), default=3, minimum=1, maximum=10)

    # Pull most recent finished games the user predicted on
    # (Assumes Game.winner is set when finished)
    qs = (
        Game.objects.filter(prediction__user=user, winner__isnull=False)
        .select_related()
        .only("id", "home_team", "away_team", "winner", "start_time", "season", "week")
        .order_by("-start_time")[:limit]
    )

    # Batch fetch user's predictions for these games
    game_ids = list(qs.values_list("id", flat=True))
    preds = Prediction.objects.filter(user=user, game_id__in=game_ids).only("game_id", "predicted_winner")
    pred_map = {p.game_id: p.predicted_winner for p in preds}

    recent = []
    for g in qs:
        pick = pred_map.get(g.id)
        recent.append(
            {
                "game_id": g.id,
                "home_team": g.home_team,
                "away_team": g.away_team,
                "winner": g.winner,
                "predicted_winner": pick,
                "correct": (pick == g.winner) if pick and g.winner else None,
                "start_time": g.start_time,
                "season": g.season,
                "week": getattr(g, "week", None),
            }
        )
    return Response({"recentGames": recent, "limit": limit, "totalGames": len(recent)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def window_completeness(request):
    '''
    Utility endpoint: is a given window complete?
    Query params: window_key (required), season (optional if window_key encodes date).
    '''
    window_key = request.GET.get("window_key")
    if not window_key:
        return Response({"error": "window_key required"}, status=status.HTTP_400_BAD_REQUEST)
    season = parse_int(request.GET.get("season"), default=None)

    games = Game.objects.filter(window_key=window_key)
    if season is not None:
        games = games.filter(season=season)
    props = PropBet.objects.filter(game__in=games)

    complete = games.filter(winner__isnull=True).count() == 0 and props.filter(correct_answer__isnull=True).count() == 0

    return Response(
        {
            "window_key": window_key,
            "season": season,
            "is_complete": complete,
            "games_total": games.count(),
            "games_completed": games.filter(winner__isnull=False).count(),
            "games_incomplete": list(games.filter(winner__isnull=True).values_list("id", flat=True)),
            "props_total": props.count(),
            "props_completed": props.filter(correct_answer__isnull=False).count(),
            "props_incomplete": list(props.filter(correct_answer__isnull=True).values_list("id", flat=True)),
        }
    )
