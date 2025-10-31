"""
Management command to refresh team record cache for all future games.
Run this after entering game results to warm the cache.

Usage:
    python manage.py refresh_team_records --season 2025
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from games.models import Game
from games.serializers import GameSerializer


class Command(BaseCommand):
    help = 'Pre-warm team record cache for all future games'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            default=2025,
            help='Season year (default: 2025)'
        )

    def handle(self, *args, **options):
        season = options['season']
        
        self.stdout.write(f'Refreshing team records for season {season}...')
        
        # Get all games in the season
        all_games = Game.objects.filter(season=season).values_list(
            'home_team', 'away_team', 'week', 'season'
        ).distinct()
        
        serializer = GameSerializer()
        count = 0
        
        for home_team, away_team, week, season in all_games:
            # Calculate and cache records for both teams
            serializer._get_team_record(home_team, season, week)
            serializer._get_team_record(away_team, season, week)
            count += 2
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Refreshed {count} team records for season {season}')
        )
