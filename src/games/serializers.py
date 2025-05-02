from rest_framework import serializers
from .models import Game
from predictions.models import PropBet

class PropBetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropBet
        fields = ['id', 'question', 'category', 'options', 'correct_answer']

class GameSerializer(serializers.ModelSerializer):
    prop_bets = PropBetSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'week', 'home_team', 'away_team', 'start_time', 'locked', 'winner', 'prop_bets']
