from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, datetime, timezone as dt_timezone, timedelta
import random
from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.services.window_stats_optimized import recompute_window_optimized

User = get_user_model()

class Command(BaseCommand):
    help = 'Create comprehensive mock NFL data for testing - 272 games through Week 10'

    # Real NFL teams for 2024
    NFL_TEAMS = [
        'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE',
        'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAC', 'KC',
        'LV', 'LAC', 'LAR', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
        'NYJ', 'PHI', 'PIT', 'SF', 'SEA', 'TB', 'TEN', 'WAS'
    ]

    # Realistic prop bet questions
    PROP_QUESTIONS = [
        ("Total Points Over/Under", "Over 45.5", "Under 45.5"),
        ("First Score", "Touchdown", "Field Goal"),
        ("Longest TD", "Over 25 yards", "Under 25 yards"),
        ("Turnovers", "Over 2.5 total", "Under 2.5 total"),
        ("Sacks", "Over 4.5 total", "Under 4.5 total"),
        ("Red Zone TDs", "Over 3.5", "Under 3.5"),
        ("Passing Yards", "Over 275", "Under 275"),
        ("Rushing Yards", "Over 125", "Under 125"),
    ]

    def handle(self, *args, **options):
        self.stdout.write("🏈 Creating comprehensive mock NFL data simulation...")
        
        # Clear existing data
        self.clear_existing_data()
        
        # Create users
        users = self.create_users()
        
        # Create season structure
        windows = self.create_season_structure()
        
        # Create games and predictions
        total_games = self.create_games_and_predictions(windows, users)
        
        # Recompute all window stats
        self.recompute_all_windows(windows)
        
        self.stdout.write(f"\n✅ Mock data creation complete!")
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   • Users: {len(users)}")
        self.stdout.write(f"   • Windows: {len(windows)}")
        self.stdout.write(f"   • Games: {total_games}")
        self.stdout.write(f"   • Prop Bets: {total_games * 3}")  # 3 props per game
        self.stdout.write(f"\n🔗 Access admin at: http://localhost:8000/admin/")
        self.stdout.write(f"   Username: admin")
        self.stdout.write(f"   Password: admin123")

    def clear_existing_data(self):
        self.stdout.write("🧹 Clearing existing data...")
        
        # Clear in dependency order
        PropBetPrediction.objects.all().delete()
        MoneyLinePrediction.objects.all().delete()
        PropBet.objects.all().delete()
        Game.objects.all().delete()
        Window.objects.all().delete()
        
        # Keep superuser, delete test users
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write("✓ Existing data cleared")

    def create_users(self):
        self.stdout.write("👥 Creating mock users...")
        
        users = []
        
        # Create superuser if doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@nflpickems.com',
                password='admin123'
            )
            users.append(admin)
        
        # Create diverse test users
        user_names = [
            'football_guru', 'touchdown_tony', 'quarterback_queen', 'blitz_betty',
            'endzone_eddie', 'field_goal_fred', 'linebacker_lucy', 'safety_sam',
            'running_rachel', 'passing_pete', 'defense_dave', 'kicker_kate',
            'coach_carlos', 'analyst_anna', 'rookie_ryan', 'veteran_vic',
            'fantasy_frank', 'stats_steve', 'upset_ursula', 'favorite_phil'
        ]
        
        for i, username in enumerate(user_names):
            user = User.objects.create_user(
                username=username,
                email=f'{username}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        self.stdout.write(f"✓ Created {len(users)} users")
        return users

    def create_season_structure(self):
        self.stdout.write("📅 Creating 2024 season structure...")
        
        season = 2024
        windows = []
        
        # Week 1: TNF opener (1 game)
        week1_date = date(2024, 9, 5)  # Thursday
        window = Window.objects.create(
            season=season,
            date=week1_date,
            slot='evening',
            is_complete=True
        )
        windows.append(window)
        
        # Weeks 1-10: Standard NFL schedule
        current_date = date(2024, 9, 8)  # Week 1 Sunday
        
        for week in range(1, 11):  # Weeks 1-10
            week_start = current_date + timedelta(days=(week-1) * 7)
            
            # Sunday early games
            windows.append(Window.objects.create(
                season=season,
                date=week_start,
                slot='early',
                is_complete=True if week <= 10 else False
            ))
            
            # Sunday afternoon games  
            windows.append(Window.objects.create(
                season=season,
                date=week_start,
                slot='afternoon',
                is_complete=True if week <= 10 else False
            ))
            
            # Sunday night game
            windows.append(Window.objects.create(
                season=season,
                date=week_start,
                slot='night',
                is_complete=True if week <= 10 else False
            ))
            
            # Monday night game
            monday = week_start + timedelta(days=1)
            windows.append(Window.objects.create(
                season=season,
                date=monday,
                slot='night',
                is_complete=True if week <= 10 else False
            ))
            
            # Thursday night (weeks 2+)
            if week > 1:
                thursday = week_start + timedelta(days=4)
                windows.append(Window.objects.create(
                    season=season,
                    date=thursday,
                    slot='evening',
                    is_complete=True if week <= 10 else False
                ))
        
        self.stdout.write(f"✓ Created {len(windows)} windows")
        return windows

    def create_games_and_predictions(self, windows, users):
        self.stdout.write("🏈 Creating games, prop bets, and predictions...")
        
        total_games = 0
        used_matchups = set()  # Track used (season, week, away, home) combinations
        
        for i, window in enumerate(windows):
            week = max(1, (i // 5) + 1)  # Better week calculation 
            
            # Determine games per window based on slot
            if window.slot == 'evening' and week == 1:  # TNF opener
                games_count = 1
            elif window.slot == 'early':
                games_count = random.randint(3, 5)  # Sunday early (reduced to avoid duplicates)
            elif window.slot == 'afternoon': 
                games_count = random.randint(2, 4)  # Sunday afternoon
            elif window.slot == 'night':
                games_count = 1  # SNF/MNF/TNF
            else:
                games_count = 1
                
            # Create games for this window
            attempts = 0
            games_created = 0
            
            while games_created < games_count and attempts < 50:  # Prevent infinite loop
                attempts += 1
                
                # Pick random matchup
                away_team = random.choice(self.NFL_TEAMS)
                home_team = random.choice(self.NFL_TEAMS)
                
                # Ensure different teams and unique matchup for this week
                if away_team == home_team:
                    continue
                    
                matchup_key = (window.season, week, away_team, home_team)
                if matchup_key in used_matchups:
                    continue
                    
                used_matchups.add(matchup_key)
                
                # Determine winner (slight home field advantage)
                winner = home_team if random.random() < 0.55 else away_team
                
                try:
                    game = Game.objects.create(
                        window=window,
                        away_team=away_team,
                        home_team=home_team,
                        season=window.season,
                        week=week,
                        start_time=datetime.combine(window.date, datetime.min.time().replace(hour=13, minute=0, tzinfo=dt_timezone.utc)),
                        winner=winner,
                        locked=window.is_complete
                    )
                    games_created += 1
                except Exception as e:
                    # Skip duplicate matchups
                    continue
                
                # Create prop bets for this game
                self.create_prop_bets(game)
                
                # Create predictions for this game
                self.create_predictions(game, users)
                
                total_games += 1
        
        self.stdout.write(f"✓ Created {total_games} games with predictions")
        return total_games

    def create_prop_bets(self, game):
        """Create 3 random prop bets per game"""
        selected_props = random.sample(self.PROP_QUESTIONS, 3)
        
        for question, option_a, option_b in selected_props:
            # Determine correct answer (use the actual option text)
            options = [option_a, option_b]
            correct_answer = random.choice(options)
            
            PropBet.objects.create(
                game=game,
                category='over_under',  # Default category
                question=f"{game.away_team} @ {game.home_team}: {question}",
                options=options,  # JSON array
                correct_answer=correct_answer
            )

    def create_predictions(self, game, users):
        """Create predictions for a subset of users (realistic participation)"""
        # Not all users predict every game (70-85% participation rate)
        participating_users = random.sample(users, k=random.randint(int(len(users)*0.7), int(len(users)*0.85)))
        
        for user in participating_users:
            # Money line prediction
            predicted_winner = random.choice([game.away_team, game.home_team])
            is_correct = (predicted_winner == game.winner)
            
            MoneyLinePrediction.objects.create(
                user=user,
                game=game,
                predicted_winner=predicted_winner,
                is_correct=is_correct
            )
            
            # Prop bet predictions (user might skip some props)
            prop_bets = PropBet.objects.filter(game=game)
            for prop_bet in prop_bets:
                if random.random() < 0.8:  # 80% chance user makes prop prediction
                    predicted_answer = random.choice(prop_bet.options)
                    is_correct = (predicted_answer == prop_bet.correct_answer)
                    
                    PropBetPrediction.objects.create(
                        user=user,
                        prop_bet=prop_bet,
                        answer=predicted_answer,
                        is_correct=is_correct
                    )

    def recompute_all_windows(self, windows):
        self.stdout.write("⚡ Computing window statistics...")
        
        # Recompute windows in chronological order
        completed_windows = [w for w in windows if w.is_complete]
        completed_windows.sort(key=lambda w: (w.date, w.slot))
        
        for window in completed_windows:
            try:
                recompute_window_optimized(window.id)
            except Exception as e:
                self.stdout.write(f"⚠️  Error computing window {window.id}: {e}")
        
        self.stdout.write(f"✓ Computed statistics for {len(completed_windows)} windows")