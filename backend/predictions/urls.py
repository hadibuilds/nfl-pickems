# predictions/urls.py (unchanged routes; views were slimmed)
from django.urls import path
from .views import (
    # Existing endpoints
    get_game_results,
    save_user_selection,
    get_user_predictions,
    get_standings,
    user_accuracy,

    # Dashboard endpoints
    get_dashboard_data,
    get_dashboard_data_realtime,
    get_dashboard_data_snapshot,

    # Granular dashboard endpoints
    get_user_stats_only,
    get_user_accuracy_only,
    get_leaderboard_only,
    get_recent_games_only,
    get_user_insights_only,
    get_current_week_only,

    # Admin
    trigger_weekly_snapshot,

    # Snapshot-powered reads (season totals + trends)
    user_season_stats_fast_view,
    user_weekly_trends_fast_view,
    season_leaderboard_fast_view,
    season_leaderboard_dynamic_trend_view,
)

urlpatterns = [
    # Core predictions
    path('api/save-selection/', save_user_selection, name='save-selection'),
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
    path('api/standings/', get_standings, name='api-standings'),
    path('api/game-results/', get_game_results, name='game-results'),
    path('api/user-accuracy/', user_accuracy, name='user-accuracy'),

    # Dashboard (full + realtime/snapshot variants)
    path('api/dashboard/', get_dashboard_data, name='dashboard-data'),
    path('api/dashboard/realtime/', get_dashboard_data_realtime, name='dashboard-data-realtime'),
    path('api/dashboard/snapshot/', get_dashboard_data_snapshot, name='dashboard-data-snapshot'),

    # Granular dashboard
    path('api/dashboard/stats/', get_user_stats_only, name='dashboard-stats-only'),
    path('api/dashboard/accuracy/', get_user_accuracy_only, name='dashboard-accuracy-only'),
    path('api/dashboard/leaderboard/', get_leaderboard_only, name='dashboard-leaderboard-only'),
    path('api/dashboard/recent/', get_recent_games_only, name='dashboard-recent-only'),
    path('api/dashboard/insights/', get_user_insights_only, name='dashboard-insights-only'),

    # Utility
    path('api/current-week/', get_current_week_only, name='current-week'),

    # Admin
    path('api/admin/trigger-snapshot/', trigger_weekly_snapshot, name='trigger-weekly-snapshot'),

    # Snapshot-powered reads (season totals + trends)
    path('api/user-season-stats-fast/', user_season_stats_fast_view, name='user-season-stats-fast'),
    path('api/user-trends-fast/', user_weekly_trends_fast_view, name='user-trends-fast'),
    path('api/season-leaderboard-fast/', season_leaderboard_fast_view, name='season-leaderboard-fast'),
    path('api/season-leaderboard-dynamic/', season_leaderboard_dynamic_trend_view, name='season-leaderboard-dynamic'),
]
