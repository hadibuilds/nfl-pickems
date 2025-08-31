from rest_framework import serializers
from .models import Game, PropBet
from django.utils.timezone import now

class PropBetSerializer(serializers.ModelSerializer):
    option_a = serializers.SerializerMethodField()
    option_b = serializers.SerializerMethodField()

    class Meta:
        model = PropBet
        fields = ["id", "category", "question", "options", "correct_answer",
                  "option_a", "option_b"]

    def get_option_a(self, obj): return obj.options[0]
    def get_option_b(self, obj): return obj.options[1]

class GameSerializer(serializers.ModelSerializer):
    prop_bets = PropBetSerializer(many=True, read_only=True)
    locked = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ['id', 'week', 'home_team', 'away_team', 'start_time', 'locked', 'winner', 'prop_bets']

    def get_locked(self, obj):
        return obj.is_locked

