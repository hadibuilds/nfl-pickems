from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Prediction, PropBet, PropBetPrediction  # Corrected PropBetPrediction model
from games.models import Game
from collections import defaultdict
import json
User = get_user_model()

@csrf_exempt  # Only use for testing; remove in production for security
@login_required
def make_prediction(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if request.method == 'POST':
        predicted_winner = request.POST.get('predicted_winner')
        if not predicted_winner:
            return JsonResponse({'error': 'No team selected'}, status=400)

        try:
            prediction = Prediction.objects.get(user=request.user, game=game)
            prediction.predicted_winner = predicted_winner
        except Prediction.DoesNotExist:
            prediction = Prediction(user=request.user, game=game, predicted_winner=predicted_winner)

        prediction.save()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt  # Only use for testing; remove in production for security
@login_required
def make_prop_bet(request, prop_bet_id):
    prop_bet = get_object_or_404(PropBet, pk=prop_bet_id)

    if request.method == 'POST':
        answer = request.POST.get('answer')
        print(f"DEBUG: Prop bet ID = {prop_bet_id}, Answer = {answer}, User = {request.user.username}")

        if not answer:
            return JsonResponse({'error': 'No answer provided'}, status=400)

        try:
            prop_prediction = PropBetPrediction.objects.get(user=request.user, prop_bet=prop_bet)
            prop_prediction.answer = answer
        except PropBetPrediction.DoesNotExist:
            prop_prediction = PropBetPrediction(user=request.user, prop_bet=prop_bet, answer=answer)

        prop_prediction.save()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def standings_view(request):
    users = User.objects.all()
    standings = []
    all_weeks = set()

    for user in users:
        weekly_scores = defaultdict(int)
        total = 0

        # Money-line predictions
        moneyline_preds = Prediction.objects.filter(user=user, is_correct=True)
        for pred in moneyline_preds:
            weekly_scores[pred.game.week] += 1
            all_weeks.add(pred.game.week)

        # Prop bets
        prop_preds = PropBetPrediction.objects.filter(user=user, is_correct=True)
        for prop in prop_preds:
            week = prop.prop_bet.game.week
            weekly_scores[week] += 2
            all_weeks.add(week)

        total = sum(weekly_scores.values())
        standings.append({
            'user': user,
            'weekly_scores': weekly_scores,
            'total': total
        })

    # Sort by total points, then username
    standings.sort(key=lambda x: (-x['total'], x['user'].username.lower()))

    sorted_weeks = sorted(all_weeks)

    return render(request, 'predictions/standings.html', {
        'standings': standings,
        'weeks': sorted_weeks,
    })


@login_required
def get_user_predictions(request):
    user = request.user
    predictions = Prediction.objects.filter(user=user)
    prop_bet_selections = PropBetPrediction.objects.filter(user=user)

    predictions_data = [
        {
            'game_id': pred.game.id,
            'predicted_winner': pred.predicted_winner
        }
        for pred in predictions
    ]
    
    prop_bet_data = [
        {
            'prop_bet_id': bet.prop_bet.id,
            'answer': bet.answer
        }
        for bet in prop_bet_selections
    ]

    return JsonResponse({'predictions': predictions_data, 'prop_bets': prop_bet_data})

@csrf_exempt  # Only for testing; remove in production for security
@login_required
def save_user_selection(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        game_id = data.get('game_id')
        predicted_winner = data.get('predicted_winner')
        prop_bet_id = data.get('prop_bet_id')
        answer = data.get('answer')

        # Handle saving money-line selection
        if game_id and predicted_winner:
            game = get_object_or_404(Game, pk=game_id)
            try:
                prediction = Prediction.objects.get(user=request.user, game=game)
                prediction.predicted_winner = predicted_winner
            except Prediction.DoesNotExist:
                prediction = Prediction(user=request.user, game=game, predicted_winner=predicted_winner)
            prediction.save()

        # Handle saving prop-bet selection
        if prop_bet_id and answer:
            prop_bet = get_object_or_404(PropBet, pk=prop_bet_id)
            try:
                prop_prediction = PropBetPrediction.objects.get(user=request.user, prop_bet=prop_bet)
                prop_prediction.answer = answer
            except PropBetPrediction.DoesNotExist:
                prop_prediction = PropBetPrediction(user=request.user, prop_bet=prop_bet, answer=answer)
            prop_prediction.save()

        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request method'}, status=400)

