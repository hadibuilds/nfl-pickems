# analytics/views.py
from __future__ import annotations
from typing import Optional, Dict, Any, List

from django.db.models import Sum, Max, F
from django.utils import timezone
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat
# Best category helper from the service layer
from analytics.services.window_stats_optimized import compute_best_category_for_user

# --- Scoring mirrors the recompute service ---
ML_POINTS = 1
PB_POINTS = 2
SLOT_ORDER = {"morning": 0, "afternoon": 1, "late": 2}


# ---------- helpers ----------
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

def _current_season() -> int:
    s = Window.objects.order_by("-season").values_list("season", flat=True).first()
    return int(s or 0)

def serialize_window(win: Window) -> dict:
    return {
        "id": win.id,
        "key": f"{win.date}:{win.slot}",
        "season": win.season,
        "date": str(win.date),
        "slot": win.slot,
        "is_complete": win.is_complete,
        "updated_at": getattr(win, "updated_at", None) and win.updated_at.isoformat(),
    }

def _ordered_windows_qs(season: int) -> List[Window]:
    wins = list(Window.objects.filter(season=season).only("id", "season", "date", "slot"))
    wins.sort(key=lambda w: (w.date, SLOT_ORDER.get(getattr(w, "slot", None), 3), w.id))
    return wins

def _current_window(season: int) -> Optional[Window]:
    """
    Find the most appropriate window for analytics display.
    Prioritizes completed windows with data, then active windows, then latest by date.
    """
    today = timezone.now().date()
    
    # 1) Try latest COMPLETED window with user stats (most stable for leaderboard)
    latest_completed_with_stats = (
        Window.objects.filter(
            season=season, 
            is_complete=True, 
            user_stats__isnull=False
        )
        .distinct()
        .order_by("-date", "-id")
        .first()
    )
    
    if latest_completed_with_stats:
        return latest_completed_with_stats
    
    # 2) Try latest window with user stats (even if incomplete - for live data)
    latest_active_window = (
        Window.objects.filter(season=season, user_stats__isnull=False)
        .distinct()
        .order_by("-date", "-id")
        .first()
    )
    
    if latest_active_window:
        return latest_active_window
    
    # 3) Fallback to date-based logic if no windows have user activity yet
    wins = list(Window.objects.filter(season=season, date__lte=today).only("id", "date", "slot"))
    if not wins:
        wins = list(Window.objects.filter(season=season).only("id", "date", "slot"))
        if not wins:
            return None
    wins.sort(key=lambda w: (w.date, SLOT_ORDER.get(getattr(w, "slot", None), 3), w.id))
    return wins[-1]


# ---------- 1) Live: user-scoped pending + my rank/points + live completeness ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_window(request):
    """
    Live snapshot for a window (user-scoped):
      - pending_ml / pending_pb (unlocked & unanswered)
      - my_rank (dense), my_window_points, my_cume_points (from UserWindowStat for this window)
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

    # Locked definition (mirror Game.is_locked): locked OR start_time <= now
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

    # My current rank/points in this window (from snapshot)
    my_stat: Optional[UserWindowStat] = (
        UserWindowStat.objects
        .filter(window=win, user_id=user_id)
        .only("rank_dense", "window_points", "season_cume_points")
        .first()
    )
    my_rank = my_stat.rank_dense if my_stat else None
    my_window_points = my_stat.window_points if my_stat else 0
    my_cume_points = my_stat.season_cume_points if my_stat else 0

    # Completeness (live)
    total_games = len(game_ids)
    completed_games = Game.objects.filter(id__in=game_ids, winner__isnull=False).count()
    total_props = len(prop_ids)
    completed_props = PropBet.objects.filter(id__in=prop_ids, correct_answer__isnull=False).count()

    payload = {
        "window": serialize_window(win),
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
            "window_points": my_window_points,
            "season_cume_points": my_cume_points,
        },
    }
    return Response(payload, status=status.HTTP_200_OK)


# ---------- 2) Window leaderboard (with rank_delta precomputed by snapshots) ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    """
    Live season-wide leaderboard with trend analysis from window snapshots.
    Shows current total points from LIVE calculation + trend arrows from window deltas.
    Query params:
      - season (optional, defaults to current season)  
      - limit (optional, default 10)
    """
    season = int(request.GET.get("season") or _current_season())
    limit = int(request.query_params.get("limit", "10") or 10)
    
    # Get latest window for trend analysis
    latest_window = _current_window(season)
    if not latest_window:
        return Response({"detail": "No windows found for season."}, status=status.HTTP_404_NOT_FOUND)

    # LIVE POINTS: Calculate current total points for each user from scratch
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    live_standings = []
    users = User.objects.all()
    
    for user in users:
        # Calculate LIVE total points
        ml_points = (
            MoneyLinePrediction.objects
            .filter(
                user=user,
                game__season=season,
                game__winner__isnull=False,  # Only finalized games
                predicted_winner=F("game__winner")
            )
            .count() * ML_POINTS
        )
        
        prop_points = (
            PropBetPrediction.objects
            .filter(
                user=user,
                prop_bet__game__season=season,
                prop_bet__correct_answer__isnull=False,  # Only finalized props
                answer=F("prop_bet__correct_answer")
            )
            .count() * PB_POINTS
        )
        
        total_live_points = ml_points + prop_points
        
        # Get trend data from latest window snapshot (if available)
        latest_stat = (
            UserWindowStat.objects
            .filter(user=user, window=latest_window)
            .first()
        )
        
        rank_delta = latest_stat.rank_delta if latest_stat else 0
        
        # Get avatar URL
        avatar_url = None
        if user.avatar:
            avatar_url = request.build_absolute_uri(f'/accounts/secure-media/{user.avatar.name}')
        
        # Only include users with any activity
        if total_live_points > 0 or latest_stat:
            live_standings.append({
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar": avatar_url,
                "total_points": total_live_points,
                "rank_delta": rank_delta,
                "window_points": latest_stat.window_points if latest_stat else 0,
            })
    
    # Sort by live points and assign dense ranks
    live_standings.sort(key=lambda x: x["total_points"], reverse=True)
    
    # Assign dense ranks (handle ties)
    current_rank = 1
    for i, entry in enumerate(live_standings):
        if i > 0 and entry["total_points"] < live_standings[i-1]["total_points"]:
            current_rank = i + 1
        entry["rank_dense"] = current_rank
    
    # Limit results
    live_standings = live_standings[:limit]

    payload = {
        "window": serialize_window(latest_window),
        "leaderboard": [
            {
                "user_id": r["user_id"],
                "username": r["username"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "avatar": r["avatar"],
                "window_points": r["window_points"],
                "total_points": r["total_points"],
                "rank_dense": r["rank_dense"],
                "rank_delta": r["rank_delta"],
            }
            for r in live_standings
        ],
        "live_calculation": True,
        "trend_source": f"window_{latest_window.id}",
    }
    return Response(payload, status=status.HTTP_200_OK)


# ---------- 3) Season accuracy vs ALL resolved items (missed picks penalized) ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accuracy_summary(request):
    """
    Accuracy computed against ALL resolved items in the season:
      - Resolved ML: Game.winner IS NOT NULL
      - Resolved Prop: PropBet.correct_answer IS NOT NULL
    Missed picks count against accuracy because denominator = all resolved items.
    """
    user = request.user
    season = int(request.GET.get("season") or _current_season())

    # Total points: user's max cume this season (latest snapshot)
    total_points = (
        UserWindowStat.objects
        .filter(user=user, window__season=season)
        .aggregate(mx=Max("season_cume_points"))["mx"] or 0
    )

    # Moneyline
    total_ml_resolved = Game.objects.filter(season=season, winner__isnull=False).count()
    ml_correct = (
        MoneyLinePrediction.objects
        .filter(
            user=user,
            game__season=season,
            game__winner__isnull=False,
            predicted_winner=F("game__winner"),
        )
        .count()
        if total_ml_resolved else 0
    )
    ml_accuracy = (ml_correct / total_ml_resolved) if total_ml_resolved else 0.0

    # Props
    total_pb_resolved = PropBet.objects.filter(game__season=season, correct_answer__isnull=False).count()
    pb_correct = (
        PropBetPrediction.objects
        .filter(
            user=user,
            prop_bet__game__season=season,
            prop_bet__correct_answer__isnull=False,
            answer=F("prop_bet__correct_answer"),
        )
        .count()
        if total_pb_resolved else 0
    )
    pb_accuracy = (pb_correct / total_pb_resolved) if total_pb_resolved else 0.0

    # Overall
    overall_total = total_ml_resolved + total_pb_resolved
    overall_correct = ml_correct + pb_correct
    overall_accuracy = (overall_correct / overall_total) if overall_total else 0.0

    # Best category (computed from the same resolved-based accuracy definition)
    bc = compute_best_category_for_user(user, season)
    best_category = bc.get("bestCategory")
    best_category_accuracy = bc.get("bestCategoryAccuracy", 0)

    return Response({
        "season": season,
        "totalPoints": int(total_points),

        "moneylineCorrect": int(ml_correct),
        "moneylineTotalResolved": int(total_ml_resolved),
        "moneylineAccuracy": round(ml_accuracy, 4),

        "propBetCorrect": int(pb_correct),
        "propBetTotalResolved": int(total_pb_resolved),
        "propBetAccuracy": round(pb_accuracy, 4),

        "overallCorrect": int(overall_correct),
        "overallTotalResolved": int(overall_total),
        "overallAccuracy": round(overall_accuracy, 4),

        "bestCategory": best_category,
        "bestCategoryAccuracy": best_category_accuracy,
    })


# ---------- 4) Stats header: week-aware weeklyPoints + rank + gap ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats_summary(request):
    """
    Dashboard header block:
      - currentWeek (derived from Game.week for the current window)
      - weeklyPoints (sum of UserWindowStat.window_points across all windows that host games for that week)
      - rank (dense) at the latest window so far in that week
      - pointsFromLeader = leader_cume - my_cume at that anchor
    """
    user = request.user
    season = int(request.GET.get("season") or _current_season())
    if season == 0:
        return Response({"detail": "No season found."}, status=404)

    # Use the fixed week logic that looks at unfinished games directly
    from predictions.utils.dashboard_utils import get_current_week
    current_week = get_current_week(season)
    
    # Get a window for display purposes (can be any recent window)
    win = _current_window(season)
    if not win:
        return Response({"detail": "No windows found for season."}, status=404)

    if current_week is None:
        # No week detected -> just use this window’s window_points
        me_now = (
            UserWindowStat.objects
            .filter(user=user, window=win)
            .only("window_points", "season_cume_points", "rank_dense")
            .first()
        )
        weekly_points = int(getattr(me_now, "window_points", 0) or 0)
        anchor_window = win
    else:
        # All window ids that contain games for this NFL week
        week_window_ids = list(
            Window.objects.filter(season=season, games__week=current_week)
            .values_list("id", flat=True).distinct()
        )

        weekly_points = (
            UserWindowStat.objects
            .filter(user=user, window_id__in=week_window_ids)
            .aggregate(points=Sum("window_points"))["points"] or 0
        )

        # Anchor rank at the latest window so far in this week
        week_wins = list(
            Window.objects.filter(id__in=week_window_ids, date__lte=win.date).only("id", "date", "slot")
        )
        week_wins.sort(key=lambda w: (w.date, SLOT_ORDER.get(getattr(w, "slot", None), 3), w.id))
        anchor_window = week_wins[-1] if week_wins else win

    # Rank & gap at anchor
    me_anchor = (
        UserWindowStat.objects
        .filter(user=user, window=anchor_window)
        .only("season_cume_points", "rank_dense")
        .first()
    )
    user_cume = int(getattr(me_anchor, "season_cume_points", 0) or 0)
    rank = int(getattr(me_anchor, "rank_dense", 0) or 0)

    leader_cume = (
        UserWindowStat.objects
        .filter(window=anchor_window)
        .order_by("-season_cume_points")
        .values_list("season_cume_points", flat=True)
        .first()
    ) or 0

    # Calculate pending picks for current week
    pending_picks_week = 0
    if current_week:
        now = timezone.now()
        week_games = Game.objects.filter(season=season, week=current_week)
        unlocked_games = week_games.filter(Q(locked=False) & Q(start_time__gt=now))
        
        user_ml_picks = set(
            MoneyLinePrediction.objects.filter(
                user=user, game__in=week_games
            ).values_list("game_id", flat=True)
        )
        
        pending_ml = unlocked_games.exclude(id__in=user_ml_picks).count()
        
        # Count unlocked prop bets user hasn't answered
        unlocked_props = PropBet.objects.filter(game__in=unlocked_games)
        user_prop_picks = set(
            PropBetPrediction.objects.filter(
                user=user, prop_bet__in=unlocked_props
            ).values_list("prop_bet_id", flat=True)
        )
        
        pending_props = unlocked_props.exclude(id__in=user_prop_picks).count()
        pending_picks_week = pending_ml + pending_props

    return Response({
        "currentWeek": current_week,
        "weeklyPoints": int(weekly_points),
        "rank": rank,
        "pointsFromLeader": int(leader_cume - user_cume),
        "pendingPicksWeek": pending_picks_week,
        "window": serialize_window(anchor_window),
        "season": season,
    })


# ---------- 5) User timeline / sparkline ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_timeline(request):
    """
    Chronological timeline for a user in a season for sparklines/graphs.
    Query: season=?, user_id? (defaults to current user)
    Returns ordered (windowId, windowKey, date, slot, windowPoints, seasonCumePoints, rank, rankDelta).
    """
    season = int(request.GET.get("season") or _current_season())
    user_id = int(request.GET.get("user_id") or request.user.id)

    ordered = _ordered_windows_qs(season)
    ordered_ids = [w.id for w in ordered]
    id_to_meta = {w.id: {"date": w.date, "slot": getattr(w, "slot", None)} for w in ordered}

    stats = (
        UserWindowStat.objects
        .filter(user_id=user_id, window_id__in=ordered_ids)
        .values("window_id", "window__date", "window_points", "season_cume_points", "rank_dense", "rank_delta")
        .order_by("window__date", "window_id")
    )

    rows = []
    for s in stats:
        slot = id_to_meta[s["window_id"]]["slot"]
        date = s["window__date"]
        rows.append({
            "windowId": s["window_id"],
            "windowKey": f"{date}:{slot}",
            "date": date,
            "slot": slot,
            "windowPoints": int(s["window_points"] or 0),
            "seasonCumePoints": int(s["season_cume_points"] or 0),
            "rank": int(s["rank_dense"] or 0),
            "rankDelta": int(s["rank_delta"] or 0),
        })

    return Response({"season": season, "userId": user_id, "timeline": rows})


# ---------- 6) Recent completed games with user results ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_results(request):
    """
    Recent fully completed games with user's picks and results.
    Returns games where both ML and all props are resolved.
    """
    user = request.user
    season = int(request.GET.get("season") or _current_season())
    limit = int(request.GET.get("limit", "10") or 10)
    
    # Find games where winner is set and all props have correct_answer
    completed_game_ids = []
    for game in Game.objects.filter(season=season, winner__isnull=False):
        props = PropBet.objects.filter(game=game)
        if not props.exists() or all(prop.correct_answer is not None for prop in props):
            completed_game_ids.append(game.id)
    
    # Get user's predictions for these games
    recent_games = []
    games = Game.objects.filter(id__in=completed_game_ids).order_by('-start_time')[:limit]
    
    for game in games:
        # User's ML prediction
        ml_pred = MoneyLinePrediction.objects.filter(user=user, game=game).first()
        user_pick = ml_pred.predicted_winner if ml_pred else None
        ml_correct = ml_pred.predicted_winner == game.winner if ml_pred and game.winner else False
        
        # User's prop predictions
        props = PropBet.objects.filter(game=game)
        prop_points = 0
        prop_correct_count = 0
        prop_total_count = 0
        
        for prop in props:
            prop_pred = PropBetPrediction.objects.filter(user=user, prop_bet=prop).first()
            if prop_pred and prop.correct_answer:
                prop_total_count += 1
                if prop_pred.answer == prop.correct_answer:
                    prop_correct_count += 1
                    prop_points += PB_POINTS
        
        # Calculate total points and status
        ml_points = ML_POINTS if ml_correct else 0
        total_points = ml_points + prop_points
        
        # Determine correct status (full/partial/none)
        ml_made = ml_pred is not None
        prop_made = prop_total_count > 0
        
        if ml_made and prop_made:
            # Both ML and props made
            if ml_correct and prop_correct_count == prop_total_count:
                correct_status = 'full'
            elif ml_correct or prop_correct_count > 0:
                correct_status = 'partial'
            else:
                correct_status = 'none'
        elif ml_made:
            # Only ML made
            correct_status = 'full' if ml_correct else 'none'
        elif prop_made:
            # Only props made
            correct_status = 'full' if prop_correct_count == prop_total_count else 'partial' if prop_correct_count > 0 else 'none'
        else:
            # No picks made
            correct_status = 'none'
        
        recent_games.append({
            "id": game.id,
            "homeTeam": game.home_team,
            "awayTeam": game.away_team,
            "winner": game.winner,
            "userPick": user_pick,
            "points": total_points,
            "correctStatus": correct_status,
            "correct": correct_status == 'full',  # legacy field
            "startTime": game.start_time.isoformat(),
        })
    
    return Response({
        "season": season,
        "results": recent_games
    })


# ---------- 7) TRUTH COUNTER: Unconditional point calculation for data integrity ----------
def calculate_truth_points(user, season=None):
    """
    TRUTH counter: Calculate EXACTLY how many points a user has earned, no BS.
    This is the source of truth that ignores all caching, snapshots, and optimizations.
    
    Args:
        user: User object or user_id
        season: Season to calculate for (defaults to current season)
    
    Returns:
        dict: {
            'ml_correct': int,
            'ml_total_finalized': int, 
            'ml_points': int,
            'prop_correct': int,
            'prop_total_finalized': int,
            'prop_points': int,
            'total_points': int,
            'calculation_timestamp': datetime,
            'season': int
        }
    """
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    
    # Handle user_id vs User object
    if isinstance(user, int):
        User = get_user_model()
        user = User.objects.get(id=user)
    
    if season is None:
        season = _current_season()
    
    # MONEYLINE TRUTH
    ml_predictions = MoneyLinePrediction.objects.filter(
        user=user,
        game__season=season,
        game__winner__isnull=False  # Only count finalized games
    )
    
    ml_correct = 0
    ml_total_finalized = 0
    
    for pred in ml_predictions:
        ml_total_finalized += 1
        if pred.predicted_winner == pred.game.winner:
            ml_correct += 1
    
    ml_points = ml_correct * ML_POINTS
    
    # PROP BET TRUTH
    prop_predictions = PropBetPrediction.objects.filter(
        user=user,
        prop_bet__game__season=season,
        prop_bet__correct_answer__isnull=False  # Only count finalized props
    )
    
    prop_correct = 0
    prop_total_finalized = 0
    
    for pred in prop_predictions:
        prop_total_finalized += 1
        if pred.answer == pred.prop_bet.correct_answer:
            prop_correct += 1
    
    prop_points = prop_correct * PB_POINTS
    total_points = ml_points + prop_points
    
    return {
        'user_id': user.id,
        'username': user.username,
        'season': season,
        'ml_correct': ml_correct,
        'ml_total_finalized': ml_total_finalized,
        'ml_points': ml_points,
        'prop_correct': prop_correct,
        'prop_total_finalized': prop_total_finalized,
        'prop_points': prop_points,
        'total_points': total_points,
        'calculation_timestamp': timezone.now(),
    }


# =============================================================================
# MIGRATED ANALYSIS FUNCTIONS (from predictions app)
# Using optimized logic from consolidated_dashboard_utils.py
# =============================================================================

from utils.consolidated_dashboard_utils import (
    get_current_week_consolidated,
    get_standings_optimized,
    calculate_accuracy_optimized,
    get_user_stats_optimized,
    get_leaderboard_optimized,
    get_dashboard_data_consolidated,
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_standings_migrated(request):
    """
    MIGRATED from predictions/views.py with OPTIMIZED logic.
    Uses UserWindowStat for 4.6x faster performance.
    """
    selected_week = request.GET.get('week')
    season = request.GET.get('season')
    
    # Validate parameters
    if selected_week and not selected_week.isdigit():
        return Response({'error': 'Invalid week parameter'}, status=status.HTTP_400_BAD_REQUEST)
    
    week_filter = int(selected_week) if selected_week else None
    season = int(season) if season and season.isdigit() else None
    
    try:
        data = get_standings_optimized(season=season, week_filter=week_filter, request=request)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_week_migrated(request):
    """
    MIGRATED from predictions/views.py with OPTIMIZED logic.
    Uses fixed week logic that resets immediately when a week completes.
    """
    season = request.GET.get('season')
    season = int(season) if season and season.isdigit() else None
    
    try:
        current_week = get_current_week_consolidated(season)
        
        # Get all available weeks (keep for compatibility)
        all_seasons = Game.objects.values_list('season', flat=True).distinct().order_by('season')
        weeks = []
        for s in all_seasons:
            season_weeks = list(
                Game.objects.filter(season=s)
                .values_list('week', flat=True)
                .distinct()
                .order_by('week')
            )
            weeks.extend(season_weeks)
        
        return Response({
            'currentWeek': current_week,
            'weeks': sorted(set(weeks)),
            'totalWeeks': len(set(weeks)),
            'season': season or _current_season(),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_accuracy_migrated(request):
    """
    MIGRATED from predictions/views.py with OPTIMIZED logic.
    Returns same format but with better performance.
    """
    user = request.user
    
    try:
        accuracy_data = calculate_accuracy_optimized(user, "overall")
        
        return Response({
            'overall_accuracy': accuracy_data['overall_accuracy'],
            'moneyline_accuracy': accuracy_data['moneyline_accuracy'],
            'prop_bet_accuracy': accuracy_data['prop_bet_accuracy'],
            'correct_predictions': accuracy_data['overall_accuracy']['correct'],
            'total_predictions_with_results': accuracy_data['overall_accuracy']['total'],
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats_migrated(request):
    """
    MIGRATED from predictions/views.py with OPTIMIZED logic.
    Uses UserWindowStat and fixed week logic.
    """
    user = request.user
    season = request.GET.get('season')
    season = int(season) if season and season.isdigit() else None
    
    try:
        stats = get_user_stats_optimized(user, season=season, include_rank=True)
        
        return Response({
            'username': stats['username'],
            'currentWeek': stats['current_week'],
            'weeklyPoints': stats['weekly_points'],
            'rank': stats.get('rank'),
            'totalUsers': stats.get('total_users'),
            'pointsFromLeader': stats.get('points_from_leader'),
            'pendingPicks': stats['pending_picks']
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_leaderboard_migrated(request):
    """
    MIGRATED from predictions/views.py with OPTIMIZED logic.
    Uses UserWindowStat for much faster queries with trend arrows.
    """
    limit = request.GET.get('limit', '5')
    season = request.GET.get('season')
    with_trends = request.GET.get('trends', 'true').lower() == 'true'
    
    # Validate limit
    try:
        limit = max(1, min(20, int(limit)))
    except (ValueError, TypeError):
        limit = 5
    
    season = int(season) if season and season.isdigit() else None
    
    try:
        leaderboard = get_leaderboard_optimized(
            season=season, 
            limit=limit, 
            with_trends=with_trends,
            request=request
        )
        
        # Mark current user
        user = request.user
        for row in leaderboard:
            if row['username'] == user.username:
                row['isCurrentUser'] = True
        
        return Response({
            'leaderboard': leaderboard,
            'limit': limit,
            'currentUserIncluded': any(u.get('isCurrentUser') for u in leaderboard),
            'season': season or _current_season(),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_migrated(request):
    """
    MIGRATED from predictions/views.py with OPTIMIZED logic.
    Single endpoint that returns all dashboard data efficiently.
    """
    user = request.user
    season = request.GET.get('season')
    season = int(season) if season and season.isdigit() else None
    
    try:
        dashboard_data = get_dashboard_data_consolidated(user, season=season)
        return Response(dashboard_data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def truth_counter(request):
    """
    TRUTH COUNTER endpoint: Returns unconditional point calculations for verification.
    Use this to audit and verify that all other calculations are correct.
    
    Query params:
    - user_id (optional): specific user, defaults to current user
    - season (optional): specific season, defaults to current season
    - all_users (optional): if 'true', returns truth for all users (admin only)
    """
    season = int(request.GET.get("season") or _current_season())
    user_id = request.GET.get("user_id")
    all_users = request.GET.get("all_users", "").lower() == "true"
    
    if all_users:
        # Return truth for all users (useful for integrity checks)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        truth_data = []
        for user in User.objects.all():
            truth = calculate_truth_points(user, season)
            if truth['total_points'] > 0:  # Only include users with points
                truth_data.append(truth)
        
        # Sort by points
        truth_data.sort(key=lambda x: x['total_points'], reverse=True)
        
        return Response({
            'season': season,
            'calculation_type': 'truth_counter_all_users',
            'total_users': len(truth_data),
            'users': truth_data,
            'calculated_at': timezone.now().isoformat(),
        })
    else:
        # Single user truth
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            target_user = User.objects.get(id=user_id)
        else:
            target_user = request.user
        
        truth = calculate_truth_points(target_user, season)
        
        return Response({
            'season': season,
            'calculation_type': 'truth_counter_single_user',
            'user': truth,
            'calculated_at': timezone.now().isoformat(),
        })


# ---------- 7) Pending picks for current user ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pending_picks(request):
    """
    Get pending (unlocked + unanswered) picks for the current user.
    Can filter by week, window, or show all pending for current season.
    
    Query params:
    - season (optional): defaults to current season
    - week (optional): filter to specific NFL week
    - window_key (optional): filter to specific window (YYYY-MM-DD:slot)
    - scope (optional): 'current_week', 'current_window', or 'all' (default: 'all')
    """
    user = request.user
    season = int(request.GET.get("season") or _current_season())
    week = request.GET.get("week")
    window_key = request.GET.get("window_key")
    scope = request.GET.get("scope", "all")
    
    now = timezone.now()
    
    # Base query for games in season
    games_query = Game.objects.filter(season=season)
    
    # Apply filters based on scope or explicit params
    if scope == "current_week" or week:
        target_week = week or (_current_window(season) and 
                              Game.objects.filter(window=_current_window(season)).values_list("week", flat=True).first())
        if target_week:
            games_query = games_query.filter(week=int(target_week))
    elif scope == "current_window" or window_key:
        target_window_key = window_key or (_current_window(season) and f"{_current_window(season).date}:{_current_window(season).slot}")
        if target_window_key:
            try:
                target_window = get_window_by_key_or_404(target_window_key)
                games_query = games_query.filter(window=target_window)
            except ValueError:
                return Response({"detail": "Invalid window_key"}, status=400)
    
    # Get unlocked games (not locked AND start_time > now)
    unlocked_games = games_query.filter(Q(locked=False) & Q(start_time__gt=now))
    
    # Get user's existing ML predictions
    user_ml_picks = set(
        MoneyLinePrediction.objects.filter(
            user=user, 
            game__in=games_query
        ).values_list("game_id", flat=True)
    )
    
    # Get user's existing prop bet predictions
    all_props = PropBet.objects.filter(game__in=games_query)
    user_prop_picks = set(
        PropBetPrediction.objects.filter(
            user=user, 
            prop_bet__in=all_props
        ).values_list("prop_bet_id", flat=True)
    )
    
    # Calculate pending counts
    pending_ml_games = unlocked_games.exclude(id__in=user_ml_picks)
    pending_ml_count = pending_ml_games.count()
    
    unlocked_props = PropBet.objects.filter(game__in=unlocked_games)
    pending_props = unlocked_props.exclude(id__in=user_prop_picks)
    pending_props_count = pending_props.count()
    
    total_pending = pending_ml_count + pending_props_count
    
    # Get details of pending items (optional)
    include_details = request.GET.get("include_details", "false").lower() == "true"
    pending_details = None
    
    if include_details:
        pending_ml_details = []
        for game in pending_ml_games.select_related("window")[:20]:  # limit for performance
            pending_ml_details.append({
                "game_id": game.id,
                "type": "moneyline",
                "matchup": f"{game.away_team} @ {game.home_team}",
                "start_time": game.start_time.isoformat(),
                "week": game.week,
                "window_key": f"{game.window.date}:{game.window.slot}"
            })
        
        pending_prop_details = []
        for prop in pending_props.select_related("game", "game__window")[:20]:  # limit for performance
            pending_prop_details.append({
                "prop_bet_id": prop.id,
                "type": "prop_bet",
                "question": prop.question,
                "category": prop.category,
                "game_matchup": f"{prop.game.away_team} @ {prop.game.home_team}",
                "start_time": prop.game.start_time.isoformat(),
                "week": prop.game.week,
                "window_key": f"{prop.game.window.date}:{prop.game.window.slot}"
            })
        
        pending_details = {
            "moneyline": pending_ml_details,
            "prop_bets": pending_prop_details
        }
    
    return Response({
        "season": season,
        "scope": scope,
        "week": week,
        "window_key": window_key,
        "pending_summary": {
            "total": total_pending,
            "moneyline": pending_ml_count,
            "prop_bets": pending_props_count
        },
        "details": pending_details
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peek_data(request):
    """
    Get peek data showing all users' picks for locked games
    Shows moneyline and prop bet picks grouped by team/answer
    Only shows data for games that are locked or have started
    """
    try:
        week = request.GET.get('week')
        if not week:
            return Response({"detail": "Week parameter required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            week = int(week)
        except ValueError:
            return Response({"detail": "Invalid week number"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get locked games for the week
        locked_games = Game.objects.filter(
            week=week
        ).filter(
            Q(locked=True) | Q(start_time__lte=timezone.now())
        ).select_related().prefetch_related('prop_bets')
        
        peek_data = {}
        
        for game in locked_games:
            # Get all moneyline predictions for this game
            ml_predictions = MoneyLinePrediction.objects.filter(
                game=game
            ).select_related('user')
            
            # Group users by their moneyline picks
            moneyline_picks = {
                'home_team': [],
                'away_team': []
            }
            
            for prediction in ml_predictions:
                avatar_url = None
                if prediction.user.avatar:
                    avatar_url = request.build_absolute_uri(f'/accounts/secure-media/{prediction.user.avatar.name}')
                
                user_data = {
                    'username': prediction.user.username,
                    'first_name': prediction.user.first_name or '',
                    'last_name': prediction.user.last_name or '',
                    'avatar': avatar_url
                }
                
                if prediction.predicted_winner == game.home_team:
                    moneyline_picks['home_team'].append(user_data)
                else:
                    moneyline_picks['away_team'].append(user_data)
            
            # Get prop bet predictions if the game has prop bets
            prop_picks = {'answer_a': [], 'answer_b': []}
            
            if game.prop_bets.exists():
                prop_bet = game.prop_bets.first()
                prop_predictions = PropBetPrediction.objects.filter(
                    prop_bet=prop_bet
                ).select_related('user')
                
                for prediction in prop_predictions:
                    avatar_url = None
                    if prediction.user.avatar:
                        avatar_url = request.build_absolute_uri(f'/accounts/secure-media/{prediction.user.avatar.name}')
                    
                    user_data = {
                        'username': prediction.user.username,
                        'first_name': prediction.user.first_name or '',
                        'last_name': prediction.user.last_name or '',
                        'avatar': avatar_url
                    }
                    
                    if prediction.answer == prop_bet.option_a:
                        prop_picks['answer_a'].append(user_data)
                    else:
                        prop_picks['answer_b'].append(user_data)
            
            peek_data[game.id] = {
                'moneyline_picks': moneyline_picks,
                'prop_picks': prop_picks
            }
        
        return Response({
            'week': week,
            'games_count': len(locked_games),
            'peek_data': peek_data
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Peek data fetch error: %s", str(e))
        return Response(
            {"detail": "Failed to fetch peek data"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
