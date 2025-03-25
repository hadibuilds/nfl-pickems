from django.urls import path
from .views import make_prediction, make_prop_bet, standings_view

urlpatterns = [
    path('predict/<int:game_id>/', make_prediction, name='make_prediction'),
    path('propbet/<int:prop_bet_id>/', make_prop_bet, name='make_prop_bet'),  # ✅ New endpoint for prop bets
    path('standings/', standings_view, name='standings'),
]
