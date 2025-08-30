from django.urls import path
from analytics.views import live_window, leaderboard, user_timeline, stats_summary, accuracy_summary, recent_results, pending_picks, truth_counter

urlpatterns = [
    path("api/live-window/", live_window, name="live_window"),
    path("api/leaderboard/", leaderboard, name="leaderboard"),
    
    path("api/user-timeline/", user_timeline, name="user_timeline"),
    path("api/stats-summary/", stats_summary, name="stats_summary"),
    path("api/accuracy-summary/", accuracy_summary, name="accuracy_summary"),
    path("api/recent-results/", recent_results, name="recent_results"),
    path("api/pending-picks/", pending_picks, name="pending_picks"),
    path("api/truth-counter/", truth_counter, name="truth_counter"),
]
