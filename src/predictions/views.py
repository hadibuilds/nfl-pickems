# predictions/views.py — SLIMMED: delegates compute to utils
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from games.models import Game
from .models import Prediction, PropBet, PropBetPrediction


# Primary realtime helpers
from .utils.dashboard_utils import (
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
    get_user_season_stats,
)

# Snapshot/historical helpers
from .utils.dashboard_utils import (
    get_leaderboard_data_with_trends,
    calculate_user_dashboard_data,
    get_user_insights,
)

# New slim utils
from .utils.param_utils import parse_int
from .utils.season_utils import (
    api_user_season_stats_fast,
    api_user_weekly_trends_fast,
    build_season_leaderboard_fast,
    build_season_leaderboard_dynamic,
)

User = get_user_model()

# =============================================================================
# PREDICTION MANAGEMENT
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
            Prediction.objects.update_or_create(
                user=request.user, game=game, defaults={'predicted_winner': data['predicted_winner']}
            )
            results.append({'type': 'moneyline', 'success': True, 'action': 'upserted'})
        except ValueError as e:
            results.append({'type': 'moneyline', 'success': False, 'error': str(e)})

    if data.get('prop_bet_id') and data.get('answer'):
        prop_bet = get_object_or_404(PropBet, pk=data['prop_bet_id'])
        try:
            PropBetPrediction.objects.update_or_create(
                user=request.user, prop_bet=prop_bet, defaults={'answer': data['answer']}
            )
            results.append({'type': 'prop_bet', 'success': True, 'action': 'upserted'})
        except ValueError as e:
            results.append({'type': 'prop_bet', 'success': False, 'error': str(e)})

    if not results:
        return Response({'error': 'No valid predictions provided'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True, 'results': results})

# =============================================================================
# READS
# =============================================================================

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
            'winner': game.winner,
            'prop_bet_results': prop_results,
            'prop_result': prop_result_alias,
        })
    return Response({'results': results, 'total_completed_games': len(results)})

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
# UTILITY
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_week_only(request):
    current = int(get_current_week())
    weeks = list(Game.objects.values_list('week', flat=True).distinct().order_by('week'))
    return Response({'currentWeek': current, 'weeks': weeks, 'totalWeeks': len(weeks)})

# =============================================================================
# GRANULAR DASHBOARD
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats_only(request):
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_accuracy_only(request):
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_leaderboard_only(request):
    limit = parse_int(request.GET.get('limit'), default=5, minimum=1, maximum=20)
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_games_only(request):
    user = request.user
    limit = parse_int(request.GET.get('limit'), default=3, minimum=1, maximum=10)
    recent_games = get_recent_games_data(user, limit=limit)
    return Response({'recentGames': recent_games, 'limit': limit, 'totalGames': len(recent_games)})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_insights_only(request):
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

# =============================================================================
# MAIN DASHBOARD
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    user = request.user
    mode = (request.GET.get('mode') or 'realtime').lower()
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
            return Response({'error': f'Invalid sections: {", ".join(invalid_sections)}'}, status=status.HTTP_400_BAD_REQUEST)

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_realtime(request):
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_snapshot(request):
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

# =============================================================================
# ADMIN
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_weekly_snapshot(request):
    if not request.user.is_staff:
        return Response({'error': 'Staff privileges required'}, status=status.HTTP_403_FORBIDDEN)

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

# =============================================================================
# SNAPSHOT-POWERED READS (delegated)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_season_stats_fast_view(request):
    user = request.user
    through_week = parse_int(request.GET.get('through_week'))
    data = api_user_season_stats_fast(user, through_week=through_week)
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_weekly_trends_fast_view(request):
    user = request.user
    window = parse_int(request.GET.get('weeks'), default=5, minimum=1, maximum=20)
    data = api_user_weekly_trends_fast(user, window=window)
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def season_leaderboard_fast_view(request):
    through_week = parse_int(request.GET.get('through_week'))
    limit = parse_int(request.GET.get('limit'), default=10, minimum=1, maximum=50)
    data = build_season_leaderboard_fast(through_week=through_week, limit=limit)
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(15)
def season_leaderboard_dynamic_trend_view(request):
    limit = parse_int(request.GET.get('limit'), default=10, minimum=1, maximum=50)
    data = build_season_leaderboard_dynamic(limit=limit)
    return Response(data)
