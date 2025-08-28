# analytics/management/commands/backfill_windowed_rankings.py

"""
Management command to backfill the windowed ranking system.

Usage:
  python manage.py backfill_windowed_rankings --season 2025
  python manage.py backfill_windowed_rankings --season 2025 --window "2025-09-07:afternoon"
  python manage.py backfill_windowed_rankings --all-seasons
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from games.models import Game, PropBet
from analytics.services.windowed_rankings import (
    get_window_key_from_game, 
    process_window,
    get_current_season
)


class Command(BaseCommand):
    help = 'Backfill windowed ranking system with historical data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            help='Specific season to backfill (default: current year)'
        )
        parser.add_argument(
            '--window',
            type=str,
            help='Specific window to backfill (format: YYYY-MM-DD:slot)'
        )
        parser.add_argument(
            '--all-seasons',
            action='store_true',
            help='Backfill all seasons with game data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh existing window data'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be modified'))

        # Determine which seasons to process
        if options['all_seasons']:
            seasons = Game.objects.values_list('season', flat=True).distinct().order_by('season')
        else:
            season = options['season'] or get_current_season()
            seasons = [season]

        total_processed = 0
        
        for season in seasons:
            if options['window']:
                # Process specific window
                total_processed += self._process_season_window(season, options['window'], dry_run, force)
            else:
                # Process entire season
                total_processed += self._process_full_season(season, dry_run, force)

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would process {total_processed} windows')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully processed {total_processed} windows')
            )

    def _process_full_season(self, season, dry_run, force):
        """Process all windows in a season"""
        
        self.stdout.write(f'\nProcessing season {season}...')
        
        # Step 1: Populate window_key for all games if missing
        self._populate_window_keys(season, dry_run)
        
        # Step 2: Get all unique windows with completed games
        windows = self._get_completed_windows(season)
        
        if not windows:
            self.stdout.write(self.style.WARNING(f'No completed windows found for season {season}'))
            return 0

        self.stdout.write(f'Found {len(windows)} completed windows in season {season}')
        
        processed_count = 0
        
        for window_key in sorted(windows):
            try:
                processed_count += self._process_season_window(season, window_key, dry_run, force)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {window_key}: {e}')
                )
                continue
        
        return processed_count

    def _process_season_window(self, season, window_key, dry_run, force):
        """Process a specific window"""
        
        if dry_run:
            # Just show what would be processed
            games_count = Game.objects.filter(season=season, window_key=window_key, winner__isnull=False).count()
            props_count = PropBet.objects.filter(
                game__season=season, 
                game__window_key=window_key,
                correct_answer__isnull=False
            ).count()
            
            self.stdout.write(f'  {window_key}: {games_count} games, {props_count} props')
            return 1
        
        # Actually process the window
        self.stdout.write(f'  Processing {window_key}...', ending='')
        
        try:
            result = process_window(season, window_key, force_refresh=force)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f' ✓ {result["users_with_points"]} users, '
                    f'{result["total_points_awarded"]} points awarded'
                )
            )
            
            if self.verbosity >= 2:
                self.stdout.write(f'    Delta records: {result["delta_records_created"]}')
                self.stdout.write(f'    Cumulative records: {result["cumulative_records_created"]}')
            
            return 1
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f' ✗ Failed: {e}'))
            return 0

    def _populate_window_keys(self, season, dry_run):
        """Populate window_key for games and props if missing"""
        
        # Update games missing window_key
        games_without_keys = Game.objects.filter(season=season, window_key__isnull=True)
        
        if games_without_keys.exists():
            self.stdout.write(f'  Populating window_key for {games_without_keys.count()} games...')
            
            if not dry_run:
                for game in games_without_keys:
                    window_key = get_window_key_from_game(game)
                    if window_key:
                        game.window_key = window_key
                        game.save(update_fields=['window_key'])
        
        # Update props missing window_key (inherit from game)
        props_without_keys = PropBet.objects.filter(
            game__season=season,
            window_key__isnull=True
        )
        
        if props_without_keys.exists():
            self.stdout.write(f'  Populating window_key for {props_without_keys.count()} props...')
            
            if not dry_run:
                for prop in props_without_keys.select_related('game'):
                    if prop.game.window_key:
                        prop.window_key = prop.game.window_key
                        prop.save(update_fields=['window_key'])

    def _get_completed_windows(self, season):
        """Get all windows that have completed games"""
        
        # Find windows with at least one completed game
        completed_windows = set()
        
        completed_games = Game.objects.filter(
            season=season,
            winner__isnull=False,
            window_key__isnull=False
        )
        
        for game in completed_games:
            completed_windows.add(game.window_key)
        
        return list(completed_windows)