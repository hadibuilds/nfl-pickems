from django.urls import path
#from .views import week_games
from . import views

urlpatterns = [
    #path('week/<int:week_number>/', week_games, name='week_games'),  # ✅ Ensure correct URL pattern
    path('api/games/', views.api_games, name='api_games'),
]
