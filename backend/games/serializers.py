from rest_framework import serializers
from games.models import Game, PropBet
from django.utils.timezone import now

class PropBetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropBet
        fields = ['id', 'question', 'category', 'options', 'correct_answer']

class GameSerializer(serializers.ModelSerializer):
    prop_bets = PropBetSerializer(many=True, read_only=True)
    locked = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ['id', 'week', 'home_team', 'away_team', 'start_time', 'locked', 'winner', 'prop_bets']

    def get_locked(self, obj):
        return obj.is_locked
