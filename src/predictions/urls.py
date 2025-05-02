from django.urls import path
from .views import make_prediction, make_prop_bet, save_user_selection, standings_view, get_user_predictions

urlpatterns = [
    path('predict/<int:game_id>/', make_prediction, name='make_prediction'),
    path('propbet/<int:prop_bet_id>/', make_prop_bet, name='make_prop_bet'),  # ✅ New endpoint for prop bets
    path('standings/', standings_view, name='standings'),
    path('api/save-selection/', save_user_selection, name='save-selection'),
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
]
