from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Prediction, PropBet, PropBetPrediction
from games.models import Game
from collections import defaultdict
import json

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
