from .models import Game, PropBet
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from .serializers import GameSerializer
from rest_framework.decorators import api_view


@csrf_exempt
@api_view(['GET'])
def api_games(request):
    games = Game.objects.prefetch_related('prop_bets').all()
    serializer = GameSerializer(games, many=True)
    return Response(serializer.data)

"""
@csrf_exempt
def api_games(request):
    if request.method == 'GET':
        games = list(Game.objects.values())
        return JsonResponse(games, safe=False)
"""

"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Game
from predictions.models import Prediction, PropBetPrediction, PropBet
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def week_games(request, week_number):
    games = Game.objects.filter(week=week_number).order_by('start_time')

    # ✅ Get money-line predictions for this user
    user_predictions = Prediction.objects.filter(user=request.user, game__in=games)
    prediction_map = {p.game_id: p.predicted_winner for p in user_predictions}

    # ✅ Get prop bets related to these games
    prop_bets = PropBet.objects.filter(game__in=games)

    # ✅ Get user's prop bet predictions
    user_prop_predictions = PropBetPrediction.objects.filter(user=request.user, prop_bet__in=prop_bets)
    prop_prediction_map = {p.prop_bet_id: p.answer for p in user_prop_predictions}

    return render(request, 'games/week_games.html', {
        'games': games,
        'week_number': week_number,
        'prediction_map': prediction_map,
        'prop_bet_predictions': prop_prediction_map,  # 👈 Add to context
    })
"""