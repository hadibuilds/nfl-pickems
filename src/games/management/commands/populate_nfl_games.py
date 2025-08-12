"""
Django management command to populate NFL game schedules from ESPN API
Scrapes: week, home_team, away_team, start_time
Place this file in: src/games/management/commands/populate_nfl_games.py
"""

import requests
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from games.models import Game


class Command(BaseCommand):
    help = 'Display NFL game schedules (week, teams, dates/times) from ESPN API - no database writes'

    # NFL team abbreviations mapping
    TEAM_ABBREVIATIONS = {
        'Arizona Cardinals': 'ARI',
        'Atlanta Falcons': 'ATL',
        'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF',
        'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN',
        'Cleveland Browns': 'CLE',
        'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN',
        'Detroit Lions': 'DET',
        'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU',
        'Indianapolis Colts': 'IND',
        'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC',
        'Las Vegas Raiders': 'LV',
        'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR',
        'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE',
        'New Orleans Saints': 'NO',
        'New York Giants': 'NYG',
        'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI',
        'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF',
        'Seattle Seahawks': 'SEA',
        'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN',
        'Washington Commanders': 'WAS'
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            default=2025,
            help='NFL season year (default: 2025)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of games to process (default: 10, use 0 for all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating games'
        )

    def handle(self, *args, **options):
        season = options['season']
        limit = options['limit']
        dry_run = options['dry_run']
        
        self.stdout.write(f"Fetching NFL games for {season} season...")
        
        # Step 1: Get all game references
        games_list_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{season}/types/2/events?limit=1000"
        
        try:
            response = requests.get(games_list_url)
            response.raise_for_status()
            games_list = response.json()
            
            self.stdout.write(f"Found {games_list['count']} games")
            if not dry_run:
                self.stdout.write("=" * 80)
            
            created_count = 0
            updated_count = 0
            processed_count = 0
            error_count = 0
            
            # Step 2: Fetch details for each game
            for item in games_list['items']:
                if limit > 0 and processed_count >= limit:
                    break
                    
                game_url = item['$ref']
                
                try:
                    game_response = requests.get(game_url)
                    game_response.raise_for_status()
                    game_data = game_response.json()
                    
                    # Extract game information
                    game_info = self.extract_game_info(game_data)
                    
                    if game_info:
                        # Convert team names to abbreviations for database
                        game_info['home_team'] = self.get_team_abbreviation(game_info['home_team'])
                        game_info['away_team'] = self.get_team_abbreviation(game_info['away_team'])
                        
                        if dry_run:
                            # Display format for dry run
                            self.stdout.write(
                                f"Week {game_info['week']:2d} | "
                                f"{game_info['away_team']:3s} @ {game_info['home_team']:3s} | "
                                f"{game_info['start_time'].strftime('%m/%d %I:%M%p ET')}"
                            )
                        else:
                            # Actually create in database
                            created = self.create_or_update_game(game_info)
                            if created:
                                created_count += 1
                                self.stdout.write(f"Created: Week {game_info['week']} - {game_info['away_team']} @ {game_info['home_team']}")
                            else:
                                updated_count += 1
                                self.stdout.write(f"Updated: Week {game_info['week']} - {game_info['away_team']} @ {game_info['home_team']}")
                        
                        processed_count += 1
                    
                except requests.RequestException as e:
                    error_count += 1
                    self.stdout.write(f"Error fetching game {game_url}: {e}")
                    continue
                except Exception as e:
                    error_count += 1
                    self.stdout.write(f"Error processing game {game_url}: {e}")
                    continue
            
            # Summary
            self.stdout.write("=" * 80)
            if dry_run:
                self.stdout.write(f"Dry run complete. Processed {processed_count} games, {error_count} errors")
            else:
                self.stdout.write(f"Complete! Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")
                
        except requests.RequestException as e:
            self.stdout.write(f"Error fetching games list: {e}")
        except Exception as e:
            self.stdout.write(f"Unexpected error: {e}")

    def extract_game_info(self, game_data):
        """Extract relevant game information from ESPN API response"""
        try:
            # Debug: Print the structure we're working with
            self.stdout.write(f"Processing game: {game_data.get('name', 'Unknown')}")
            
            # Get week number - try multiple ways
            week = None
            if 'week' in game_data and game_data['week']:
                week = game_data['week'].get('number')
            
            # If week is still None, try to extract from season info
            if not week:
                # Try to get it from the season/week structure
                season_info = game_data.get('season', {})
                if season_info:
                    week_info = season_info.get('week', {})
                    if week_info:
                        week = week_info.get('number')
            
            # If still no week, we'll estimate based on date (September = Week 1, etc.)
            if not week:
                game_date_str = game_data.get('date')
                if game_date_str:
                    game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                    # Rough estimate: September 5th = Week 1, add 1 week per 7 days
                    season_start = datetime(2025, 9, 5, tzinfo=game_date.tzinfo)
                    days_diff = (game_date - season_start).days
                    week = max(1, (days_diff // 7) + 1)
                    self.stdout.write(f"Estimated week {week} from date {game_date_str}")
            
            if not week:
                self.stdout.write(f"Could not determine week for game: {game_data.get('name')}")
                return None
            
            # Get game date/time
            game_date_str = game_data.get('date')
            if not game_date_str:
                self.stdout.write(f"No date found for game: {game_data.get('name')}")
                return None
            
            # Parse ISO date format
            start_time = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            
            # Get teams from name field as backup
            game_name = game_data.get('name', '')
            if ' at ' in game_name:
                parts = game_name.split(' at ')
                away_team = parts[0].strip()
                home_team = parts[1].strip()
            else:
                # Try competitions structure
                competition = game_data.get('competitions', [{}])[0]
                competitors = competition.get('competitors', [])
                
                if len(competitors) != 2:
                    self.stdout.write(f"Expected 2 competitors, found {len(competitors)} for game: {game_name}")
                    return None
                
                home_team = None
                away_team = None
                
                for competitor in competitors:
                    team_data = competitor.get('team', {})
                    team_name = team_data.get('displayName', '') or team_data.get('name', '')
                    
                    if competitor.get('homeAway') == 'home':
                        home_team = team_name
                    elif competitor.get('homeAway') == 'away':
                        away_team = team_name
                
                if not home_team or not away_team:
                    self.stdout.write(f"Could not extract teams from competitors for game: {game_name}")
                    return None
            
            self.stdout.write(f"Extracted: Week {week}, {self.get_team_abbreviation(away_team)} @ {self.get_team_abbreviation(home_team)}, {start_time}")
            
            return {
                'week': week,
                'home_team': home_team,
                'away_team': away_team,
                'start_time': start_time
            }
            
        except Exception as e:
            self.stdout.write(f"Error extracting game info: {e}")
            return None

    def get_team_abbreviation(self, team_name):
        """Convert full team name to abbreviation"""
        return self.TEAM_ABBREVIATIONS.get(team_name, team_name[:3].upper())

    def create_or_update_game(self, game_info):
        """Create or update game in database"""
        try:
            game, created = Game.objects.get_or_create(
                week=game_info['week'],
                home_team=game_info['home_team'],
                away_team=game_info['away_team'],
                defaults={
                    'start_time': game_info['start_time']
                }
            )
            
            if not created:
                # Update existing game's start time if it changed
                game.start_time = game_info['start_time']
                game.save()
            
            return created
            
        except Exception as e:
            self.stdout.write(f"Error creating/updating game: {e}")
            return False