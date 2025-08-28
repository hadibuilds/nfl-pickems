"""
Django management command to populate NFL game schedules from ESPN API
Scrapes: week, home_team, away_team, start_time (UTC), window_key (PT)
Place this file in: backend/games/management/commands/populate_nfl_games.py
"""

import json
from datetime import datetime
import pytz

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from nfl_pickems.settings.base import NFL_SEASON
from games.models import Game


PT = pytz.timezone("America/Los_Angeles")


class Command(BaseCommand):
    help = (
        "Fetch NFL game schedules from ESPN API and create/update Game records.\n"
        "Stores start_time in UTC and computes window_key using Pacific Time."
    )

    # NFL team abbreviations mapping
    TEAM_ABBREVIATIONS = {
        "Arizona Cardinals": "ARI",
        "Atlanta Falcons": "ATL",
        "Baltimore Ravens": "BAL",
        "Buffalo Bills": "BUF",
        "Carolina Panthers": "CAR",
        "Chicago Bears": "CHI",
        "Cincinnati Bengals": "CIN",
        "Cleveland Browns": "CLE",
        "Dallas Cowboys": "DAL",
        "Denver Broncos": "DEN",
        "Detroit Lions": "DET",
        "Green Bay Packers": "GB",
        "Houston Texans": "HOU",
        "Indianapolis Colts": "IND",
        "Jacksonville Jaguars": "JAX",
        "Kansas City Chiefs": "KC",
        "Las Vegas Raiders": "LV",
        "Los Angeles Chargers": "LAC",
        "Los Angeles Rams": "LAR",
        "Miami Dolphins": "MIA",
        "Minnesota Vikings": "MIN",
        "New England Patriots": "NE",
        "New Orleans Saints": "NO",
        "New York Giants": "NYG",
        "New York Jets": "NYJ",
        "Philadelphia Eagles": "PHI",
        "Pittsburgh Steelers": "PIT",
        "San Francisco 49ers": "SF",
        "Seattle Seahawks": "SEA",
        "Tampa Bay Buccaneers": "TB",
        "Tennessee Titans": "TEN",
        "Washington Commanders": "WAS",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            type=int,
            default=2025,
            help="NFL season year (default: 2025)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Limit number of games to process (default: 10, use 0 for all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating games",
        )

    # ------------- helpers -----------------

    def _slot_for_local_time(self, dt_local: datetime) -> str:
        """
        Map a local PT time to morning/afternoon/late buckets.
        Now handles timezone-aware datetime objects properly.
        """
        # Ensure we're working with the hour in local time
        if dt_local.tzinfo is not None:
            # If timezone-aware, get the hour directly
            h = dt_local.hour
        else:
            # If naive, assume it's already in local time
            h = dt_local.hour
            
        if h < 13:
            return "morning"
        if h < 17:
            return "afternoon"
        return "late"

    def _compute_window_key_from_utc(self, dt_utc: datetime) -> str:
        """
        Convert UTC datetime to PT and compute YYYY-MM-DD:slot label.
        Fixed to use Django timezone utilities with pytz.
        """
        # Ensure the UTC datetime is timezone-aware
        if dt_utc.tzinfo is None:
            dt_utc = timezone.make_aware(dt_utc, pytz.UTC)
        elif dt_utc.tzinfo != pytz.UTC:
            dt_utc = dt_utc.astimezone(pytz.UTC)
        
        # Convert to Pacific Time using pytz
        dt_pt = dt_utc.astimezone(PT)
        
        # Generate the window key using PT date and time slot
        date_str = dt_pt.date().isoformat()
        slot = self._slot_for_local_time(dt_pt)
        
        return f"{date_str}:{slot}"

    def _parse_api_datetime_to_utc(self, dt_str: str) -> datetime:
        """
        Parse ESPN API datetime string into timezone-aware UTC datetime.
        Fixed to handle both naive and aware datetime strings properly.
        """
        # Use Django's parse_datetime which handles ISO8601 formats
        dt = parse_datetime(dt_str)
        
        if dt is None:
            raise ValueError(f"Could not parse datetime: {dt_str}")
        
        # Handle timezone awareness
        if dt.tzinfo is None:
            # If naive, assume it's UTC and make it timezone-aware
            dt = timezone.make_aware(dt, pytz.UTC)
        else:
            # If already timezone-aware, convert to UTC
            dt = dt.astimezone(pytz.UTC)
        
        return dt

    def get_team_abbreviation(self, team_name):
        """Convert full team name to abbreviation; fallback to first 3 uppercase if unknown."""
        return self.TEAM_ABBREVIATIONS.get(team_name, team_name[:3].upper())

    # ------------- command entry -----------------

    def handle(self, *args, **options):
        season = options["season"]
        limit = options["limit"]
        dry_run = options["dry_run"]

        self.stdout.write(f"Fetching NFL games for {season} season...")

        # Step 1: Get all game references
        games_list_url = (
            f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/"
            f"seasons/{season}/types/2/events?limit=1000"
        )

        try:
            response = requests.get(games_list_url, timeout=20)
            response.raise_for_status()
            games_list = response.json()

            total = int(games_list.get("count", 0))
            self.stdout.write(f"Found {total} games")
            if not dry_run:
                self.stdout.write("=" * 80)

            created_count = 0
            updated_count = 0
            processed_count = 0
            error_count = 0

            # Step 2: Fetch details for each game
            for item in games_list.get("items", []):
                if limit > 0 and processed_count >= limit:
                    break

                game_url = item.get("$ref")
                if not game_url:
                    error_count += 1
                    self.stdout.write("Skipping an item without $ref")
                    continue

                try:
                    game_response = requests.get(game_url, timeout=20)
                    game_response.raise_for_status()
                    game_data = game_response.json()

                    # Extract game information
                    game_info = self.extract_game_info(game_data)

                    if game_info:
                        # Convert team names to abbreviations for database
                        game_info["home_team"] = self.get_team_abbreviation(game_info["home_team"])
                        game_info["away_team"] = self.get_team_abbreviation(game_info["away_team"])

                        if dry_run:
                            # Display format for dry run
                            # Show both PT (for fan view) and UTC (for clarity)
                            start_pt = game_info["start_time"].astimezone(PT)
                            self.stdout.write(
                                f"Week {game_info['week']:2d} | "
                                f"{game_info['away_team']:3s} @ {game_info['home_team']:3s} | "
                                f"{start_pt.strftime('%m/%d %I:%M%p PT')} "
                                f"(UTC: {game_info['start_time'].strftime('%Y-%m-%d %H:%M')}Z) | "
                                f"window={game_info['window_key']}"
                            )
                        else:
                            # Actually create/update in database
                            created = self.create_or_update_game(game_info)
                            if created:
                                created_count += 1
                                self.stdout.write(
                                    f"Created: Week {game_info['week']} - "
                                    f"{game_info['away_team']} @ {game_info['home_team']}"
                                )
                            else:
                                updated_count += 1
                                self.stdout.write(
                                    f"Updated: Week {game_info['week']} - "
                                    f"{game_info['away_team']} @ {game_info['home_team']}"
                                )

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
                self.stdout.write(
                    f"Complete! Created: {created_count}, Updated: {updated_count}, Errors: {error_count}"
                )

        except requests.RequestException as e:
            self.stdout.write(f"Error fetching games list: {e}")
        except Exception as e:
            self.stdout.write(f"Unexpected error: {e}")

    # ------------- extraction & persistence -----------------

    def extract_game_info(self, game_data):
        """Extract relevant game information from ESPN API response"""
        try:
            # Debug: Print the structure we're working with
            self.stdout.write(f"Processing game: {game_data.get('name', 'Unknown')}")

            # ---- WEEK RESOLUTION -------------------------------------------------
            week = None
            if "week" in game_data and game_data["week"]:
                week = game_data["week"].get("number")

            if not week:
                # Some feeds nest week under season
                season_info = game_data.get("season", {})
                if season_info:
                    week_info = season_info.get("week", {})
                    if week_info:
                        week = week_info.get("number")

            # If still missing, estimate from date (fallback only)
            if not week:
                game_date_str = game_data.get("date")
                if game_date_str:
                    game_date = self._parse_api_datetime_to_utc(game_date_str)

                    # Rough estimate: September 5th (UTC midnight) = Week 1
                    season_start = timezone.make_aware(datetime(2025, 9, 5), pytz.UTC)
                    days_diff = (game_date - season_start).days
                    week = max(1, (days_diff // 7) + 1)
                    self.stdout.write(f"Estimated week {week} from date {game_date_str}")

            if not week:
                self.stdout.write(f"Could not determine week for game: {game_data.get('name')}")
                return None

            # ---- DATE/TIME NORMALIZATION ----------------------------------------
            game_date_str = game_data.get("date")
            if not game_date_str:
                self.stdout.write(f"No date found for game: {game_data.get('name')}")
                return None

            # Parse to timezone-aware UTC
            start_time = self._parse_api_datetime_to_utc(game_date_str)

            # Compute PT-based window_key for labeling
            window_key = self._compute_window_key_from_utc(start_time)

            # ---- TEAMS -----------------------------------------------------------
            game_name = game_data.get("name", "")
            if " at " in game_name:
                parts = game_name.split(" at ")
                away_team = parts[0].strip()
                home_team = parts[1].strip()
            else:
                # Try competitions structure
                competition = (game_data.get("competitions") or [{}])[0]
                competitors = competition.get("competitors", [])

                if len(competitors) != 2:
                    self.stdout.write(
                        f"Expected 2 competitors, found {len(competitors)} for game: {game_name}"
                    )
                    return None

                home_team = None
                away_team = None

                for competitor in competitors:
                    team_data = competitor.get("team", {})
                    team_name = team_data.get("displayName", "") or team_data.get("name", "")

                    if competitor.get("homeAway") == "home":
                        home_team = team_name
                    elif competitor.get("homeAway") == "away":
                        away_team = team_name

                if not home_team or not away_team:
                    self.stdout.write(f"Could not extract teams from competitors for game: {game_name}")
                    return None

            self.stdout.write(
                f"Extracted: Week {week}, "
                f"{self.get_team_abbreviation(away_team)} @ {self.get_team_abbreviation(home_team)}, "
                f"{start_time.isoformat()} (UTC), window_key={window_key}"
            )

            return {
                "week": week,
                "home_team": home_team,
                "away_team": away_team,
                "start_time": start_time,   # aware UTC
                "window_key": window_key,   # PT-based label
            }

        except Exception as e:
            self.stdout.write(f"Error extracting game info: {e}")
            return None

    def create_or_update_game(self, game_info):
        """Create or update game in database"""
        try:
            game, created = Game.objects.get_or_create(
                season=NFL_SEASON,
                week=game_info["week"],
                home_team=game_info["home_team"],
                away_team=game_info["away_team"],
                defaults={
                    "start_time": game_info["start_time"],  # UTC
                    "window_key": game_info["window_key"],  # PT label
                },
            )

            if not created:
                # Update fields if changed
                changed = False
                if game.start_time != game_info["start_time"]:
                    game.start_time = game_info["start_time"]
                    changed = True
                if getattr(game, "window_key", None) != game_info["window_key"]:
                    game.window_key = game_info["window_key"]
                    changed = True
                if changed:
                    game.save()

            return created

        except Exception as e:
            self.stdout.write(f"Error creating/updating game: {e}")
            return False