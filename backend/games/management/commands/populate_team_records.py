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
WEEK_9_RECORDS = {
    # NFC EAST
    "Philadelphia Eagles": "6-2",
    "Dallas Cowboys": "3-4-1",
    "Washington Commanders": "3-5",
    "New York Giants": "2-6",
    # NFC NORTH
    "Green Bay Packers": "5-1-1",
    "Detroit Lions": "5-2",
    "Chicago Bears": "4-3",
    "Minnesota Vikings": "3-4",
    # NFC SOUTH
    "Tampa Bay Buccaneers": "6-2",
    "Carolina Panthers": "4-4",
    "Atlanta Falcons": "3-4",
    "New Orleans Saints": "1-7",
    # NFC WEST
    "Seattle Seahawks": "5-2",
    "Los Angeles Rams": "5-2",
    "San Francisco 49ers": "5-3",
    "Arizona Cardinals": "2-5",
    # AFC EAST
    "New England Patriots": "6-2",
    "Buffalo Bills": "5-2",
    "Miami Dolphins": "2-6",
    "New York Jets": "1-7",
    # AFC NORTH
    "Pittsburgh Steelers": "4-3",
    "Cincinnati Bengals": "3-5",
    "Baltimore Ravens": "2-5",
    "Cleveland Browns": "2-6",
    # AFC SOUTH
    "Indianapolis Colts": "7-1",
    "Jacksonville Jaguars": "4-3",
    "Houston Texans": "3-4",
    "Tennessee Titans": "1-7",
    # AFC WEST
    "Denver Broncos": "6-2",
    "Los Angeles Chargers": "5-3",
    "Kansas City Chiefs": "5-3",
    "Las Vegas Raiders": "2-5",
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
