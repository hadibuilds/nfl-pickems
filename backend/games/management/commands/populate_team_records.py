"""
Management command to populate team records for all games.
Run this once after migration to set initial records.

Usage:
    python manage.py populate_team_records --season 2025
"""
from django.core.management.base import BaseCommand
from games.models import Game
from django.db.models import Q


# Week 9 records (going into week 9)
# Using team abbreviations as they appear in the database
WEEK_9_RECORDS = {
    # NFC EAST
    "PHI": "6-2",
    "DAL": "3-4-1",
    "WAS": "3-5",
    "NYG": "2-6",
    # NFC NORTH
    "GB": "5-1-1",
    "DET": "5-2",
    "CHI": "4-3",
    "MIN": "3-4",
    # NFC SOUTH
    "TB": "6-2",
    "CAR": "4-4",
    "ATL": "3-4",
    "NO": "1-7",
    # NFC WEST
    "SEA": "5-2",
    "LAR": "5-2",
    "SF": "5-3",
    "ARI": "2-5",
    # AFC EAST
    "NE": "6-2",
    "BUF": "5-2",
    "MIA": "2-6",
    "NYJ": "1-7",
    # AFC NORTH
    "PIT": "4-3",
    "CIN": "3-5",
    "BAL": "2-5",
    "CLE": "2-6",
    # AFC SOUTH
    "IND": "7-1",
    "JAX": "4-3",
    "HOU": "3-4",
    "TEN": "1-7",
    # AFC WEST
    "DEN": "6-2",
    "LAC": "5-3",
    "KC": "5-3",
    "LV": "2-5",
}


class Command(BaseCommand):
    help = 'Populate team records for all games based on week 9 standings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            default=2025,
            help='Season year (default: 2025)'
        )

    def handle(self, *args, **options):
        season = options['season']
        
        self.stdout.write(f'Populating team records for season {season}...')
        
        # Get all games week 9 and later
        games = Game.objects.filter(season=season, week__gte=9).order_by('week')
        
        updated = 0
        for game in games:
            # Set records for week 9 games
            if game.week == 9:
                game.home_team_record = WEEK_9_RECORDS.get(game.home_team, "")
                game.away_team_record = WEEK_9_RECORDS.get(game.away_team, "")
                game.save(update_fields=['home_team_record', 'away_team_record'])
                updated += 1
            # For future weeks, calculate based on results up to that week
            else:
                # This will be calculated when you enter game results
                pass
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Populated {updated} games with team records')
        )
