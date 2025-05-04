from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Prediction, PropBet, PropBetPrediction
from games.models import Game
from collections import defaultdict

User = get_user_model()

@csrf_exempt
@login_required
def make_prediction(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if request.method == 'POST':
        predicted_winner = request.POST.get('predicted_winner')
        print("DEBUG predicted_winner =", predicted_winner)
        print("DEBUG: home_team =", game.home_team)
        print("DEBUG: away_team =", game.away_team)

        if not predicted_winner:
            return JsonResponse({'error': 'No team selected'}, status=400)

        # ✅ Fix: Manually check if prediction exists
        try:
            prediction = Prediction.objects.get(user=request.user, game=game)
            prediction.predicted_winner = predicted_winner
        except Prediction.DoesNotExist:
            prediction = Prediction(user=request.user, game=game, predicted_winner=predicted_winner)

        prediction.save()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
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

