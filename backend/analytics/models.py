# analytics/models.py - Analytics App Models Organized by Concern

"""
Analytics App Models

***STANDINGS MODELS***:
- UserStatHistory: Weekly snapshots of user rankings and stats
- UserSeasonTotals: Materialized view of current season totals (used for realtime calculations)
- LeaderboardSnapshot: Historical leaderboard data for specific weeks
- Top3Snapshot: Windowed top-3 snapshots with correction tracking

***INSIGHTS MODELS***:  
- UserSeasonInsights: Season-long achievements and performance insights

***DEPRECATED/LEGACY***:
- WeeklySnapshot: Old snapshot system (marked for removal)

**WINDOWED SYSTEM***:
- UserWindowDeltas: Per-window point deltas for each user
- UserWindowCumulative: Cumulative totals and ranks after each window
"""

from django.db import models
from django.conf import settings
from games.models import Game, PropBet
from predictions.models import Prediction, PropBetPrediction, CorrectionEvent
from django.utils import timezone

# =============================================================================
# STANDINGS MODELS - Rankings, leaderboards, user positioning over time
# =============================================================================

class UserStatHistory(models.Model):
    """
    STANDINGS: Weekly snapshot of user statistics and performance data.
    Contains both weekly stats and cumulative season data for fast calculations.
    Used for tracking rank changes and trends over time.
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
            models.Index(fields=['user', '-week']),
            models.Index(fields=['week', 'rank']),
            models.Index(fields=['-total_points']),
        ]

    @property
    def trend_direction(self):
        """Rank trend direction (up = rank improved, down = rank declined)."""
        if self.rank_change > 0:
            return 'up'
        elif self.rank_change < 0:
            return 'down'
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
        return self.week_moneyline_total + self.week_prop_total

    @property
    def week_predictions_correct(self):
        return self.week_moneyline_correct + self.week_prop_correct

    @property
    def season_predictions_total(self):
        return self.season_moneyline_total + self.season_prop_total

    @property
    def season_predictions_correct(self):
        return self.season_moneyline_correct + self.season_prop_correct

    def __str__(self):
        return f"{self.user.username} - Week {self.week}: #{self.rank} ({self.total_points} pts, {self.rank_change_display})"


class UserSeasonTotals(models.Model):
    """
    STANDINGS: Materialized view of user season totals for fast realtime calculations.
    This model maps to the user_season_totals_mv created by migration.
    Used for quick lookups when calculating current standings with live data.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        db_column="user_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )
    ml_points = models.IntegerField()
    prop_points = models.IntegerField()
    total_points = models.IntegerField()

    class Meta:
        managed = False
        db_table = "user_season_totals_mv"

    def __str__(self):
        return f"{self.user.username}: {self.total_points} pts"


class LeaderboardSnapshot(models.Model):
    """
    STANDINGS: Historical leaderboard data for specific weeks.
    Stores full leaderboard state to enable historical comparisons and trends.
    """
    week = models.IntegerField()
    snapshot_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('week',)
        ordering = ['-week']
    
    def save(self, *args, **kwargs):
        if self.pk and not kwargs.pop('force_update', False):
            raise ValueError("LeaderboardSnapshot is read-only. Use force_update=True to override.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Leaderboard - Week {self.week}"


class Top3Snapshot(models.Model):
    """
    STANDINGS: Windowed top-3 snapshots with correction tracking.
    Stores top performers for specific time windows, tracks when corrections were applied.
    Format: window_key = "YYYY-MM-DD:morning|afternoon|late"
    """
    window_key = models.CharField(max_length=128, db_index=True)
    version = models.PositiveIntegerField()
    payload = models.JSONField()  # [{user_id, ml_points, prop_points, total_points, rank}, ...]
    created_at = models.DateTimeField(auto_now_add=True)
    correction_applied = models.BooleanField(default=False)
    correction_event = models.ForeignKey(
        "predictions.CorrectionEvent", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="snapshots"
    )
    
    class Meta:
        unique_together = (("window_key", "version"),)
        ordering = ["-created_at"]

    def __str__(self):
        return f"Top3Snapshot({self.window_key} v{self.version})"

# =============================================================================
# INSIGHTS MODELS - User achievements, performance analysis, trends
# =============================================================================

class UserSeasonInsights(models.Model):
    """
    INSIGHTS: Season-long user achievements and performance insights.
    Tracks meaningful accomplishments like rank consistency, peak performance,
    and category strengths. Used for user analytics and achievement displays.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Performance records
    best_week_points = models.IntegerField(default=0)
    best_week_number = models.IntegerField(null=True, blank=True)
    
    # Rank achievements
    best_rank = models.IntegerField(null=True, blank=True)
    best_rank_week = models.IntegerField(null=True, blank=True)
    worst_rank = models.IntegerField(null=True, blank=True)
    
    # Rank consistency metrics
    weeks_at_rank_1 = models.IntegerField(default=0)
    weeks_in_top_3 = models.IntegerField(default=0)
    weeks_in_top_5 = models.IntegerField(default=0)
    consecutive_weeks_at_1 = models.IntegerField(default=0)
    max_consecutive_weeks_at_1 = models.IntegerField(default=0)
    
    # Movement records
    biggest_rank_climb = models.IntegerField(default=0)
    biggest_rank_fall = models.IntegerField(default=0)
    
    # Category performance insights
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
        return f"{self.user.username} - Season Insights"
    
    @property 
    def rank_consistency_score(self):
        """Calculate consistency score based on time in top ranks."""
        # TODO: Implement when total_weeks tracking is added
        return 0
    
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

# =============================================================================
# WINDOWED RANKING SYSTEM MODELS - Time-based rank tracking with corrections
# =============================================================================

class UserWindowDeltas(models.Model):
    """
    WINDOWED STANDINGS: Point deltas earned by users in specific time windows.
    Tracks what each user earned during each window (morning/afternoon/late).
    Used as foundation for cumulative calculations and rank determination.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    season = models.IntegerField(db_index=True)
    window_key = models.CharField(max_length=64, db_index=True)  # "YYYY-MM-DD:morning|afternoon|late"
    
    # Point deltas for this window only
    ml_points_delta = models.IntegerField(default=0)
    prop_points_delta = models.IntegerField(default=0) 
    total_delta = models.IntegerField(default=0)
    
    # Meta information
    window_seq = models.IntegerField(db_index=True)  # For ordered calculations
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'season', 'window_key')
        ordering = ['season', 'window_seq', 'user']
        indexes = [
            models.Index(fields=['season', 'window_seq']),
            models.Index(fields=['user', 'season']),
            models.Index(fields=['window_key']),
        ]

    def save(self, *args, **kwargs):
        # Auto-calculate total_delta
        self.total_delta = self.ml_points_delta + self.prop_points_delta
        
        # Auto-calculate window_seq from window_key
        if not self.window_seq and self.window_key:
            self.window_seq = self._calculate_window_seq()
        
        super().save(*args, **kwargs)

    def _calculate_window_seq(self):
        """Convert window_key to sortable integer: YYYY-MM-DD:slot -> YYYYMMDD * 10 + slot_num"""
        try:
            date_part, slot_part = self.window_key.split(':')
            date_int = int(date_part.replace('-', ''))  # "2025-09-07" -> 20250907
            slot_map = {'morning': 1, 'afternoon': 2, 'late': 3}
            slot_num = slot_map.get(slot_part, 1)
            return date_int * 10 + slot_num  # 202509071, 202509072, 202509073
        except:
            return 0

    def __str__(self):
        return f"{self.user.username} - {self.window_key}: {self.total_delta} pts"


class UserWindowCumulative(models.Model):
    """
    WINDOWED STANDINGS: Cumulative totals and ranks after each window.
    Powers the windowed trend system with rank_before/rank_after tracking.
    Provides the foundation for trend arrows and historical analysis.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    season = models.IntegerField(db_index=True)
    window_key = models.CharField(max_length=64, db_index=True)
    window_seq = models.IntegerField(db_index=True)
    
    # Cumulative totals after this window
    cume_ml_after = models.IntegerField(default=0)
    cume_prop_after = models.IntegerField(default=0)  
    cume_total_after = models.IntegerField(default=0)
    
    # Ranking information
    rank_after = models.IntegerField(db_index=True)  # Dense rank after this window
    rank_before = models.IntegerField(null=True, blank=True)  # Rank before this window (from previous)
    rank_change = models.IntegerField(default=0)  # rank_before - rank_after (positive = improved)
    
    # Trend analysis
    trend = models.CharField(
        max_length=10,
        choices=[('up', 'Up'), ('down', 'Down'), ('same', 'Same')],
        default='same'
    )
    display_trend = models.BooleanField(default=True)  # False for first window
    
    # Meta information  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'season', 'window_key')
        ordering = ['season', 'window_seq', 'rank_after']
        indexes = [
            models.Index(fields=['season', 'window_seq', 'rank_after']),
            models.Index(fields=['user', 'season', 'window_seq']),
            models.Index(fields=['window_key', 'rank_after']),
        ]

    def save(self, *args, **kwargs):
        # Auto-calculate trend from rank_change
        if self.rank_before is not None:
            if self.rank_change > 0:
                self.trend = 'up'
            elif self.rank_change < 0:
                self.trend = 'down'
            else:
                self.trend = 'same'
        
        super().save(*args, **kwargs)

    @property
    def rank_change_display(self):
        """Human-readable rank change display"""
        if not self.display_trend:
            return "—"
        if self.rank_change > 0:
            return f"+{self.rank_change}"
        elif self.rank_change < 0:
            return str(self.rank_change)  # Already negative
        else:
            return "—"

    @property 
    def is_first_window(self):
        """Check if this is the first real window (no trend display)"""
        return not self.display_trend

    def __str__(self):
        trend_display = self.rank_change_display if self.display_trend else "—"
        return f"{self.user.username} - {self.window_key}: #{self.rank_after} ({trend_display})"


# =============================================================================
# WINDOWED SYSTEM MATERIALIZED VIEWS (for performance)
# =============================================================================

class UserWindowDeltasMV(models.Model):
    """
    WINDOWED PERFORMANCE: Materialized view for fast delta calculations.
    Auto-refreshed when games/props are updated.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    season = models.IntegerField()
    window_key = models.CharField(max_length=64)
    window_seq = models.IntegerField()
    ml_points_delta = models.IntegerField()
    prop_points_delta = models.IntegerField()
    total_delta = models.IntegerField()

    class Meta:
        managed = False
        db_table = "user_window_deltas_mv"

    def __str__(self):
        return f"{self.user.username} - {self.window_key}: {self.total_delta}"


class UserWindowCumulativeMV(models.Model):
    """
    WINDOWED PERFORMANCE: Materialized view for fast cumulative calculations.
    Powers homepage top-3 and standings page trend arrows.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    season = models.IntegerField()
    window_key = models.CharField(max_length=64)
    window_seq = models.IntegerField()
    cume_ml_after = models.IntegerField()
    cume_prop_after = models.IntegerField()
    cume_total_after = models.IntegerField()
    rank_after = models.IntegerField()
    rank_before = models.IntegerField(null=True)
    rank_change = models.IntegerField()
    trend = models.CharField(max_length=10)
    display_trend = models.BooleanField()

    class Meta:
        managed = False 
        db_table = "user_window_cume_mv"

    def __str__(self):
        return f"{self.user.username} - {self.window_key}: #{self.rank_after}"