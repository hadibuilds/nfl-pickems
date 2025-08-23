# predictions/urls.py - Updated with granular dashboard endpoints
from django.urls import path
from .views import (
    get_game_results, 
    save_user_selection, 
    get_user_predictions, 
    get_standings, 
    user_accuracy, 
    get_dashboard_data,
    get_dashboard_data_realtime,
    get_dashboard_data_snapshot,
    trigger_weekly_snapshot,
    # New granular endpoints
    get_user_stats_only,
    get_user_accuracy_only,
    get_leaderboard_only,
    get_recent_games_only,
    get_user_insights_only,
)

urlpatterns = [
    # Existing endpoints
    path('api/save-selection/', save_user_selection, name='save-selection'),
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
    path('api/standings/', get_standings, name='api-standings'),
    path('api/game-results/', get_game_results, name='game-results'),
    path('api/user-accuracy/', user_accuracy, name='user-accuracy'),
    
    # Dashboard endpoints
    path('api/dashboard/', get_dashboard_data, name='dashboard-data'),  # Full dashboard (supports ?sections= parameter)
    path('api/dashboard/realtime/', get_dashboard_data_realtime, name='dashboard-data-realtime'),
    path('api/dashboard/snapshot/', get_dashboard_data_snapshot, name='dashboard-data-snapshot'),
    
    # NEW: Granular dashboard endpoints (FAST!)
    path('api/dashboard/stats/', get_user_stats_only, name='dashboard-stats-only'),           # Fastest: rank, points, pending picks
    path('api/dashboard/accuracy/', get_user_accuracy_only, name='dashboard-accuracy-only'), # Fast: accuracy percentages  
    path('api/dashboard/leaderboard/', get_leaderboard_only, name='dashboard-leaderboard-only'), # Slowest: but isolated
    path('api/dashboard/recent/', get_recent_games_only, name='dashboard-recent-only'),       # Fast: recent games
    path('api/dashboard/insights/', get_user_insights_only, name='dashboard-insights-only'), # Fast: streaks & insights
    
    # Admin endpoint for snapshots
    path('api/admin/trigger-snapshot/', trigger_weekly_snapshot, name='trigger-weekly-snapshot'),
]