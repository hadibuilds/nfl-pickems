from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg
from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat

User = get_user_model()

class Command(BaseCommand):
    help = 'Show overview of mock data for testing'

    def handle(self, *args, **options):
        self.stdout.write("🏈 MOCK NFL DATA OVERVIEW")
        self.stdout.write("=" * 50)
        
        # Basic counts
        users_count = User.objects.count()
        windows_count = Window.objects.count()
        games_count = Game.objects.count()
        props_count = PropBet.objects.count()
        ml_predictions = MoneyLinePrediction.objects.count()
        prop_predictions = PropBetPrediction.objects.count()
        user_stats = UserWindowStat.objects.count()
        
        self.stdout.write(f"\n📊 DATA SUMMARY:")
        self.stdout.write(f"   • Users: {users_count}")
        self.stdout.write(f"   • Windows: {windows_count}")
        self.stdout.write(f"   • Games: {games_count}")
        self.stdout.write(f"   • Prop Bets: {props_count}")
        self.stdout.write(f"   • ML Predictions: {ml_predictions}")
        self.stdout.write(f"   • Prop Predictions: {prop_predictions}")
        self.stdout.write(f"   • User Window Stats: {user_stats}")
        
        # Week breakdown
        self.stdout.write(f"\n📅 WEEKLY BREAKDOWN:")
        weeks_data = Game.objects.values('week').annotate(
            game_count=Count('id'),
            window_count=Count('window', distinct=True)
        ).order_by('week')
        
        for week_data in weeks_data:
            self.stdout.write(f"   Week {week_data['week']}: {week_data['game_count']} games across {week_data['window_count']} windows")
        
        # User participation
        self.stdout.write(f"\n👥 USER PARTICIPATION (Top 10):")
        participation_data = User.objects.annotate(
            ml_count=Count('moneyline_predictions', distinct=True),
            prop_count=Count('prop_bet_predictions', distinct=True),
            stat_count=Count('window_stats', distinct=True)
        ).filter(ml_count__gt=0).order_by('-ml_count')[:10]
        
        for user in participation_data:
            self.stdout.write(f"   {user.username}: {user.ml_count} ML + {user.prop_count} prop predictions, {user.stat_count} windows tracked")
        
        # Top performers (get latest stats for each user)
        self.stdout.write(f"\n🏆 TOP PERFORMERS (by cumulative points):")
        
        # Get the most recent window for each user to show their latest cumulative points
        latest_window_id = Window.objects.filter(is_complete=True).order_by('-date', '-slot').first().id if Window.objects.filter(is_complete=True).exists() else None
        
        if latest_window_id:
            top_performers = UserWindowStat.objects.select_related('user').filter(
                window_id=latest_window_id
            ).order_by('-season_cume_points')[:10]
            
            for i, stat in enumerate(top_performers, 1):
                self.stdout.write(f"   {i}. {stat.user.username}: {stat.season_cume_points} points (rank {stat.rank_dense})")
        else:
            self.stdout.write("   No completed windows yet")
        
        # Window completion status
        completed_windows = Window.objects.filter(is_complete=True).count()
        self.stdout.write(f"\n✅ COMPLETION STATUS:")
        self.stdout.write(f"   • Completed windows: {completed_windows} / {windows_count}")
        self.stdout.write(f"   • Games with results: {Game.objects.exclude(winner__isnull=True).count()} / {games_count}")
        self.stdout.write(f"   • Props with answers: {PropBet.objects.exclude(correct_answer__isnull=True).count()} / {props_count}")
        
        # Admin access
        self.stdout.write(f"\n🔗 ADMIN ACCESS:")
        self.stdout.write(f"   URL: http://localhost:8000/admin/")
        self.stdout.write(f"   Username: admin")
        self.stdout.write(f"   Password: admin123")
        
        self.stdout.write(f"\n📝 ADMIN SECTIONS TO EXPLORE:")
        self.stdout.write(f"   • Games > Windows: View window structure and completion")
        self.stdout.write(f"   • Games > Games: See all games with winners")
        self.stdout.write(f"   • Games > Prop bets: View prop questions and answers")
        self.stdout.write(f"   • Analytics > User window stats: Rankings and points")
        self.stdout.write(f"   • Accounts > Custom users: All test users")
        
        self.stdout.write(f"\n🎮 UI TESTING READY:")
        self.stdout.write(f"   • Season spans 10 weeks with realistic NFL structure")
        self.stdout.write(f"   • Multiple user performance levels for ranking tests")
        self.stdout.write(f"   • All windows through Week 10 are complete with results")
        self.stdout.write(f"   • Rich prediction data for dashboard testing")
        
        self.stdout.write(f"\n✓ Mock data overview complete!")