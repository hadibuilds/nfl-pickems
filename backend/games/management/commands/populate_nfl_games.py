"""
Django management command to populate NFL game schedules from ESPN API
Scrapes: season, week, home_team, away_team, start_time
"""

import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from games.models import Game, Window  # ⬅️ add Window


PACIFIC = ZoneInfo("America/Los_Angeles")  # ⬅️ PT for windowing


class Command(BaseCommand):
    help = "Populate NFL games from ESPN API (idempotent by season+week+teams)"

    # NFL team abbreviations mapping (kept from your legacy script)
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
            help='Limit number of games to process (0 = all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created/updated without writing'
        )
        parser.add_argument(
            '--display-tz',
            type=str,
            default='America/New_York',
            help='Timezone for printing times in dry-run (default: America/New_York)'
        )

    # ---------- Window helpers (new) ----------

    def _slot_for(self, dt_utc: datetime) -> str:
        """Return window slot based on *Pacific* local time."""
        dt_pt = timezone.localtime(dt_utc, PACIFIC)
        h = dt_pt.hour
        if h < 13:          # before 1pm PT
            return "morning"
        elif h < 17:        # 1–4:59pm PT
            return "afternoon"
        return "late"       # 5pm+ PT

    def _ensure_window(self, season: int, start_time_utc: datetime) -> Window:
        """Create or get the Window (PT date + slot) for a given game."""
        dt_pt = timezone.localtime(start_time_utc, PACIFIC)
        slot = self._slot_for(start_time_utc)
        window, _ = Window.objects.get_or_create(
            season=season,
            date=dt_pt.date(),  # PT calendar date
            slot=slot,
            defaults={},        # flags are computed later by grading/recompute
        )
        return window

    # ---------- Main flow ----------

    def handle(self, *args, **options):
        season = options['season']
        limit = options['limit']
        dry_run = options['dry_run']
        display_tz = ZoneInfo(options['display_tz'])

        self.stdout.write(f"Fetching NFL games for {season} season...")

        games_list_url = (
            f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/"
            f"seasons/{season}/types/2/events?limit=1000"
        )

        try:
            response = requests.get(games_list_url, timeout=30)
            response.raise_for_status()
            games_list = response.json()

            total = games_list.get('count', 0)
            self.stdout.write(f"Found {total} games referenced by ESPN")

            created_count = 0
            updated_count = 0
            processed_count = 0
            error_count = 0

            # ESPN returns refs; fetch each game detail
            for item in games_list.get('items', []):
                if limit and limit > 0 and processed_count >= limit:
                    break

                game_url = item.get('$ref')
                if not game_url:
                    continue

                try:
                    game_response = requests.get(game_url, timeout=30)
                    game_response.raise_for_status()
                    game_data = game_response.json()

                    game_info = self.extract_game_info(game_data, season=season)
                    if not game_info:
                        continue

                    # Convert team names to abbreviations for DB
                    game_info['home_team'] = self.get_team_abbreviation(game_info['home_team'])
                    game_info['away_team'] = self.get_team_abbreviation(game_info['away_team'])

                    if dry_run:
                        # Display-only timezone
                        disp_dt = game_info['start_time'].astimezone(display_tz)
                        tz_label = options['display_tz']
                        self.stdout.write(
                            f"S{game_info['season']} W{game_info['week']:2d} | "
                            f"{game_info['away_team']:3s} @ {game_info['home_team']:3s} | "
                            f"{disp_dt.strftime('%m/%d %I:%M%p')} {tz_label}"
                        )
                    else:
                        created = self.create_or_update_game(game_info)  # ⬅️ now attaches/moves Window
                        if created is True:
                            created_count += 1
                            self.stdout.write(
                                f"Created: S{game_info['season']} W{game_info['week']} "
                                f"{game_info['away_team']} @ {game_info['home_team']}"
                            )
                        elif created is False:
                            updated_count += 1
                            self.stdout.write(
                                f"Updated: S{game_info['season']} W{game_info['week']} "
                                f"{game_info['away_team']} @ {game_info['home_team']}"
                            )
                        # created can be None on error; no counters in that case

                    processed_count += 1

                except requests.RequestException as e:
                    error_count += 1
                    self.stdout.write(f"Error fetching game {game_url}: {e}")
                except Exception as e:
                    error_count += 1
                    self.stdout.write(f"Error processing game {game_url}: {e}")

            # Summary
            self.stdout.write("=" * 80)
            if dry_run:
                self.stdout.write(f"Dry run complete. Processed {processed_count} games, {error_count} errors")
            else:
                self.stdout.write(
                    f"Complete! Created: {created_count}, Updated: {updated_count}, "
                    f"Processed: {processed_count}, Errors: {error_count}"
                )

        except requests.RequestException as e:
            self.stdout.write(f"Error fetching games list: {e}")
        except Exception as e:
            self.stdout.write(f"Unexpected error: {e}")

    def extract_game_info(self, game_data, season: int):
        """Extract season, week, teams, start_time from ESPN game payload."""
        try:
            # Week extraction (your original logic, with a fallback)
            week = None
            if 'week' in game_data and game_data['week']:
                week = game_data['week'].get('number')

            if not week:
                season_info = game_data.get('season', {})
                if season_info:
                    week_info = season_info.get('week', {})
                    if week_info:
                        week = week_info.get('number')

            if not week:
                game_date_str = game_data.get('date')
                if game_date_str:
                    # Estimate week from date if ESPN omits it
                    game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                    season_start = datetime(season, 9, 5, tzinfo=game_date.tzinfo)  # rough anchor
                    days_diff = (game_date - season_start).days
                    week = max(1, (days_diff // 7) + 1)
                    self.stdout.write(f"Estimated week {week} from date {game_date_str}")

            if not week:
                self.stdout.write(f"Could not determine week for game: {game_data.get('name')}")
                return None

            # Date/time → make tz-aware UTC
            game_date_str = game_data.get('date')
            if not game_date_str:
                self.stdout.write(f"No date found for game: {game_data.get('name')}")
                return None

            dt = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            if timezone.is_naive(dt):
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            else:
                dt = dt.astimezone(ZoneInfo("UTC"))

            # Teams: prefer competitions block; fall back to name parsing
            away_team = home_team = None
            competition = (game_data.get('competitions') or [{}])[0]
            competitors = competition.get('competitors') or []
            if len(competitors) == 2:
                for comp in competitors:
                    t = comp.get('team', {}) or {}
                    tname = t.get('displayName') or t.get('name') or ""
                    if comp.get('homeAway') == 'home':
                        home_team = tname
                    elif comp.get('homeAway') == 'away':
                        away_team = tname

            if not home_team or not away_team:
                # fallback to "Team A at Team B"
                game_name = game_data.get('name', '')
                if ' at ' in game_name:
                    parts = game_name.split(' at ')
                    away_team = away_team or parts[0].strip()
                    home_team = home_team or parts[1].strip()

            if not home_team or not away_team:
                self.stdout.write(f"Could not extract teams for game: {game_data.get('name')}")
                return None

            return {
                'season': season,
                'week': int(week),
                'home_team': home_team,
                'away_team': away_team,
                'start_time': dt,  # stored as UTC
            }

        except Exception as e:
            self.stdout.write(f"Error extracting game info: {e}")
            return None

    def get_team_abbreviation(self, team_name):
        """Convert full team name to abbreviation (kept from your legacy)."""
        return self.TEAM_ABBREVIATIONS.get(team_name, team_name[:3].upper())

    def create_or_update_game(self, game_info):
        """
        Upsert by unique key: (season, week, home_team, away_team).
        Returns:
          True  -> created
          False -> updated (start_time and/or window changed)
          None  -> error/no change
        """
        try:
            # Compute the correct Window for this start time (PT date + slot)
            win = self._ensure_window(
                season=game_info['season'],
                start_time_utc=game_info['start_time'],
            )

            # Create or get the game, attaching window on create
            game, created = Game.objects.get_or_create(
                season=game_info['season'],
                week=game_info['week'],
                home_team=game_info['home_team'],
                away_team=game_info['away_team'],
                defaults={
                    'start_time': game_info['start_time'],  # UTC
                    'window': win,                          # ⬅️ attach window
                }
            )

            if created:
                return True

            # Existing → update start_time and window if they changed
            changed = False
            if game.start_time != game_info['start_time']:
                game.start_time = game_info['start_time']
                changed = True

            # If the start time changed, or if the window is simply incorrect, move it
            new_win = self._ensure_window(
                season=game_info['season'],
                start_time_utc=game_info['start_time'],
            )
            if game.window_id != new_win.id:
                game.window = new_win
                changed = True

            if changed:
                update_fields = ['start_time', 'window']
                if hasattr(game, 'updated_at'):
                    update_fields.append('updated_at')
                game.save(update_fields=update_fields)
                return False

            # No changes
            return None

        except Exception as e:
            self.stdout.write(f"Error creating/updating game: {e}")
            return None
