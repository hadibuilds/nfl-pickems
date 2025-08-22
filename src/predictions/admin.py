# predictions/admin.py
from django.contrib import admin
from .models import (
    Prediction, PropBet, PropBetPrediction, 
    WeeklySnapshot, RankHistory, UserStreak, 
    LeaderboardSnapshot, SeasonStats
)

# ✅ Admin for game predictions (money-line picks)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'predicted_winner', 'is_correct')
    list_filter = ('is_correct', 'game__week')
    search_fields = ('user__username', 'game__home_team', 'game__away_team', 'predicted_winner')
    ordering = ('-game__week', '-game__start_time')

# ✅ Admin for prop bets
class PropBetAdmin(admin.ModelAdmin):
    list_display = ('get_week', 'game', 'category', 'question', 'correct_answer')
    ordering = ('game__week',)
    search_fields = ('question',)
    list_filter = ('category', 'game__week')

    def get_week(self, obj):
        return obj.game.week
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'game__week'

# ✅ Admin for user prop bet predictions
class PropBetPredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'prop_bet', 'answer', 'is_correct')
    list_filter = ('is_correct', 'prop_bet__category', 'prop_bet__game__week')
    search_fields = ('user__username', 'prop_bet__question', 'answer')
    ordering = ('-prop_bet__game__week',)

# 📊 Admin for weekly snapshots
class WeeklySnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'week', 'rank', 'total_points', 'weekly_points', 
        'overall_accuracy', 'created_at'
    )
    list_filter = ('week', 'rank')
    search_fields = ('user__username',)
    ordering = ('week', 'rank')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'week', 'rank', 'total_users', 'points_from_leader')
        }),
        ('Weekly Stats', {
            'fields': (
                'weekly_points', 'weekly_game_correct', 'weekly_game_total',
                'weekly_prop_correct', 'weekly_prop_total', 'weekly_accuracy'
            )
        }),
        ('Cumulative Stats', {
            'fields': (
                'total_points', 'total_game_correct', 'total_game_total',
                'total_prop_correct', 'total_prop_total'
            )
        }),
        ('Accuracies', {
            'fields': ('overall_accuracy', 'moneyline_accuracy', 'prop_accuracy')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

# 📈 Admin for rank history
class RankHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'week', 'rank', 'previous_rank', 'rank_change_display', 
        'total_points', 'trend_direction'
    )
    list_filter = ('week', 'rank_change')
    search_fields = ('user__username',)
    ordering = ('week', 'rank')
    readonly_fields = ('created_at', 'trend_direction', 'rank_change_display')
    
    def rank_change_display(self, obj):
        return obj.rank_change_display
    rank_change_display.short_description = 'Rank Change'
    
    def trend_direction(self, obj):
        return obj.trend_direction
    trend_direction.short_description = 'Trend'

# 🔥 Admin for user streaks
class UserStreakAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'current_streak', 'streak_type', 'longest_win_streak', 
        'longest_loss_streak', 'last_updated'
    )
    list_filter = ('streak_type', 'current_streak')
    search_fields = ('user__username',)
    ordering = ('-current_streak',)
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        ('Current Streak', {
            'fields': ('user', 'current_streak', 'streak_type')
        }),
        ('Record Streaks', {
            'fields': ('longest_win_streak', 'longest_loss_streak')
        }),
        ('Metadata', {
            'fields': ('last_updated',)
        }),
    )

# 🏆 Admin for leaderboard snapshots
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ('week', 'get_leader', 'get_total_users', 'created_at')
    list_filter = ('week',)
    ordering = ('-week',)
    readonly_fields = ('created_at', 'get_leader', 'get_total_users', 'formatted_snapshot')
    
    def get_leader(self, obj):
        """Show who was leading that week"""
        if obj.snapshot_data:
            leader = next((user for user in obj.snapshot_data if user.get('rank') == 1), None)
            return f"{leader['username']} ({leader['points']} pts)" if leader else 'N/A'
        return 'N/A'
    get_leader.short_description = 'Week Leader'
    
    def get_total_users(self, obj):
        """Show total users that week"""
        return len(obj.snapshot_data) if obj.snapshot_data else 0
    get_total_users.short_description = 'Total Users'
    
    def formatted_snapshot(self, obj):
        """Pretty print the JSON data"""
        if obj.snapshot_data:
            formatted = ""
            for user in obj.snapshot_data[:5]:  # Show top 5
                formatted += f"#{user.get('rank', '?')} {user.get('username', 'Unknown')} - {user.get('points', 0)} pts\n"
            if len(obj.snapshot_data) > 5:
                formatted += f"... and {len(obj.snapshot_data) - 5} more users"
            return formatted
        return 'No data'
    formatted_snapshot.short_description = 'Top 5 Leaderboard'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('week', 'get_leader', 'get_total_users', 'created_at')
        }),
        ('Leaderboard Data', {
            'fields': ('formatted_snapshot',),
            'description': 'Top 5 users from this week\'s leaderboard'
        }),
    )

# 🌟 Admin for season stats
class SeasonStatsAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'best_week_points', 'best_week_number', 'highest_rank',
        'weeks_in_top_3', 'weeks_as_leader', 'trending_direction'
    )
    list_filter = ('trending_direction', 'weeks_as_leader', 'weeks_in_top_3')
    search_fields = ('user__username', 'favorite_team_picked')
    ordering = ('-weeks_as_leader', '-weeks_in_top_3', 'highest_rank')
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Best Performances', {
            'fields': (
                'best_week_points', 'best_week_number', 
                'highest_rank', 'highest_rank_week'
            )
        }),
        ('Consistency Metrics', {
            'fields': (
                'weeks_in_top_3', 'weeks_in_top_5', 'weeks_as_leader'
            )
        }),
        ('Prediction Patterns', {
            'fields': (
                'favorite_team_picked', 'favorite_team_pick_count',
                'most_successful_category'
            )
        }),
        ('Trends', {
            'fields': ('trending_direction',)
        }),
        ('Metadata', {
            'fields': ('last_updated',)
        }),
    )

# Register all models
admin.site.register(Prediction, PredictionAdmin)
admin.site.register(PropBet, PropBetAdmin)
admin.site.register(PropBetPrediction, PropBetPredictionAdmin)

# Register new historical models
admin.site.register(WeeklySnapshot, WeeklySnapshotAdmin)
admin.site.register(RankHistory, RankHistoryAdmin)
admin.site.register(UserStreak, UserStreakAdmin)
admin.site.register(LeaderboardSnapshot, LeaderboardSnapshotAdmin)
admin.site.register(SeasonStats, SeasonStatsAdmin)