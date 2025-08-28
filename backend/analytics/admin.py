# analytics/admin.py - CRITICAL FIX: Admin field mismatches

from django.contrib import admin
from analytics.models import UserSeasonInsights, UserStatHistory, LeaderboardSnapshot, Top3Snapshot

@admin.register(UserSeasonInsights)
class UserSeasonInsightsAdmin(admin.ModelAdmin):
    list_display = (
        "user", "best_week_points", "best_rank", "weeks_at_rank_1", 
        "weeks_in_top_3", "consecutive_weeks_at_1", "biggest_rank_climb", "trending_direction"
    )
    list_filter = ("trending_direction", "weeks_at_rank_1", "weeks_in_top_3", "best_category")
    search_fields = ("user__username", "favorite_team_picked")
    ordering = ("-weeks_at_rank_1", "-weeks_in_top_3", "best_rank")
    readonly_fields = ("last_updated",)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Performance Records', {
            'fields': ('best_week_points', 'best_week_number', 'best_rank', 'best_rank_week', 'worst_rank'),
            'description': 'Peak performance achievements'
        }),
        ('Rank Consistency', {
            'fields': (
                'weeks_at_rank_1', 'weeks_in_top_3', 'weeks_in_top_5',
                'consecutive_weeks_at_1', 'max_consecutive_weeks_at_1'
            ),
            'description': 'Rank-based achievements and consistency metrics'
        }),
        ('Movement Records', {
            'fields': ('biggest_rank_climb', 'biggest_rank_fall'),
            'description': 'Single-week rank movement records'
        }),
        ('Category Performance', {
            'fields': ('favorite_team_picked', 'favorite_team_pick_count', 'best_category'),
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ('trending_direction', 'last_updated'),
        }),
    )

@admin.register(UserStatHistory)
class UserStatHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'week', 'rank', 'rank_change_display', 'total_points', 
        'week_points', 'week_accuracy', 'season_accuracy', 'trend_direction', 'created_at'
    ]
    # CRITICAL FIX: Use actual field names, not properties
    list_filter = ['week', 'rank']  # Removed 'rank_change' since it's calculated
    search_fields = ['user__username']
    ordering = ['-week', 'rank']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'week', 'created_at')
        }),
        ('Ranking Information', {
            'fields': ('rank', 'previous_rank', 'rank_change', 'total_points'),
            'description': 'Ranking position and changes from previous week'
        }),
        ('Weekly Performance', {
            'fields': (
                'week_points', 'week_accuracy',
                ('week_moneyline_correct', 'week_moneyline_total'),
                ('week_prop_correct', 'week_prop_total')
            ),
            'classes': ['collapse'],
            'description': 'Performance statistics for this specific week'
        }),
        ('Season Cumulative Stats', {
            'fields': (
                'season_accuracy', 
                ('moneyline_accuracy', 'prop_accuracy'),
                ('season_moneyline_correct', 'season_moneyline_total'),
                ('season_prop_correct', 'season_prop_total')
            ),
            'classes': ['collapse'],
            'description': 'Cumulative performance through this week'
        }),
    )
    
    readonly_fields = [
        'user', 'week', 'rank', 'previous_rank', 'rank_change', 'total_points',
        'week_points', 'week_moneyline_correct', 'week_moneyline_total',
        'week_prop_correct', 'week_prop_total', 'season_moneyline_correct',
        'season_moneyline_total', 'season_prop_correct', 'season_prop_total',
        'week_accuracy', 'season_accuracy', 'moneyline_accuracy', 'prop_accuracy',
        'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    # CRITICAL FIX: These display methods work correctly
    def rank_change_display(self, obj):
        return obj.rank_change_display
    rank_change_display.short_description = 'Rank Change'
    rank_change_display.admin_order_field = 'rank_change'
    
    def trend_direction(self, obj):
        return obj.trend_direction.title()
    trend_direction.short_description = 'Trend'
    trend_direction.admin_order_field = 'rank_change'

@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ['week', 'entry_count', 'top_player', 'created_at']
    list_filter = ['week']
    ordering = ['-week']
    
    readonly_fields = ['week', 'snapshot_data', 'created_at', 'formatted_data']
    
    fieldsets = (
        ('Snapshot Info', {
            'fields': ('week', 'entry_count', 'created_at')
        }),
        ('Leaderboard Data', {
            'fields': ('formatted_data',),
            'classes': ['collapse']
        }),
        ('Raw Data', {
            'fields': ('snapshot_data',),
            'classes': ['collapse']
        }),
    )
    
    def entry_count(self, obj):
        return len(obj.snapshot_data) if obj.snapshot_data else 0
    entry_count.short_description = 'Total Entries'
    
    def top_player(self, obj):
        if obj.snapshot_data and len(obj.snapshot_data) > 0:
            leader = obj.snapshot_data[0]
            return f"{leader.get('username', 'Unknown')} ({leader.get('points', 0)} pts)"
        return "No data"
    top_player.short_description = 'Week Leader'
    
    def formatted_data(self, obj):
        if not obj.snapshot_data:
            return "No leaderboard data"
        
        lines = []
        for i, entry in enumerate(obj.snapshot_data[:10]):
            rank = entry.get('rank', i + 1)
            username = entry.get('username', 'Unknown')
            points = entry.get('points', 0)
            lines.append(f"#{rank}: {username} - {points} points")
        
        if len(obj.snapshot_data) > 10:
            lines.append(f"... and {len(obj.snapshot_data) - 10} more entries")
        
        return '\n'.join(lines)
    formatted_data.short_description = 'Leaderboard Preview'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Top3Snapshot)
class Top3SnapshotAdmin(admin.ModelAdmin):
    list_display = ['window_key', 'version', 'correction_applied', 'created_at']
    list_filter = ['correction_applied', 'window_key']
    ordering = ['-created_at']
    readonly_fields = ['window_key', 'version', 'payload', 'created_at', 'correction_event']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser