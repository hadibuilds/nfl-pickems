from django.urls import path
from analytics.views import (
    live_window, leaderboard, user_timeline, stats_summary, accuracy_summary, recent_results, pending_picks, truth_counter,
    # Migrated analysis functions from predictions app (with optimized logic)
    get_standings_migrated, get_current_week_migrated, user_accuracy_migrated,
    get_user_stats_migrated, get_leaderboard_migrated, get_dashboard_data_migrated
)

urlpatterns = [
    # Original analytics endpoints (keep)
    path("api/live-window/", live_window, name="live_window"),
    path("api/leaderboard/", leaderboard, name="leaderboard"),
    path("api/user-timeline/", user_timeline, name="user_timeline"),
    path("api/stats-summary/", stats_summary, name="stats_summary"),
    path("api/accuracy-summary/", accuracy_summary, name="accuracy_summary"),
    path("api/recent-results/", recent_results, name="recent_results"),
    path("api/pending-picks/", pending_picks, name="pending_picks"),
    path("api/truth-counter/", truth_counter, name="truth_counter"),
    
    # MIGRATED from predictions app (analysis functions with optimized logic)
    path("api/standings/", get_standings_migrated, name="standings"),
    path("api/current-week/", get_current_week_migrated, name="current_week"),
    path("api/user-accuracy/", user_accuracy_migrated, name="user_accuracy"),
    path("api/user-stats/", get_user_stats_migrated, name="user_stats"),
    path("api/leaderboard-migrated/", get_leaderboard_migrated, name="leaderboard_migrated"),
    path("api/dashboard/", get_dashboard_data_migrated, name="dashboard"),
]
