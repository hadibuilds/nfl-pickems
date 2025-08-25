# predictions/views.py - Snapshot season endpoints implemented inline (no missing imports)
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Max
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from games.models import Game
from .models import (
    Prediction,
    PropBet,
    PropBetPrediction,
    WeeklySnapshot,        # in case used it elsewhere
    UserStatHistory,       # snapshot history per user/week
)

# ======== Realtime & existing helpers you already had ========
from .utils.dashboard_utils import (
    # Realtime (primary)
    calculate_user_dashboard_data_realtime,
    calculate_total_points_simple,
    get_leaderboard_data_realtime,
    get_user_insights_realtime,
    get_current_week,
    calculate_live_stats,
    calculate_current_user_rank_realtime,
    get_best_category_realtime,
    calculate_current_accuracy,
    calculate_pending_picks,
    get_recent_games_data,
    get_user_rank_achievements,
    get_user_season_stats,              # existing season summary (non-snapshot-fast)
    # Snapshot (optional)
    get_leaderboard_data_with_trends,
    calculate_user_dashboard_data,
    get_user_insights,
)

User = get_user_model()

# =============================================================================
# PREDICTION MANAGEMENT ENDPOINTS (unchanged)
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_prediction(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    predicted_winner = request.data.get('predicted_winner')
    if not predicted_winner:
        return Response({'error': 'No team selected'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        prediction, created = Prediction.objects.update_or_create(
            user=request.user,
            game=game,
            defaults={'predicted_winner': predicted_winner}
        )
        return Response({'success': True, 'action': 'created' if created else 'updated', 'prediction_id': prediction.id})
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_prop_bet(request, prop_bet_id):
    prop_bet = get_object_or_404(PropBet, pk=prop_bet_id)
    answer = request.data.get('answer')
    if not answer:
        return Response({'error': 'No answer provided'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        prop_prediction, created = PropBetPrediction.objects.update_or_create(
            user=request.user,
            prop_bet=prop_bet,
            defaults={'answer': answer}
        )
        return Response({'success': True, 'action': 'created' if created else 'updated', 'prediction_id': prop_prediction.id})
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_user_selection(request):
    data = request.data
    results = []

    if data.get('game_id') and data.get('predicted_winner'):
        game = get_object_or_404(Game, pk=data['game_id'])
        try:
            prediction, created = Prediction.objects.update_or_create(
                user=request.user, game=game, defaults={'predicted_winner': data['predicted_winner']}
            )
            results.append({'type': 'moneyline', 'success': True, 'action': 'created' if created else 'updated'})
        except ValueError as e:
            results.append({'type': 'moneyline', 'success': False, 'error': str(e)})

    if data.get('prop_bet_id') and data.get('answer'):
        prop_bet = get_object_or_404(PropBet, pk=data['prop_bet_id'])
        try:
            prop_prediction, created = PropBetPrediction.objects.update_or_create(
                user=request.user, prop_bet=prop_bet, defaults={'answer': data['answer']}
            )
            results.append({'type': 'prop_bet', 'success': True, 'action': 'created' if created else 'updated'})
        except ValueError as e:
            results.append({'type': 'prop_bet', 'success': False, 'error': str(e)})

    if not results:
        return Response({'error': 'No valid predictions provided'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True, 'results': results})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_predictions(request):
    user = request.user
    predictions = Prediction.objects.filter(user=user).select_related('game')
    prop_bet_selections = PropBetPrediction.objects.filter(user=user).select_related('prop_bet__game')

    predictions_data = [
        {'game_id': p.game.id, 'predicted_winner': p.predicted_winner, 'week': p.game.week, 'is_correct': p.is_correct}
        for p in predictions
    ]
    prop_bet_data = [
        {'prop_bet_id': pb.prop_bet.id, 'answer': pb.answer, 'week': pb.prop_bet.game.week, 'is_correct': pb.is_correct}
        for pb in prop_bet_selections
    ]

    return Response({
        'predictions': predictions_data,
        'prop_bets': prop_bet_data,
        'total_predictions': len(predictions_data) + len(prop_bet_data)
    })

# =============================================================================
# STANDINGS & RESULTS (unchanged)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_standings(request):
    selected_week = request.GET.get('week')
    if selected_week and not selected_week.isdigit():
        return Response({'error': 'Invalid week parameter'}, status=status.HTTP_400_BAD_REQUEST)

    users = User.objects.all()
    standings = []
    all_weeks = set()

    for user in users:
        weekly_scores = defaultdict(int)

        for pred in Prediction.objects.filter(user=user, is_correct=True).select_related('game'):
            weekly_scores[pred.game.week] += 1
            all_weeks.add(pred.game.week)

        for prop in PropBetPrediction.objects.filter(user=user, is_correct=True).select_related('prop_bet__game'):
            w = prop.prop_bet.game.week
            weekly_scores[w] += 2
            all_weeks.add(w)

        total = weekly_scores[int(selected_week)] if selected_week else sum(weekly_scores.values())
        standings.append({'username': user.username, 'weekly_scores': dict(weekly_scores), 'total_points': total})

    standings.sort(key=lambda x: (-x['total_points'], x['username'].lower()))
    all_weeks = sorted(all_weeks)

    return Response({
        'standings': standings,
        'weeks': all_weeks,
        'selected_week': int(selected_week) if selected_week else None,
        'total_users': len(standings)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_game_results(request):
    try:
        completed_games = Game.objects.filter(winner__isnull=False).prefetch_related('prop_bets').order_by('-start_time')
        results = []
        for game in completed_games:
            prop_results = []
            for prop_bet in game.prop_bets.all():
                if prop_bet.correct_answer:
                    prop_results.append({
                        'prop_bet_id': prop_bet.id,
                        'question': prop_bet.question,
                        'correct_answer': prop_bet.correct_answer
                    })
            prop_result_alias = prop_results[0]['correct_answer'] if len(prop_results) == 1 else None
            results.append({
                'game_id': game.id,
                'week': game.week,
                'home_team': game.home_team,
                'away_team': game.away_team,
                'winning_team': game.winner,
                'winner': game.winner,
                'prop_bet_results': prop_results,
                'prop_result': prop_result_alias,
            })
        return Response({'results': results, 'total_completed_games': len(results)})
    except Exception as e:
        return Response({'error': f'Failed to fetch game results: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_accuracy(request):
    user = request.user
    moneyline_with_results = Prediction.objects.filter(user=user, is_correct__isnull=False)
    prop_bet_with_results = PropBetPrediction.objects.filter(user=user, is_correct__isnull=False)

    correct_ml = moneyline_with_results.filter(is_correct=True).count()
    total_ml = moneyline_with_results.count()

    correct_prop = prop_bet_with_results.filter(is_correct=True).count()
    total_prop = prop_bet_with_results.count()

    total_correct = correct_ml + correct_prop
    total_preds = total_ml + total_prop

    ml_pct = round((correct_ml / total_ml * 100), 1) if total_ml > 0 else 0
    prop_pct = round((correct_prop / total_prop * 100), 1) if total_prop > 0 else 0
    overall_pct = round((total_correct / total_preds * 100), 1) if total_preds > 0 else 0

    return Response({
        'overall_accuracy': {'percentage': overall_pct, 'correct': total_correct, 'total': total_preds},
        'moneyline_accuracy': {'percentage': ml_pct, 'correct': correct_ml, 'total': total_ml},
        'prop_bet_accuracy': {'percentage': prop_pct, 'correct': correct_prop, 'total': total_prop},
        'correct_predictions': total_correct,
        'total_predictions_with_results': total_preds,
    })

# =============================================================================
# UTILITY (unchanged)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_week_only(request):
    try:
        current = int(get_current_week())
        weeks = list(Game.objects.values_list('week', flat=True).distinct().order_by('week'))
        return Response({'currentWeek': current, 'weeks': weeks, 'totalWeeks': len(weeks)})
    except Exception as e:
        return Response({'error': f'Failed to get current week: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# GRANULAR DASHBOARD (unchanged)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats_only(request):
    try:
        user = request.user
        current_week = get_current_week()
        live_stats = calculate_live_stats(user, current_week)
        current_rank_info = calculate_current_user_rank_realtime(user, current_week)
        pending_picks = calculate_pending_picks(user, current_week)
        return Response({
            'username': user.username,
            'currentWeek': current_week,
            'weeklyPoints': live_stats['weekly_points'],
            'rank': current_rank_info['rank'],
            'totalUsers': current_rank_info['total_users'],
            'pointsFromLeader': current_rank_info['points_from_leader'],
            'pendingPicks': pending_picks
        })
    except Exception as e:
        return Response({'error': f'Failed to fetch user stats: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_accuracy_only(request):
    try:
        user = request.user
        best_category, best_accuracy = get_best_category_realtime(user)
        total_points = calculate_total_points_simple(user)
        return Response({
            'overallAccuracy': calculate_current_accuracy(user, 'overall'),
            'moneylineAccuracy': calculate_current_accuracy(user, 'moneyline'),
            'propBetAccuracy': calculate_current_accuracy(user, 'prop'),
            'totalPoints': total_points,
            'bestCategory': best_category,
            'bestCategoryAccuracy': best_accuracy,
        })
    except Exception as e:
        return Response({'error': f'Failed to fetch accuracy data: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_leaderboard_only(request):
    try:
        limit = min(int(request.GET.get('limit', 5)), 20)
        user = request.user
        leaderboard = get_leaderboard_data_realtime(limit=limit)
        for row in leaderboard:
            if row['username'] == user.username:
                row['isCurrentUser'] = True
        return Response({
            'leaderboard': leaderboard,
            'limit': limit,
            'currentUserIncluded': any(u.get('isCurrentUser') for u in leaderboard)
        })
    except Exception as e:
        return Response({'error': f'Failed to fetch leaderboard: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_games_only(request):
    try:
        user = request.user
        limit = min(int(request.GET.get('limit', 3)), 10)
        recent_games = get_recent_games_data(user, limit=limit)
        return Response({'recentGames': recent_games, 'limit': limit, 'totalGames': len(recent_games)})
    except Exception as e:
        return Response({'error': f'Failed to fetch recent games: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_insights_only(request):
    try:
        user = request.user
        insights = get_user_insights_realtime(user)
        season_stats = get_user_season_stats(user)
        achievements = get_user_rank_achievements(user)
        return Response({
            'insights': insights,
            'rankAchievements': {
                'currentRank': achievements.get('current_rank'),
                'consecutiveWeeksAt1': achievements.get('consecutive_weeks_at_1'),
                'consecutiveWeeksInTop3': achievements.get('consecutive_weeks_in_top_3'),
                'bestRank': achievements.get('best_rank'),
                'weeksAt1': achievements.get('weeks_at_1'),
                'weeksInTop3': achievements.get('weeks_in_top_3'),
                'biggestClimb': achievements.get('biggest_climb'),
                'totalWeeksTracked': achievements.get('total_weeks_tracked'),
            },
            'seasonStats': season_stats,
            'insightCount': len(insights)
        })
    except Exception as e:
        return Response({'error': f'Failed to fetch insights: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# MAIN DASHBOARD (unchanged)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    try:
        user = request.user
        mode = request.GET.get('mode', 'realtime').lower()
        sections_param = request.GET.get('sections', '')
        sections = [s.strip() for s in sections_param.split(',') if s.strip()] if sections_param else []
        response_data = {}

        if not sections:
            if mode == 'snapshot':
                dashboard_data = calculate_user_dashboard_data(user)
                leaderboard = get_leaderboard_data_with_trends(limit=5)
                insights = get_user_insights(user)
                calculation_mode = 'snapshot'
            else:
                dashboard_data = calculate_user_dashboard_data_realtime(user)
                leaderboard = get_leaderboard_data_realtime(limit=5)
                insights = get_user_insights_realtime(user)
                calculation_mode = 'realtime'

            for row in leaderboard:
                if row['username'] == user.username:
                    row['isCurrentUser'] = True

            response_data = {
                'user_data': dashboard_data,
                'leaderboard': leaderboard,
                'insights': insights,
                'trends': {
                    'performance_trend': dashboard_data.get('performanceTrend', 'stable'),
                    'weekly_trends': dashboard_data.get('weeklyTrends', []),
                    'rank_trend': dashboard_data.get('rankTrend', 'same')
                },
                'meta': {
                    'calculation_mode': calculation_mode,
                    'sections': 'all',
                    'timestamp': dashboard_data.get('currentWeek'),
                }
            }
        else:
            valid_sections = {'stats', 'accuracy', 'leaderboard', 'recent', 'insights'}
            invalid_sections = set(sections) - valid_sections
            if invalid_sections:
                return Response(
                    {'error': f'Invalid sections: {", ".join(invalid_sections)}. Valid options: {", ".join(valid_sections)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if 'stats' in sections:
                current_week = get_current_week()
                live_stats = calculate_live_stats(user, current_week)
                current_rank_info = calculate_current_user_rank_realtime(user, current_week)
                response_data.setdefault('user_data', {}).update({
                    'username': user.username,
                    'currentWeek': current_week,
                    'weeklyPoints': live_stats['weekly_points'],
                    'rank': current_rank_info['rank'],
                    'totalUsers': current_rank_info['total_users'],
                    'pointsFromLeader': current_rank_info['points_from_leader'],
                    'pendingPicks': calculate_pending_picks(user, current_week)
                })

            if 'accuracy' in sections:
                best_category, best_accuracy = get_best_category_realtime(user)
                response_data.setdefault('user_data', {}).update({
                    'overallAccuracy': calculate_current_accuracy(user, 'overall'),
                    'moneylineAccuracy': calculate_current_accuracy(user, 'moneyline'),
                    'propBetAccuracy': calculate_current_accuracy(user, 'prop'),
                    'bestCategory': best_category,
                    'bestCategoryAccuracy': best_accuracy,
                })

            if 'leaderboard' in sections:
                leaderboard = get_leaderboard_data_realtime(limit=5)
                for row in leaderboard:
                    if row['username'] == user.username:
                        row['isCurrentUser'] = True
                response_data['leaderboard'] = leaderboard

            if 'recent' in sections:
                response_data.setdefault('user_data', {})['recentGames'] = get_recent_games_data(user, limit=3)

            if 'insights' in sections:
                response_data['insights'] = get_user_insights_realtime(user)

            response_data['meta'] = {'calculation_mode': 'realtime', 'sections': sections, 'requested_sections': len(sections)}

        return Response(response_data)
    except Exception as e:
        return Response({'error': f'Failed to fetch dashboard data: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_realtime(request):
    try:
        user = request.user
        dashboard_data = calculate_user_dashboard_data_realtime(user)
        leaderboard = get_leaderboard_data_realtime(limit=5)
        insights = get_user_insights_realtime(user)

        for row in leaderboard:
            if row['username'] == user.username:
                row['isCurrentUser'] = True

        return Response({
            'user_data': dashboard_data,
            'leaderboard': leaderboard,
            'insights': insights,
            'trends': {
                'performance_trend': dashboard_data.get('performanceTrend', 'stable'),
                'weekly_trends': dashboard_data.get('weeklyTrends', []),
                'rank_trend': dashboard_data.get('rankTrend', 'same')
            },
            'meta': {
                'calculation_mode': 'realtime',
                'guaranteed_realtime': True,
                'timestamp': dashboard_data.get('currentWeek')
            }
        })
    except Exception as e:
        return Response({'error': f'Failed to fetch real-time dashboard data: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_snapshot(request):
    try:
        user = request.user
        dashboard_data = calculate_user_dashboard_data(user)
        leaderboard = get_leaderboard_data_with_trends(limit=5)
        insights = get_user_insights(user)

        for row in leaderboard:
            if row['username'] == user.username:
                row['isCurrentUser'] = True

        return Response({
            'user_data': dashboard_data,
            'leaderboard': leaderboard,
            'insights': insights,
            'trends': {
                'performance_trend': dashboard_data.get('performanceTrend', 'stable'),
                'weekly_trends': dashboard_data.get('weeklyTrends', []),
                'rank_trend': dashboard_data.get('rankTrend', 'same')
            },
            'meta': {'calculation_mode': 'snapshot', 'requires_snapshots': True, 'uses_historical_data': True}
        })
    except Exception as e:
        return Response({'error': f'Failed to fetch snapshot dashboard data: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# ADMIN (unchanged)
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_weekly_snapshot(request):
    if not request.user.is_staff:
        return Response({'error': 'Staff privileges required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        week = request.data.get('week')
        force = request.data.get('force', False)
        if week and not isinstance(week, int):
            return Response({'error': 'Week must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        if week:
            call_command('capture_weekly_snapshot', week=week, force=force)
            message = f"Snapshot captured for week {week}"
        else:
            call_command('capture_weekly_snapshot', force=force)
            message = "Snapshot captured for latest completed week"
        return Response({'success': True, 'message': message, 'week': week, 'forced': force})
    except Exception as e:
        return Response({'error': f'Failed to capture snapshot: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# SNAPSHOT-POWERED READS (implemented inline)
# =============================================================================

def _latest_user_stat_history(user, through_week=None):
    qs = UserStatHistory.objects.filter(user=user)
    if through_week is not None:
        qs = qs.filter(week__lte=through_week)
    # Prefer latest by week; fall back to max(id)
    stat = qs.order_by('-week').first() or qs.order_by('-id').first()
    return stat

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_season_stats_fast_view(request):
    """
    Season-to-date stats where the denominator comes from the schedule/results,
    not from user rows — so missed picks are implicitly counted as incorrect.

    Denominators:
      moneyline_den = count(Game) with winner set (completed)
      prop_den      = count(PropBet) whose game is completed AND correct_answer set

    Numerators:
      moneyline_num = user's correct moneyline predictions on those games
      prop_num      = user's correct prop predictions on those props

    Optional query:
      ?through_week=<int>  -> only include games/props up to and including this week
    """
    user = request.user

    # ----- (A) Resolve week ceiling -----
    # If caller provides ?through_week, use that; else try the latest snapshot week;
    # else fall back to max completed week.
    through_week_param = request.GET.get('through_week')
    try:
        through_week = int(through_week_param) if through_week_param is not None else None
    except ValueError:
        through_week = None

    latest_snap = UserStatHistory.objects.filter(user=user).order_by('-week').first()
    if through_week is None and latest_snap:
        through_week = getattr(latest_snap, 'week', None)

    # ----- (B) Base result sets (completed only) -----
    games_qs = Game.objects.filter(winner__isnull=False)
    if through_week is not None:
        games_qs = games_qs.filter(week__lte=through_week)

    # only props that actually resolved (have a correct answer) on completed games
    props_qs = PropBet.objects.filter(
        correct_answer__isnull=False,
        game__in=games_qs,
    )

    moneyline_den = games_qs.count()
    prop_den = props_qs.count()

    # ----- (C) Your correct picks (numerators) -----
    correct_ml = Prediction.objects.filter(
        user=user,
        is_correct=True,
        game__in=games_qs
    ).count()

    correct_prop = PropBetPrediction.objects.filter(
        user=user,
        is_correct=True,
        prop_bet__in=props_qs
    ).count()

    # ----- (D) Percentages -----
    def pct(num, den):
        return round((num / den) * 100, 1) if den > 0 else 0.0

    moneyline_pct = pct(correct_ml, moneyline_den)
    prop_pct = pct(correct_prop, prop_den)

    overall_num = correct_ml + correct_prop
    overall_den = moneyline_den + prop_den
    overall_pct = pct(overall_num, overall_den)

    # ----- (E) Trend + points from snapshot (optional, keeps your rank trend)
    trend = 'same'
    if latest_snap:
        prev_snap = UserStatHistory.objects.filter(user=user, week__lt=latest_snap.week).order_by('-week').first()
        if prev_snap and getattr(latest_snap, 'rank', None) and getattr(prev_snap, 'rank', None):
            delta = prev_snap.rank - latest_snap.rank  # positive = moved up
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

    season_points = getattr(latest_snap, 'total_points', 0) if latest_snap else 0
    if not season_points:
        # conservative fallback if snapshots not populated yet
        season_points = (
            Prediction.objects.filter(user=user, is_correct=True, game__in=games_qs).count() * 1
            + PropBetPrediction.objects.filter(user=user, is_correct=True, prop_bet__in=props_qs).count() * 2
        )

    return Response({
        'current_season_points': season_points,
        'current_season_accuracy': overall_pct,          # overall ring
        'current_moneyline_accuracy': moneyline_pct,     # ML ring
        'current_prop_accuracy': prop_pct,               # Prop ring
        'trending_direction': trend,
        'week': through_week,
        'rank': getattr(latest_snap, 'rank', None) if latest_snap else None,
        # useful for validating math
        'debug_counts': {
            'denominators': {'ml_games_completed': moneyline_den, 'props_resolved': prop_den, 'overall': overall_den},
            'numerators': {'ml_correct': correct_ml, 'prop_correct': correct_prop, 'overall_correct': overall_num},
        }
    })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_weekly_trends_fast_view(request):
    """
    Recent weekly trends for the current user via UserStatHistory.
    Query param: ?weeks=N (default 5)
    Returns: {'trends': [ { week, points, total_points, rank, rank_change, trend, accuracy, moneyline_accuracy, prop_accuracy } ]}
    """
    user = request.user
    try:
        window = max(1, int(request.GET.get('weeks', 5)))
    except ValueError:
        window = 5

    rows = list(UserStatHistory.objects.filter(user=user).order_by('week'))
    if not rows:
        return Response({'trends': []})

    rows = rows[-window:]  # last N by week ascending
    trends = []
    prev = None
    for r in rows:
        # rank change vs previous
        rank_change = None
        trend = 'same'
        if prev is not None and getattr(r, 'rank', None) and getattr(prev, 'rank', None):
            delta = prev.rank - r.rank  # positive = moved up
            rank_change = delta
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

        trends.append({
            'week': getattr(r, 'week', None),
            'points': getattr(r, 'weekly_points', None),         # weekly points (if you store it)
            'total_points': getattr(r, 'total_points', 0) or 0,  # season-to-date after this week
            'rank': getattr(r, 'rank', None),
            'rank_change': rank_change if rank_change is not None else 0,
            'trend': trend,
            'accuracy': getattr(r, 'season_accuracy', 0) or 0,
            'moneyline_accuracy': getattr(r, 'moneyline_accuracy', 0) or 0,
            'prop_accuracy': getattr(r, 'prop_accuracy', 0) or 0,
        })
        prev = r

    return Response({'trends': trends})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def season_leaderboard_fast_view(request):
    """
    Season leaderboard using each user's latest UserStatHistory (optionally through a given week).
    Query params:
      ?through_week=<int>     Only consider snapshot rows with week <= through_week
      ?limit=<int default 10> Limit the result size (max 50)
    """
    try:
        limit = min(int(request.GET.get('limit', 10)), 50)
    except ValueError:
        limit = 10

    through_week = request.GET.get('through_week')
    try:
        through_week = int(through_week) if through_week is not None else None
    except ValueError:
        through_week = None

    users = User.objects.all()
    board = []
    for u in users:
        latest = _latest_user_stat_history(u, through_week=through_week)
        if not latest:
            # fallback to current simple total if no snapshots exist
            total_pts = calculate_total_points_simple(u)
            board.append({
                'username': u.username,
                'total_points': total_pts,
                'rank': None,
                'trend': None,
                'rank_change': None,
            })
            continue

        # infer trend vs previous snapshot
        prev = UserStatHistory.objects.filter(user=u, week__lt=getattr(latest, 'week', 0)).order_by('-week').first()
        trend = None
        rank_change = None
        if prev and getattr(latest, 'rank', None) and getattr(prev, 'rank', None):
            delta = prev.rank - latest.rank  # positive = moved up
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'
            rank_change = delta

        board.append({
            'username': u.username,
            'total_points': getattr(latest, 'total_points', 0) or 0,
            'rank': getattr(latest, 'rank', None),
            'trend': trend,
            'rank_change': rank_change,
        })

    # sort by total_points desc, then username for stability
    board.sort(key=lambda r: (-r['total_points'], r['username'].lower()))
    return Response({'standings': board[:limit], 'limit': limit, 'through_week': through_week})
