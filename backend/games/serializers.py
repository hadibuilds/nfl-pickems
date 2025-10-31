from rest_framework import serializers
from .models import Game, PropBet
from django.utils.timezone import now
from django.db.models import Q, Count, Case, When, IntegerField
from django.core.cache import cache

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
        fields = ['id', 'week', 'home_team', 'away_team', 'start_time', 'locked', 'winner',
                  'prop_bets', 'home_team_record', 'away_team_record']

    def get_locked(self, obj):
        return obj.is_locked

    def _get_team_record(self, team_name, season, current_week):
        """Calculate team's W-L-T record for games before the current week in this season."""
        # Cache key for this team's record up to this week
        # Cache indefinitely - only cleared when game results are entered
        cache_key = f"team_record:{season}:{team_name}:week{current_week}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Get all games for this team in this season before the current week
        team_games = Game.objects.filter(
            season=season,
            week__lt=current_week,
            winner__isnull=False  # Only count games with results
        ).filter(
            Q(home_team=team_name) | Q(away_team=team_name)
        )

        # Count wins, ties, and losses
        wins = team_games.filter(winner=team_name).count()
        ties = team_games.filter(winner="TIE").count()
        total_games = team_games.count()
        losses = total_games - wins - ties

        # Only include ties in record if team has at least one tie
        if ties > 0:
            result = f"{wins}-{losses}-{ties}"
        else:
            result = f"{wins}-{losses}"

        # Cache for 7 days (records don't change until you enter new results)
        cache.set(cache_key, result, 60 * 60 * 24 * 7)
        return result

    def get_home_team_record(self, obj):
        """Get home team's record going into this game."""
        return self._get_team_record(obj.home_team, obj.season, obj.week)

    def get_away_team_record(self, obj):
        """Get away team's record going into this game."""
        return self._get_team_record(obj.away_team, obj.season, obj.week)

