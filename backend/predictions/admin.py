# predictions/admin.py
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.conf import settings

from .models import (
    Prediction, PropBet, PropBetPrediction,
    WeeklySnapshot, UserStatHistory,
    LeaderboardSnapshot, SeasonStats
)

# Try to import Game so we can show it under "Non-User Data"
try:
    from games.models import Game
    HAS_GAME = True
except Exception:
    HAS_GAME = False


# ===========================
#   ModelAdmin definitions
# ===========================

class PredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "predicted_winner", "is_correct")
    list_filter = ("is_correct", "game__week")
    search_fields = ("user__username", "game__home_team", "game__away_team", "predicted_winner")
    ordering = ("-game__week", "-game__start_time")


class PropBetAdmin(admin.ModelAdmin):
    list_display = ("get_week", "game", "category", "question", "correct_answer")
    list_filter = ("category", "game__week")
    search_fields = ("question",)
    ordering = ("game__week",)

    def get_week(self, obj):
        return obj.game.week
    get_week.short_description = "Week"
    get_week.admin_order_field = "game__week"


class PropBetPredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "prop_bet", "answer", "is_correct")
    list_filter = ("is_correct", "prop_bet__category", "prop_bet__game__week")
    search_fields = ("user__username", "prop_bet__question", "answer")
    ordering = ("-prop_bet__game__week",)


# Remove UserStreak admin and update SeasonStats admin
class SeasonStatsAdmin(admin.ModelAdmin):
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


class WeeklySnapshotAdmin(admin.ModelAdmin):
    list_display = ("user", "week", "rank", "total_points", "weekly_points", "overall_accuracy", "created_at")
    list_filter = ("week", "rank")
    search_fields = ("user__username",)
    ordering = ("week", "rank")
    readonly_fields = ("created_at",)


@admin.register(UserStatHistory)
class UserStatHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'week', 'rank', 'rank_change_display', 'total_points', 
        'week_points', 'week_accuracy', 'season_accuracy', 'trend_direction', 'created_at'
    ]
    list_filter = ['week', 'rank', 'rank_change']  # Use actual field, not property
    search_fields = ['user__username']
    ordering = ['-week', 'rank']
    
    # Group fields logically in the admin form
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
    
    # Make all fields read-only (since these are snapshots)
    readonly_fields = [
        'user', 'week', 'rank', 'previous_rank', 'rank_change', 'total_points',
        'week_points', 'week_moneyline_correct', 'week_moneyline_total',
        'week_prop_correct', 'week_prop_total', 'season_moneyline_correct',
        'season_moneyline_total', 'season_prop_correct', 'season_prop_total',
        'week_accuracy', 'season_accuracy', 'moneyline_accuracy', 'prop_accuracy',
        'created_at'
    ]
    
    # Prevent adding/editing through admin (only allow viewing)
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only snapshots
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete snapshots
    
    # Custom display methods
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
        
        # Format the JSON data nicely for display
        lines = []
        for i, entry in enumerate(obj.snapshot_data[:10]):  # Show top 10
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


# ===========================
#   Register remaining models
# ===========================

# Remove UserStreak registration and update model groupings

admin.site.register(Prediction, PredictionAdmin)
admin.site.register(PropBet, PropBetAdmin)
admin.site.register(PropBetPrediction, PropBetPredictionAdmin)
admin.site.register(SeasonStats, SeasonStatsAdmin)  # Keep but moved to User Data section

# Only register legacy snapshots if needed for backward compatibility
if getattr(settings, "LEGACY_SNAPSHOTS_ENABLED", False):
    admin.site.register(WeeklySnapshot, WeeklySnapshotAdmin)

# ============================================
#   Updated admin grouping - cleaner sections
# ============================================

USER_MODEL_NAMES = {"User"}
GROUP_MODEL_NAMES = {"Group"}
NONUSER_MODEL_NAMES = {"PropBet"} | ({"Game"} if HAS_GAME else set())

# SeasonStats is live data that updates throughout season, so it belongs in User Data
USERDATA_MODEL_NAMES = {"Prediction", "PropBetPrediction", "SeasonStats"}

# Only TRUE immutable snapshot models
SNAPSHOT_MODEL_NAMES = {"UserStatHistory", "LeaderboardSnapshot"}

# Add legacy snapshots only if enabled
if getattr(settings, "LEGACY_SNAPSHOTS_ENABLED", False):
    SNAPSHOT_MODEL_NAMES.add("WeeklySnapshot")

# Save the *original class method* so we can call it safely
_ORIG_CLASS_GET_APP_LIST = admin.AdminSite.get_app_list

def _custom_get_app_list(adminsite, request):
    """
    Build a custom app list with five ordered pseudo sections first:
      Users → Groups → Non-User Data → User Data → Snapshot Data
    Then append all remaining apps/models as Django would normally display.
    """
    # Call Django's original class method (not super()), then reshape
    apps = list(_ORIG_CLASS_GET_APP_LIST(adminsite, request))

    # Flatten all models (keep original dict structure for each model row)
    flat = []
    for app in apps:
        for m in app["models"]:
            flat.append({
                "app_label": app["app_label"],
                "app_name": app["name"],
                "app_url": app["app_url"],
                "model": m,
            })

    def pluck(names, pool):
        picked, rest = [], []
        ns = set(names)
        for row in pool:
            if row["model"]["object_name"] in ns:
                picked.append(row)
            else:
                rest.append(row)
        return picked, rest

    # Build the five sections in exact order
    users_rows, rest = pluck(USER_MODEL_NAMES, flat)
    groups_rows, rest = pluck(GROUP_MODEL_NAMES, rest)
    nonuser_rows, rest = pluck(NONUSER_MODEL_NAMES, rest)
    userdata_rows, rest = pluck(USERDATA_MODEL_NAMES, rest)
    snapshot_rows, rest = pluck(SNAPSHOT_MODEL_NAMES, rest)

    def make_app(name, rows, label):
        return {
            "name": name,
            "app_label": label,
            "app_url": "",
            "has_module_perms": True,
            "models": sorted([r["model"] for r in rows], key=lambda m: m["name"].lower()),
        }

    pseudo = []
    if users_rows:    pseudo.append(make_app("Users", users_rows, "z_users"))
    if groups_rows:   pseudo.append(make_app("Groups", groups_rows, "z_groups"))
    if nonuser_rows:  pseudo.append(make_app("Non-User Data", nonuser_rows, "z_nonuser"))
    if userdata_rows: pseudo.append(make_app("User Data", userdata_rows, "z_user"))
    if snapshot_rows: pseudo.append(make_app("Snapshot Data", snapshot_rows, "z_snapshot"))

    # Rebuild remaining real apps (auth, admin, etc.)
    by_app = {}
    for row in rest:
        key = (row["app_label"], row["app_name"], row["app_url"])
        by_app.setdefault(key, []).append(row["model"])

    remaining = []
    for (app_label, app_name, app_url), models in by_app.items():
        remaining.append({
            "name": app_name,
            "app_label": app_label,
            "app_url": app_url,
            "has_module_perms": True,
            "models": sorted(models, key=lambda m: m["name"].lower()),
        })

    # Our five pseudo sections FIRST, then the rest alphabetically by app name
    return pseudo + sorted(remaining, key=lambda a: a["name"].lower())

# Patch the AdminSite *class* so all admin sites use this ordering
admin.AdminSite.get_app_list = _custom_get_app_list

# Optional: header branding
admin.site.site_header = "NFL Pickems Admin"
admin.site.site_title = "NFL Pickems Admin"
admin.site.index_title = "Dashboard & Statistics Management"