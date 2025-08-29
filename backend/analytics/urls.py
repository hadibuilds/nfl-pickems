from django.urls import path
from analytics.views import live_window, leaderboard

urlpatterns = [
    path("api/live-window/", live_window),
    path("api/leaderboard/", leaderboard),
]
