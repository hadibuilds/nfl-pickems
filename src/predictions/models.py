from django.db import models
from django.conf import settings
from games.models import Game
import inspect

class Prediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    predicted_winner = models.CharField(max_length=50, default="N/A")
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Money-line prediction"
        verbose_name_plural = "Money-line predictions"
        unique_together = ('user', 'game')
        indexes = [
            models.Index(fields=["user", "is_correct"]),
            models.Index(fields=["game", "is_correct"]),
        ]

    def save(self, *args, **kwargs):
        # Allow updates to correctness even when locked
        if self.pk:
            old = Prediction.objects.get(pk=self.pk)
            updating_correctness_only = (
                self.predicted_winner == old.predicted_winner and
                self.game == old.game and
                self.user == old.user
            )
        else:
            updating_correctness_only = False

        if self.game.is_locked and not updating_correctness_only:
            # Allow saving from admin
            if not any('django/contrib/admin' in frame.filename for frame in inspect.stack()):
                raise ValueError("This game is locked. Predictions cannot be changed.")

        if self.predicted_winner not in [self.game.home_team, self.game.away_team]:
            raise ValueError("Invalid prediction: Team not in this game")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.game.winner is not None:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - Week {self.game.week}: {self.predicted_winner} ({status})"
        return f"{self.user.username} - Week {self.game.week}: {self.predicted_winner}"


class PropBet(models.Model):
    CATEGORY_CHOICES = [
        ('over_under', 'Over/Under'),
        ('point_spread', 'Point Spread'),
        ('take_the_bait', 'Take-the-Bait')
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="prop_bets")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=list)
    correct_answer = models.CharField(max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.correct_answer:
            for prediction in self.propbetprediction_set.all():
                prediction.is_correct = (prediction.answer == self.correct_answer)
                prediction.save()

    def __str__(self):
        return f"Week {self.game.week} ({self.category}): {self.question}"


class PropBetPrediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prop_bet = models.ForeignKey(PropBet, on_delete=models.CASCADE)
    answer = models.CharField(max_length=50)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'prop_bet')
        indexes = [
            models.Index(fields=["user", "is_correct"]),
            models.Index(fields=["prop_bet", "is_correct"]),
        ]

    def save(self, *args, **kwargs):
        # Allow updates to correctness even when locked
        if self.pk:
            old = PropBetPrediction.objects.get(pk=self.pk)
            updating_correctness_only = (
                self.user == old.user and
                self.prop_bet == old.prop_bet and
                self.answer == old.answer
            )
        else:
            updating_correctness_only = False

        if hasattr(self, 'prop_bet') and hasattr(self.prop_bet, 'game') \
           and self.prop_bet.game.is_locked and not updating_correctness_only:
            if not any('django/contrib/admin' in frame.filename for frame in inspect.stack()):
                raise ValueError("This prop bet is locked. You cannot change your prediction.")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.prop_bet.correct_answer:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - {self.prop_bet.question} ({status})"
        return f"{self.user.username} - {self.prop_bet.question}"


# NOTE: Keeping these small tables for audit/frozen weekly views only
class WeeklySnapshot(models.Model):
    """Deprecated as a source of truth. (Kept only for back-compat reads.)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    week = models.IntegerField()
    weekly_points = models.IntegerField(default=0)
    weekly_game_correct = models.IntegerField(default=0)
    weekly_game_total = models.IntegerField(default=0)
    weekly_prop_correct = models.IntegerField(default=0)
    weekly_prop_total = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    total_game_correct = models.IntegerField(default=0)
    total_game_total = models.IntegerField(default=0)
    total_prop_correct = models.IntegerField(default=0)
    total_prop_total = models.IntegerField(default=0)
    rank = models.IntegerField()
    total_users = models.IntegerField()
    points_from_leader = models.IntegerField(default=0)
    weekly_accuracy = models.FloatField(null=True, blank=True)
    overall_accuracy = models.FloatField(null=True, blank=True)
    moneyline_accuracy = models.FloatField(null=True, blank=True)
    prop_accuracy = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'week')
        ordering = ['week', 'rank']

    def __str__(self):
        return f"{self.user.username} - Week {self.week} (#{self.rank})"


# Updated models.py - Rename RankHistory to UserStatHistory

class UserStatHistory(models.Model):
    """
    Weekly snapshot of user statistics and performance data.
    Contains both weekly stats and cumulative season data for fast calculations.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, editable=False)
    week = models.IntegerField(editable=False)
    
    # Ranking information
    rank = models.IntegerField(editable=False)
    previous_rank = models.IntegerField(null=True, blank=True, editable=False)
    rank_change = models.IntegerField(default=0, editable=False)
    total_points = models.IntegerField(default=0, editable=False)
    
    # Weekly statistics (this week only)
    week_points = models.IntegerField(default=0, editable=False)
    week_moneyline_correct = models.IntegerField(default=0, editable=False)
    week_moneyline_total = models.IntegerField(default=0, editable=False)
    week_prop_correct = models.IntegerField(default=0, editable=False)
    week_prop_total = models.IntegerField(default=0, editable=False)
    
    # Cumulative season statistics (through this week)
    season_moneyline_correct = models.IntegerField(default=0, editable=False)
    season_moneyline_total = models.IntegerField(default=0, editable=False)
    season_prop_correct = models.IntegerField(default=0, editable=False)
    season_prop_total = models.IntegerField(default=0, editable=False)
    
    # Pre-calculated percentages for performance
    week_accuracy = models.FloatField(default=0.0, editable=False)
    season_accuracy = models.FloatField(default=0.0, editable=False)
    moneyline_accuracy = models.FloatField(default=0.0, editable=False)
    prop_accuracy = models.FloatField(default=0.0, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        unique_together = ('user', 'week')
        ordering = ['week', 'rank']
        verbose_name = "User Statistics History"
        verbose_name_plural = "User Statistics History"
        indexes = [
            models.Index(fields=['user', '-week']),  # For getting user's latest snapshots
            models.Index(fields=['week', 'rank']),   # For leaderboard queries
            models.Index(fields=['-total_points']),  # For ranking queries
        ]

    @property
    def trend_direction(self):
        """Rank trend direction (up = rank improved, down = rank declined)."""
        if self.rank_change > 0:
            return 'up'  # Rank improved (lower number = better)
        elif self.rank_change < 0:
            return 'down'  # Rank declined (higher number = worse)
        else:
            return 'same'

    @property
    def rank_change_display(self):
        """Human-readable rank change display."""
        if self.rank_change > 0:
            return f"+{self.rank_change}"
        elif self.rank_change < 0:
            return str(self.rank_change)
        else:
            return "—"

    @property
    def week_predictions_total(self):
        """Total predictions made this week."""
        return self.week_moneyline_total + self.week_prop_total

    @property
    def week_predictions_correct(self):
        """Total correct predictions this week."""
        return self.week_moneyline_correct + self.week_prop_correct

    @property
    def season_predictions_total(self):
        """Total predictions made this season."""
        return self.season_moneyline_total + self.season_prop_total

    @property
    def season_predictions_correct(self):
        """Total correct predictions this season."""
        return self.season_moneyline_correct + self.season_prop_correct

    def __str__(self):
        return f"{self.user.username} - Week {self.week}: #{self.rank} ({self.total_points} pts, {self.rank_change_display})"


# DEPRECATED: Use UserStatHistory instead - proxy model exists for backward compatibility only.
class RankHistory(UserStatHistory):
    class Meta:
        proxy = True
        verbose_name = "Rank History (Deprecated)"
        verbose_name_plural = "Rank History (Deprecated)"


class LeaderboardSnapshot(models.Model):
    week = models.IntegerField()
    snapshot_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('week',)
    
    def save(self, *args, **kwargs):
        # Allow creation but prevent updates
        if self.pk and not kwargs.pop('force_update', False):
            raise ValueError("LeaderboardSnapshot is read-only. Use force_update=True to override.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Leaderboard - Week {self.week}"


class SeasonStats(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Performance records
    best_week_points = models.IntegerField(default=0)
    best_week_number = models.IntegerField(null=True, blank=True)
    
    # Rank achievements (much more meaningful than streaks)
    best_rank = models.IntegerField(null=True, blank=True)
    best_rank_week = models.IntegerField(null=True, blank=True)
    worst_rank = models.IntegerField(null=True, blank=True)
    
    # Rank consistency metrics
    weeks_at_rank_1 = models.IntegerField(default=0)
    weeks_in_top_3 = models.IntegerField(default=0)
    weeks_in_top_5 = models.IntegerField(default=0)
    consecutive_weeks_at_1 = models.IntegerField(default=0)  # Current streak at #1
    max_consecutive_weeks_at_1 = models.IntegerField(default=0)  # Best streak at #1
    
    # Movement records
    biggest_rank_climb = models.IntegerField(default=0)  # Spots climbed in single week
    biggest_rank_fall = models.IntegerField(default=0)   # Spots fallen in single week
    
    # Category performance
    favorite_team_picked = models.CharField(max_length=50, blank=True)
    favorite_team_pick_count = models.IntegerField(default=0)
    best_category = models.CharField(
        max_length=20, 
        choices=[('moneyline', 'Moneyline'), ('prop', 'Prop Bets'), ('balanced', 'Balanced')],
        default='balanced'
    )
    
    # Overall trend
    trending_direction = models.CharField(
        max_length=10,
        choices=[('up', 'Trending Up'), ('down', 'Trending Down'), ('stable', 'Stable')],
        default='stable'
    )
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Season Stats"
    
    @property 
    def rank_consistency_score(self):
        """Calculate a consistency score based on time in top ranks."""
        if not hasattr(self, '_total_weeks'):
            # This would be calculated when updating stats
            return 0
        
        total_weeks = getattr(self, '_total_weeks', 1)
        top3_percentage = (self.weeks_in_top_3 / total_weeks) * 100
        top5_percentage = (self.weeks_in_top_5 / total_weeks) * 100
        
        # Weighted score: top 3 worth more than top 5
        return (top3_percentage * 0.7) + (top5_percentage * 0.3)
    
    @property
    def peak_performance_summary(self):
        """Summary of user's best achievements."""
        summary = []
        
        if self.weeks_at_rank_1 > 0:
            summary.append(f"Led league {self.weeks_at_rank_1} time(s)")
            
        if self.max_consecutive_weeks_at_1 >= 2:
            summary.append(f"Longest reign: {self.max_consecutive_weeks_at_1} weeks at #1")
            
        if self.biggest_rank_climb >= 5:
            summary.append(f"Biggest comeback: +{self.biggest_rank_climb} spots")
            
        return " | ".join(summary) if summary else "Building achievements..."