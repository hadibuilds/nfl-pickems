# predictions/views.py - Cleaned up version with real-time as default
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Prediction, PropBet, PropBetPrediction
from games.models import Game
from .utils.dashboard_utils import (
    # Real-time functions (primary)
    calculate_user_dashboard_data_realtime,
    get_leaderboard_data_realtime,
    get_user_insights_realtime,
    
    # Snapshot functions (legacy/optional)
    calculate_user_dashboard_data,
    get_leaderboard_data_with_trends,
    get_user_insights,
)
from collections import defaultdict
import os

User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_prediction(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    predicted_winner = request.data.get('predicted_winner')

    if not predicted_winner:
        return Response({'error': 'No team selected'}, status=400)

    try:
        prediction = Prediction.objects.get(user=request.user, game=game)
        prediction.predicted_winner = predicted_winner
    except Prediction.DoesNotExist:
        prediction = Prediction(user=request.user, game=game, predicted_winner=predicted_winner)

    prediction.save()
    return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_prop_bet(request, prop_bet_id):
    prop_bet = get_object_or_404(PropBet, pk=prop_bet_id)
    answer = request.data.get('answer')

    if not answer:
        return Response({'error': 'No answer provided'}, status=400)

    try:
        prop_prediction = PropBetPrediction.objects.get(user=request.user, prop_bet=prop_bet)
        prop_prediction.answer = answer
    except PropBetPrediction.DoesNotExist:
        prop_prediction = PropBetPrediction(user=request.user, prop_bet=prop_bet, answer=answer)

    prop_prediction.save()
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_predictions(request):
    user = request.user
    predictions = Prediction.objects.filter(user=user)
    prop_bet_selections = PropBetPrediction.objects.filter(user=user)

    predictions_data = [
        {'game_id': pred.game.id, 'predicted_winner': pred.predicted_winner}
        for pred in predictions
    ]
    prop_bet_data = [
        {'prop_bet_id': bet.prop_bet.id, 'answer': bet.answer}
        for bet in prop_bet_selections
    ]

    return Response({'predictions': predictions_data, 'prop_bets': prop_bet_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_user_selection(request):
    data = request.data
    game_id = data.get('game_id')
    predicted_winner = data.get('predicted_winner')
    prop_bet_id = data.get('prop_bet_id')
    answer = data.get('answer')

    if game_id and predicted_winner:
        game = get_object_or_404(Game, pk=game_id)
        try:
            prediction = Prediction.objects.get(user=request.user, game=game)
            prediction.predicted_winner = predicted_winner
        except Prediction.DoesNotExist:
            prediction = Prediction(user=request.user, game=game, predicted_winner=predicted_winner)
        prediction.save()

    if prop_bet_id and answer:
        prop_bet = get_object_or_404(PropBet, pk=prop_bet_id)
        try:
            prop_prediction = PropBetPrediction.objects.get(user=request.user, prop_bet=prop_bet)
            prop_prediction.answer = answer
        except PropBetPrediction.DoesNotExist:
            prop_prediction = PropBetPrediction(user=request.user, prop_bet=prop_bet, answer=answer)
        prop_prediction.save()

    return Response({'success': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_standings(request):
    selected_week = request.GET.get('week')
    users = User.objects.all()
    standings = []
    all_weeks = set()

    for user in users:
        weekly_scores = defaultdict(int)

        moneyline_preds = Prediction.objects.filter(user=user, is_correct=True)
        for pred in moneyline_preds:
            weekly_scores[pred.game.week] += 1
            all_weeks.add(pred.game.week)

        prop_preds = PropBetPrediction.objects.filter(user=user, is_correct=True)
        for prop in prop_preds:
            week = prop.prop_bet.game.week
            weekly_scores[week] += 2
            all_weeks.add(week)

        total = (
            weekly_scores[int(selected_week)] if selected_week and selected_week.isdigit()
            else sum(weekly_scores.values())
        )

        standings.append({
            'username': user.username,
            'weekly_scores': weekly_scores,
            'total_points': total
        })

    standings.sort(key=lambda x: (-x['total_points'], x['username'].lower()))
    all_weeks = sorted(all_weeks)

    return Response({
        "standings": standings,
        "weeks": all_weeks,
        "selected_week": int(selected_week) if selected_week and selected_week.isdigit() else None
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_game_results(request):
    """
    API endpoint to get results for completed games
    Returns game_id, winning_team, and prop_bet_result for games that have results
    """
    try:
        from games.models import Game
        
        # Get all games that have results (winner is set)
        completed_games = Game.objects.filter(
            winner__isnull=False
        ).prefetch_related('prop_bets')
        
        results = []
        for game in completed_games:
            # Get prop bet result if exists
            prop_result = None
            if game.prop_bets.exists():
                prop_bet = game.prop_bets.first()
                prop_result = prop_bet.correct_answer
            
            results.append({
                'game_id': game.id,
                'winning_team': game.winner,
                'prop_bet_result': prop_result
            })
        
        return Response(results)
    
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_accuracy(request):
    """
    Calculate user accuracy based on predictions where is_correct is not null
    (i.e., games with results and prop bets with correct answers)
    """
    user = request.user
    
    # Count moneyline predictions where is_correct is not null (games with winners)
    moneyline_with_results = Prediction.objects.filter(
        user=user,
        is_correct__isnull=False  # Game has winner set
    )
    
    # Count prop bet predictions where is_correct is not null (prop bets with correct_answer)
    prop_bet_with_results = PropBetPrediction.objects.filter(
        user=user,
        is_correct__isnull=False  # PropBet has correct_answer set
    )
    
    # Count correct predictions
    correct_moneyline = moneyline_with_results.filter(is_correct=True).count()
    correct_prop_bets = prop_bet_with_results.filter(is_correct=True).count()
    
    # Total predictions with results
    total_moneyline = moneyline_with_results.count()
    total_prop_bets = prop_bet_with_results.count()
    
    return Response({
        'correct_predictions': correct_moneyline + correct_prop_bets,
        'total_predictions_with_results': total_moneyline + total_prop_bets,
        'moneyline_accuracy': {
            'correct': correct_moneyline,
            'total': total_moneyline
        },
        'prop_bet_accuracy': {
            'correct': correct_prop_bets,
            'total': total_prop_bets
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    """
    Main dashboard API endpoint - REAL-TIME BY DEFAULT
    Can use snapshots via ?mode=snapshot query parameter
    """
    try:
        user = request.user
        
        # Check mode - real-time is default
        mode = request.GET.get('mode', 'realtime').lower()
        
        if mode == 'snapshot':
            # Use snapshot-based calculations
            dashboard_data = calculate_user_dashboard_data(user)
            leaderboard = get_leaderboard_data_with_trends(limit=5)
            insights = get_user_insights(user)
            calculation_mode = 'snapshot'
        else:
            # Use real-time calculations (DEFAULT)
            dashboard_data = calculate_user_dashboard_data_realtime(user)
            leaderboard = get_leaderboard_data_realtime(limit=5)
            insights = get_user_insights_realtime(user)
            calculation_mode = 'realtime'
        
        # Mark current user in leaderboard
        for user_data in leaderboard:
            if user_data['username'] == user.username:
                user_data['isCurrentUser'] = True
        
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
                'timestamp': dashboard_data.get('currentWeek', 'unknown')
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch dashboard data: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Keep these for specific use cases if needed
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_realtime(request):
    """
    EXPLICIT real-time dashboard endpoint
    """
    try:
        user = request.user
        
        dashboard_data = calculate_user_dashboard_data_realtime(user)
        leaderboard = get_leaderboard_data_realtime(limit=5)
        insights = get_user_insights_realtime(user)
        
        # Mark current user in leaderboard
        for user_data in leaderboard:
            if user_data['username'] == user.username:
                user_data['isCurrentUser'] = True
        
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
                'calculation_mode': 'realtime',
                'guaranteed_realtime': True
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch real-time dashboard data: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_snapshot(request):
    """
    EXPLICIT snapshot-based dashboard endpoint
    Good for historical analysis or when you want consistent historical rankings
    """
    try:
        user = request.user
        
        dashboard_data = calculate_user_dashboard_data(user)
        leaderboard = get_leaderboard_data_with_trends(limit=5)
        insights = get_user_insights(user)
        
        # Mark current user in leaderboard
        for user_data in leaderboard:
            if user_data['username'] == user.username:
                user_data['isCurrentUser'] = True
        
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
                'calculation_mode': 'snapshot',
                'requires_snapshots': True
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch snapshot dashboard data: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_weekly_snapshot(request):
    """
    Manual trigger for weekly snapshot (admin use)
    Useful for capturing historical data at week boundaries
    """
    try:
        from django.core.management import call_command
        
        week = request.data.get('week')
        force = request.data.get('force', False)
        
        if week:
            call_command('capture_weekly_snapshot', week=week, force=force)
            message = f"Snapshot captured for week {week}"
        else:
            call_command('capture_weekly_snapshot', force=force)
            message = "Snapshot captured for latest completed week"
        
        return Response({'success': True, 'message': message})
        
    except Exception as e:
        return Response(
            {'error': f'Failed to capture snapshot: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )