from django.urls import path
from .views import get_game_results, save_user_selection, get_user_predictions, get_standings, user_accuracy

urlpatterns = [
    path('api/save-selection/', save_user_selection, name='save-selection'),
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
    path('api/standings/', get_standings, name='api-standings'),
    path('api/game-results/', get_game_results, name='game-results'),
    path('api/user-accuracy/', user_accuracy, name='user-accuracy'),
]
