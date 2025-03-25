from django.urls import path
from .views import week_games

urlpatterns = [
    path('week/<int:week_number>/', week_games, name='week_games'),  # ✅ Ensure correct URL pattern
]
