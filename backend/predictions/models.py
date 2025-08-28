from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint, Index
from django.contrib.auth import get_user_model

from games.models import Game, PropBet

User = get_user_model()

class MoneyLinePrediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="moneyline_predictions")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moneyline_predictions")
    predicted_winner = models.CharField(max_length=50, default="N/A")
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Money-line prediction"
        verbose_name_plural = "Money-line predictions"
        constraints = [
            UniqueConstraint(fields=["user", "game"], name="uniq_ml_user_game"),
        ]
        indexes = [
            Index(fields=["user", "is_correct"]),
            Index(fields=["game", "is_correct"]),
        ]

    def clean(self):
        # must be a valid team (or "N/A")
        valid = {self.game.home_team, self.game.away_team, "N/A"}
        if self.predicted_winner not in valid:
            raise ValidationError("Pick must be home, away, or 'N/A'.")
        # no edits after lock
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            if old.predicted_winner != self.predicted_winner and self.game.is_locked:
                raise ValidationError("Cannot change pick after the game is locked.")
        else:
            if self.game.is_locked:
                raise ValidationError("Cannot create a pick after the game is locked.")

    def __str__(self):
        return f"{self.user} → {self.game}: {self.predicted_winner}"


class PropBetPrediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prop_bet_predictions")
    prop_bet = models.ForeignKey(PropBet, on_delete=models.CASCADE, related_name="prop_bet_predictions")
    answer = models.CharField(max_length=100)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "prop_bet"], name="uniq_pb_user_prop"),
        ]
        indexes = [
            Index(fields=["user", "is_correct"]),
            Index(fields=["prop_bet", "is_correct"]),
        ]

    def clean(self):
        opts = self.prop_bet.options or []
        if opts and self.answer not in opts:
            raise ValidationError("Answer must be one of the defined options.")
        game = self.prop_bet.game
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            if old.answer != self.answer and game.is_locked:
                raise ValidationError("Cannot change answer after the game is locked.")
        else:
            if game.is_locked:
                raise ValidationError("Cannot create an answer after the game is locked.")

    def __str__(self):
        return f"{self.user} → PB#{self.prop_bet_id}: {self.answer}"

class UserStatHistory(models.Model):
    """
    Weekly snapshot of user statistics and performance data.
    Contains both weekly stats and cumulative season data for fast calculations.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)
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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
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