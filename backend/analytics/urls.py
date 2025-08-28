# analytics/urls.py - ADD TO EXISTING FILE

from django.urls import path
from . import views

urlpatterns = [
    # =============================================================================
    # STANDINGS API ENDPOINTS - Rankings, leaderboards, user positioning  
    # =============================================================================
    
    # Windowed standings (NEW)
    path('api/windowed-standings/', views.get_windowed_standings, name='windowed-standings'),
    path('api/windowed-top3/', views.get_windowed_top3, name='windowed-top3'),
    path('api/windowed-summary/', views.get_windowed_summary, name='windowed-summary'),
    path('api/user-windowed-history/', views.get_user_windowed_history, name='user-windowed-history'),
    path('api/window-completeness/', views.window_completeness, name='window-completeness'),
    
    # Windowed admin (NEW)
    path('api/admin/refresh-windowed/', views.refresh_windowed_data, name='refresh-windowed-data'),
    path('api/admin/check-window/', views.check_window_status, name='check-window-status'),


    path("api/user-dashboard/", views.get_user_dashboard, name="get-user-dashboard"),
    path("api/compare-users/", views.compare_users, name="compare-users"),
    path("api/peek-window/", views.peek_window, name="peek-window"),

    # Legacy endpoints (soft-deprecated)
    path("api/home-top3/", views.home_top3_api, name="home-top3"),
    path("api/get-standings/", views.get_standings, name="get-standings"),
    path("api/get-standings-only/", views.get_leaderboard_only, name="get-standings-only"),

    # Fallback endpoints (NEW)
    path("api/fallback/season-performance/", views.realtime_fallback_combined, name="realtime-fallback-combined"),
    path("api/fallback/leaderboard/", views.realtime_leaderboard_only, name="realtime-fallback-leaderboard-only"),
    path("api/fallback/user-stats/", views.realtime_user_stats_only, name="realtime-fallback-user-stats-only"),
    
]