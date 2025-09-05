# predictions/views.py — CRUD OPERATIONS ONLY
# Clean separation: predictions = raw data input/output, analytics = data analysis

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from games.models import Game, PropBet
from .models import MoneyLinePrediction, PropBetPrediction

# =============================================================================
# PREDICTION MANAGEMENT (CRUD OPERATIONS)
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_prediction(request, game_id):
    """Create or update a moneyline prediction."""
    game = get_object_or_404(Game, pk=game_id)
    
    # SECURITY: Check if game is locked before accepting predictions
    if game.is_locked:
        return Response({'error': 'Cannot submit picks for locked games'}, status=status.HTTP_400_BAD_REQUEST)
    
    predicted_winner = request.data.get('predicted_winner')
    if not predicted_winner:
        return Response({'error': 'No team selected'}, status=status.HTTP_400_BAD_REQUEST)
    
    game = get_object_or_404(Game, pk=game_id)
    
    # SECURITY: Check if game is locked before accepting predictions
    if game.is_locked:
        return Response({'error': 'Cannot submit picks for locked games'}, status=status.HTTP_400_BAD_REQUEST)
    
    predicted_winner = request.data.get('predicted_winner')
    if not predicted_winner:
        return Response({'error': 'No team selected'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        prediction, created = MoneyLinePrediction.objects.update_or_create(
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
    """Create or update a prop bet prediction."""
    prop_bet = get_object_or_404(PropBet, pk=prop_bet_id)
    
    # SECURITY: Check if game is locked before accepting prop bet predictions
    if prop_bet.is_locked:
        return Response({'error': 'Cannot submit picks for locked games'}, status=status.HTTP_400_BAD_REQUEST)
    
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
    """Bulk save user selections for moneyline and prop bets."""
    data = request.data
    results = []

    if data.get('game_id') and data.get('predicted_winner'):
        game = get_object_or_404(Game, pk=data['game_id'])
        
        # SECURITY: Check if game is locked before accepting predictions
        if game.is_locked:
            results.append({'type': 'moneyline', 'success': False, 'error': 'Cannot submit picks for locked games'})
        else:
            try:
                MoneyLinePrediction.objects.update_or_create(
                    user=request.user, game=game, defaults={'predicted_winner': data['predicted_winner']}
                )
                results.append({'type': 'moneyline', 'success': True, 'action': 'upserted'})
            except ValueError as e:
                results.append({'type': 'moneyline', 'success': False, 'error': str(e)})

    if data.get('prop_bet_id') and data.get('answer'):
        prop_bet = get_object_or_404(PropBet, pk=data['prop_bet_id'])
        
        # SECURITY: Check if prop bet game is locked before accepting predictions
        if prop_bet.is_locked:
            results.append({'type': 'prop_bet', 'success': False, 'error': 'Cannot submit picks for locked games'})
        else:
            try:
                PropBetPrediction.objects.update_or_create(
                    user=request.user, prop_bet=prop_bet, defaults={'answer': data['answer']}
                )
                results.append({'type': 'prop_bet', 'success': True, 'action': 'upserted'})
            except ValueError as e:
                results.append({'type': 'prop_bet', 'success': False, 'error': str(e)})

    if not results:
        return Response({'error': 'No valid predictions provided'}, status=400)

    any_failed = any(r.get('success') is False for r in results)
    if any_failed:
        return Response(
            {'success': False, 'results': results, 'error': 'Some picks were rejected.'},
            status=400
        )

    return Response({'success': True, 'results': results}, status=200)


# =============================================================================
# DATA READS (CRUD OPERATIONS)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_predictions(request):
    """Get all predictions for the authenticated user."""
    user = request.user
    predictions = MoneyLinePrediction.objects.filter(user=user).select_related('game')
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
def get_game_results(request):
    """Get completed game results with winners and prop bet answers."""
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