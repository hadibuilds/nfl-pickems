from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import Window, Game
from predictions.models import MoneyLinePrediction
from analytics.models import UserWindowStat

User = get_user_model()

class Command(BaseCommand):
    help = 'Inspect existing data for non-participant analysis'

    def handle(self, *args, **options):
        self.stdout.write("=== INSPECTING EXISTING DATA ===")
        
        try:
            # Check users
            users = User.objects.all()[:10]
            self.stdout.write(f"Total users: {User.objects.count()}")
            for user in users:
                self.stdout.write(f"  - {user.username} (id: {user.id})")
            
            # Check windows
            windows = Window.objects.all().order_by('date', 'slot')[:10]
            self.stdout.write(f"\nTotal windows: {Window.objects.count()}")
            for window in windows:
                self.stdout.write(f"  - Window {window.id}: {window.date} {window.slot} (season {window.season})")
            
            # Check games
            games = Game.objects.all()[:5]
            self.stdout.write(f"\nTotal games: {Game.objects.count()}")
            for game in games:
                self.stdout.write(f"  - Game {game.id}: {game.away_team} @ {game.home_team} (Window {game.window_id})")
            
            # Check predictions
            predictions = MoneyLinePrediction.objects.all()[:5]
            self.stdout.write(f"\nTotal ML predictions: {MoneyLinePrediction.objects.count()}")
            for pred in predictions:
                self.stdout.write(f"  - User {pred.user_id} -> Game {pred.game_id}: {pred.predicted_winner} ({'✓' if pred.is_correct else '✗'})")
            
            # Check existing UserWindowStats
            stats = UserWindowStat.objects.all()[:5]
            self.stdout.write(f"\nTotal UserWindowStats: {UserWindowStat.objects.count()}")
            for stat in stats:
                self.stdout.write(f"  - User {stat.user_id}, Window {stat.window_id}: {stat.window_points} pts, rank {stat.rank_dense}")
                
        except Exception as e:
            self.stdout.write(f"Error: {e}")
            
        self.stdout.write("\n✓ Data inspection complete")