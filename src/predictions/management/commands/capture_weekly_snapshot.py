# predictions/management/commands/capture_weekly_snapshot.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from predictions.models import (
    Prediction, PropBetPrediction, WeeklySnapshot, 
    RankHistory, UserStreak, LeaderboardSnapshot, SeasonStats
)
from games.models import Game
from collections import defaultdict
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Capture weekly snapshot of user statistics and rankings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week',
            type=int,
            help='Week number to capture (defaults to latest completed week)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recapture even if snapshot exists',
        )

    def handle(self, *args, **options):
        week = options.get('week')
        force = options.get('force', False)
        
        if not week:
            # Find the latest week with completed games
            latest_week = self.get_latest_completed_week()
            if not latest_week:
                self.stdout.write(
                    self.style.WARNING('No completed weeks found')
                )
                return
            week = latest_week
        
        self.stdout.write(f"Capturing snapshot for Week {week}...")
        
        # Check if snapshot already exists
        if WeeklySnapshot.objects.filter(week=week).exists() and not force:
            self.stdout.write(
                self.style.WARNING(f'Snapshot for Week {week} already exists. Use --force to overwrite.')
            )
            return
        
        # Delete existing snapshots for this week if forcing
        if force:
            WeeklySnapshot.objects.filter(week=week).delete()
            RankHistory.objects.filter(week=week).delete()
            LeaderboardSnapshot.objects.filter(week=week).delete()
        
        # Capture snapshots
        self.capture_weekly_snapshots(week)
        self.capture_rank_history(week)
        self.update_streaks()
        self.capture_leaderboard_snapshot(week)
        self.update_season_stats(week)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully captured Week {week} snapshot')
        )

    def get_latest_completed_week(self):
        """Find the latest week where all games have results"""
        weeks_with_games = Game.objects.values_list('week', flat=True).distinct()
        
        for week in sorted(weeks_with_games, reverse=True):
            week_games = Game.objects.filter(week=week)
            completed_games = week_games.filter(winner__isnull=False)
            
            if week_games.count() == completed_games.count() and week_games.count() > 0:
                return week
        
        return None

    def capture_weekly_snapshots(self, week):
        """Capture detailed stats for each user for the given week"""
        users = User.objects.all()
        
        for user in users:
            # Calculate weekly stats
            weekly_stats = self.calculate_weekly_stats(user, week)
            cumulative_stats = self.calculate_cumulative_stats(user, week)
            
            # Get ranking info
            rank_info = self.calculate_user_rank(user, week)
            
            # Create or update snapshot
            WeeklySnapshot.objects.update_or_create(
                user=user,
                week=week,
                defaults={
                    # Weekly stats
                    'weekly_points': weekly_stats['points'],
                    'weekly_game_correct': weekly_stats['game_correct'],
                    'weekly_game_total': weekly_stats['game_total'],
                    'weekly_prop_correct': weekly_stats['prop_correct'],
                    'weekly_prop_total': weekly_stats['prop_total'],
                    
                    # Cumulative stats
                    'total_points': cumulative_stats['points'],
                    'total_game_correct': cumulative_stats['game_correct'],
                    'total_game_total': cumulative_stats['game_total'],
                    'total_prop_correct': cumulative_stats['prop_correct'],
                    'total_prop_total': cumulative_stats['prop_total'],
                    
                    # Ranking
                    'rank': rank_info['rank'],
                    'total_users': rank_info['total_users'],
                    'points_from_leader': rank_info['points_from_leader'],
                    
                    # Accuracies
                    'weekly_accuracy': weekly_stats['accuracy'],
                    'overall_accuracy': cumulative_stats['accuracy'],
                    'moneyline_accuracy': cumulative_stats['moneyline_accuracy'],
                    'prop_accuracy': cumulative_stats['prop_accuracy'],
                }
            )

    def calculate_weekly_stats(self, user, week):
        """Calculate stats for a specific week"""
        week_games = Game.objects.filter(week=week, winner__isnull=False)
        
        # Game predictions
        week_predictions = Prediction.objects.filter(
            user=user, 
            game__in=week_games
        )
        game_correct = week_predictions.filter(is_correct=True).count()
        game_total = week_predictions.count()
        
        # Prop predictions
        week_props = PropBetPrediction.objects.filter(
            user=user,
            prop_bet__game__in=week_games,
            is_correct__isnull=False
        )
        prop_correct = week_props.filter(is_correct=True).count()
        prop_total = week_props.count()
        
        # Calculate points and accuracy
        points = game_correct + (prop_correct * 2)
        total_predictions = game_total + prop_total
        accuracy = (game_correct + prop_correct) / total_predictions * 100 if total_predictions > 0 else 0
        
        return {
            'points': points,
            'game_correct': game_correct,
            'game_total': game_total,
            'prop_correct': prop_correct,
            'prop_total': prop_total,
            'accuracy': accuracy
        }

    def calculate_cumulative_stats(self, user, through_week):
        """Calculate cumulative stats through the given week"""
        completed_games = Game.objects.filter(week__lte=through_week, winner__isnull=False)
        
        # Game predictions
        all_predictions = Prediction.objects.filter(
            user=user,
            game__in=completed_games
        )
        game_correct = all_predictions.filter(is_correct=True).count()
        game_total = all_predictions.count()
        
        # Prop predictions
        all_props = PropBetPrediction.objects.filter(
            user=user,
            prop_bet__game__in=completed_games,
            is_correct__isnull=False
        )
        prop_correct = all_props.filter(is_correct=True).count()
        prop_total = all_props.count()
        
        # Calculate totals
        total_points = game_correct + (prop_correct * 2)
        total_predictions = game_total + prop_total
        
        # Calculate accuracies
        overall_accuracy = (game_correct + prop_correct) / total_predictions * 100 if total_predictions > 0 else 0
        moneyline_accuracy = game_correct / game_total * 100 if game_total > 0 else 0
        prop_accuracy = prop_correct / prop_total * 100 if prop_total > 0 else 0
        
        return {
            'points': total_points,
            'game_correct': game_correct,
            'game_total': game_total,
            'prop_correct': prop_correct,
            'prop_total': prop_total,
            'accuracy': overall_accuracy,
            'moneyline_accuracy': moneyline_accuracy,
            'prop_accuracy': prop_accuracy
        }

    def calculate_user_rank(self, user, through_week):
        """Calculate user's rank through the given week"""
        # Get all users' points through this week
        user_points = []
        for u in User.objects.all():
            stats = self.calculate_cumulative_stats(u, through_week)
            user_points.append((u, stats['points']))
        
        # Sort by points (descending)
        user_points.sort(key=lambda x: x[1], reverse=True)
        
        # Find user's rank
        rank = 1
        leader_points = user_points[0][1] if user_points else 0
        user_total_points = 0
        
        for i, (u, points) in enumerate(user_points):
            if u == user:
                rank = i + 1
                user_total_points = points
                break
        
        return {
            'rank': rank,
            'total_users': len(user_points),
            'points_from_leader': leader_points - user_total_points
        }

    def capture_rank_history(self, week):
        """Capture rank changes from previous week"""
        for user in User.objects.all():
            current_snapshot = WeeklySnapshot.objects.get(user=user, week=week)
            
            # Get previous week's rank
            previous_snapshot = WeeklySnapshot.objects.filter(
                user=user, 
                week__lt=week
            ).order_by('-week').first()
            
            previous_rank = previous_snapshot.rank if previous_snapshot else None
            rank_change = 0
            
            if previous_rank:
                # Rank change: positive = moved up (rank number decreased)
                rank_change = previous_rank - current_snapshot.rank
            
            RankHistory.objects.update_or_create(
                user=user,
                week=week,
                defaults={
                    'rank': current_snapshot.rank,
                    'previous_rank': previous_rank,
                    'rank_change': rank_change,
                    'total_points': current_snapshot.total_points
                }
            )

    def update_streaks(self):
        """Update current streaks for all users"""
        for user in User.objects.all():
            self.calculate_user_streak(user)

    def calculate_user_streak(self, user):
        """Calculate current win/loss streak for a user"""
        # Get recent predictions in chronological order
        recent_predictions = Prediction.objects.filter(
            user=user,
            is_correct__isnull=False
        ).select_related('game').order_by('-game__week', '-game__start_time')[:20]
        
        if not recent_predictions:
            return
        
        # Calculate current streak
        current_streak = 0
        streak_type = 'win' if recent_predictions[0].is_correct else 'loss'
        current_result = recent_predictions[0].is_correct
        
        for pred in recent_predictions:
            if pred.is_correct == current_result:
                current_streak += 1
            else:
                break
        
        # Calculate longest streaks
        longest_win = 0
        longest_loss = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for pred in reversed(list(recent_predictions)):
            if pred.is_correct:
                current_win_streak += 1
                longest_loss = max(longest_loss, current_loss_streak)
                current_loss_streak = 0
            else:
                current_loss_streak += 1
                longest_win = max(longest_win, current_win_streak)
                current_win_streak = 0
        
        longest_win = max(longest_win, current_win_streak)
        longest_loss = max(longest_loss, current_loss_streak)
        
        # Update or create streak record
        UserStreak.objects.update_or_create(
            user=user,
            defaults={
                'current_streak': current_streak,
                'streak_type': streak_type,
                'longest_win_streak': longest_win,
                'longest_loss_streak': longest_loss
            }
        )

    def capture_leaderboard_snapshot(self, week):
        """Capture full leaderboard for the week"""
        snapshots = WeeklySnapshot.objects.filter(week=week).order_by('rank')
        
        leaderboard_data = []
        for snapshot in snapshots:
            rank_history = RankHistory.objects.filter(user=snapshot.user, week=week).first()
            
            leaderboard_data.append({
                'rank': snapshot.rank,
                'username': snapshot.user.username,
                'points': snapshot.total_points,
                'weekly_points': snapshot.weekly_points,
                'rank_change': rank_history.rank_change if rank_history else 0,
                'trend': rank_history.trend_direction if rank_history else 'same'
            })
        
        LeaderboardSnapshot.objects.update_or_create(
            week=week,
            defaults={'snapshot_data': leaderboard_data}
        )

    def update_season_stats(self, week):
        """Update season-long statistics"""
        for user in User.objects.all():
            self.calculate_season_stats(user, week)