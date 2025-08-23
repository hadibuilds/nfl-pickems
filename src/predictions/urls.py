# predictions/urls.py - Updated with new dashboard endpoints
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
    trigger_weekly_snapshot
)

urlpatterns = [
    # Existing endpoints
    path('api/save-selection/', save_user_selection, name='save-selection'),
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
    path('api/standings/', get_standings, name='api-standings'),
    path('api/game-results/', get_game_results, name='game-results'),
    path('api/user-accuracy/', user_accuracy, name='user-accuracy'),
    
    # Dashboard endpoints (NEW)
    path('api/dashboard/', get_dashboard_data, name='dashboard-data'),  # Configurable (realtime by default)
    path('api/dashboard/realtime/', get_dashboard_data_realtime, name='dashboard-data-realtime'),  # Always realtime
    path('api/dashboard/snapshot/', get_dashboard_data_snapshot, name='dashboard-data-snapshot'),  # Always snapshot-based
    
    # Admin endpoint for snapshots
    path('api/admin/trigger-snapshot/', trigger_weekly_snapshot, name='trigger-weekly-snapshot'),
]