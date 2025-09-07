# Updated capture_weekly_snapshot.py with UserStatHistory

"""
Enhanced snapshot command: freeze leaderboard + detailed per-user weekly statistics.
Uses UserStatHistory model for comprehensive weekly and seasonal data storage.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from predictions.models import UserStatHistory, LeaderboardSnapshot, Prediction, PropBetPrediction
from games.models import Game

User = get_user_model()

class Command(BaseCommand):
    help = 'Create weekly user statistics snapshot for fast seasonal calculations'

    def add_arguments(self, parser):
        parser.add_argument('--week', type=int, help='Completed NFL week to snapshot. Default: latest completed week')
        parser.add_argument('--force', action='store_true', help='Overwrite existing snapshot for the week')

    def handle(self, *args, **opts):
        week = opts.get('week') or self._latest_completed_week()
        if not week:
            self.stdout.write(self.style.WARNING('No completed weeks found'))
            return

        if UserStatHistory.objects.filter(week=week).exists() and not opts.get('force'):
            self.stdout.write(self.style.WARNING(f'Week {week} snapshot already exists. Use --force to overwrite.'))
            return

        # Compute detailed weekly and seasonal statistics
        self.stdout.write(f'Computing detailed statistics for Week {week}...')
        user_stats = self._compute_detailed_weekly_stats(week)

        if opts.get('force'):
            self.stdout.write(self.style.WARNING(f'FORCE mode: Deleting existing Week {week} snapshots'))
            UserStatHistory.objects.filter(week=week).delete()
            LeaderboardSnapshot.objects.filter(week=week).delete()

        # Create compact leaderboard snapshot (with dense ranking)
        leaderboard_data = []
        current_rank = 1
        for i, stats in enumerate(user_stats):
            if i > 0 and stats['total_points'] < user_stats[i-1]['total_points']:
                current_rank += 1
            
            leaderboard_data.append({
                'rank': current_rank, 
                'username': stats['username'], 
                'points': stats['total_points'],
                'week_points': stats['week_points'],
                'accuracy': stats['season_accuracy']
            })
        
        LeaderboardSnapshot.objects.create(week=week, snapshot_data=leaderboard_data)

        # Create detailed user statistics history entries (with dense ranking)
        created_count = 0
        current_rank = 1
        for i, stats in enumerate(user_stats):
            if i > 0 and stats['total_points'] < user_stats[i-1]['total_points']:
                current_rank += 1
            
            user = stats['user_object']
            rank = current_rank
            
            # Get previous week's stats for trend calculation
            previous_stats = UserStatHistory.objects.filter(
                user=user, 
                week__lt=week
            ).order_by('-week').first()
            
            prev_rank = previous_stats.rank if previous_stats else None
            rank_change = (prev_rank - rank) if prev_rank else 0

            UserStatHistory.objects.create(
                user=user,
                week=week,
                rank=rank,
                previous_rank=prev_rank,
                rank_change=rank_change,
                total_points=stats['total_points'],
                
                # Weekly statistics
                week_points=stats['week_points'],
                week_moneyline_correct=stats['week_ml_correct'],
                week_moneyline_total=stats['week_ml_total'],
                week_prop_correct=stats['week_prop_correct'],
                week_prop_total=stats['week_prop_total'],
                
                # Seasonal cumulative statistics
                season_moneyline_correct=stats['season_ml_correct'],
                season_moneyline_total=stats['season_ml_total'],
                season_prop_correct=stats['season_prop_correct'],
                season_prop_total=stats['season_prop_total'],
                
                # Pre-calculated accuracies
                week_accuracy=stats['week_accuracy'],
                season_accuracy=stats['season_accuracy'],
                moneyline_accuracy=stats['moneyline_accuracy'],
                prop_accuracy=stats['prop_accuracy'],
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Week {week} snapshot completed successfully!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Created {created_count} user stat history records'))
        self.stdout.write(self.style.SUCCESS(f'📈 Created leaderboard snapshot with {len(leaderboard_data)} entries'))

    def _latest_completed_week(self):
        """Find the latest week where all games have results."""
        weeks = list(Game.objects.values_list('week', flat=True).distinct())
        for week in sorted(weeks, reverse=True):
            week_games = Game.objects.filter(week=week)
            if week_games.exists() and week_games.filter(winner__isnull=False).count() == week_games.count():
                return week
        return None

    def _compute_detailed_weekly_stats(self, through_week):
        """Compute comprehensive weekly and seasonal statistics for all users."""
        results = []
        
        for user in User.objects.all():
            # === THIS WEEK ONLY ===
            week_games = Game.objects.filter(week=through_week, winner__isnull=False)
            
            # Moneyline predictions for this week
            week_ml_preds = Prediction.objects.filter(user=user, game__in=week_games)
            week_ml_correct = week_ml_preds.filter(is_correct=True).count()
            week_ml_total = week_ml_preds.count()
            
            # Prop predictions for this week  
            week_prop_preds = PropBetPrediction.objects.filter(
                user=user, 
                prop_bet__game__in=week_games,
                is_correct__isnull=False
            )
            week_prop_correct = week_prop_preds.filter(is_correct=True).count()
            week_prop_total = week_prop_preds.count()
            
            # Week totals and accuracy
            week_points = week_ml_correct + (week_prop_correct * 2)
            week_total_preds = week_ml_total + week_prop_total
            week_correct_total = week_ml_correct + week_prop_correct
            week_accuracy = round(week_correct_total / week_total_preds * 100, 1) if week_total_preds > 0 else 0
            
            # === SEASON THROUGH THIS WEEK ===
            season_games = Game.objects.filter(week__lte=through_week, winner__isnull=False)
            
            # Season moneyline statistics
            season_ml_preds = Prediction.objects.filter(user=user, game__in=season_games)
            season_ml_correct = season_ml_preds.filter(is_correct=True).count()
            season_ml_total = season_ml_preds.count()
            
            # Season prop statistics
            season_prop_preds = PropBetPrediction.objects.filter(
                user=user,
                prop_bet__game__in=season_games,
                is_correct__isnull=False
            )
            season_prop_correct = season_prop_preds.filter(is_correct=True).count()
            season_prop_total = season_prop_preds.count()
            
            # Season calculations
            total_points = season_ml_correct + (season_prop_correct * 2)
            season_total_preds = season_ml_total + season_prop_total
            season_correct_total = season_ml_correct + season_prop_correct
            
            # Calculate accuracies
            season_accuracy = round(season_correct_total / season_total_preds * 100, 1) if season_total_preds > 0 else 0
            moneyline_accuracy = round(season_ml_correct / season_ml_total * 100, 1) if season_ml_total > 0 else 0
            prop_accuracy = round(season_prop_correct / season_prop_total * 100, 1) if season_prop_total > 0 else 0
            
            results.append({
                'user_object': user,
                'username': user.username,
                'total_points': total_points,
                
                # This week's performance
                'week_points': week_points,
                'week_ml_correct': week_ml_correct,
                'week_ml_total': week_ml_total,
                'week_prop_correct': week_prop_correct,
                'week_prop_total': week_prop_total,
                'week_accuracy': week_accuracy,
                
                # Season cumulative performance
                'season_ml_correct': season_ml_correct,
                'season_ml_total': season_ml_total,
                'season_prop_correct': season_prop_correct,
                'season_prop_total': season_prop_total,
                'season_accuracy': season_accuracy,
                'moneyline_accuracy': moneyline_accuracy,
                'prop_accuracy': prop_accuracy,
            })
        
        # Sort by total points (descending), then username (ascending) for tiebreakers
        results.sort(key=lambda x: (-x['total_points'], x['username']))
        return results