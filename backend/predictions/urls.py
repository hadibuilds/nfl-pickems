# predictions/urls.py — CRUD OPERATIONS ONLY
# Clean separation: predictions = raw data input/output, analytics = data analysis

from django.urls import path
from .views import (
    # Prediction management (CRUD)
    make_prediction,
    make_prop_bet,
    save_user_selection,
    get_user_predictions,
    get_game_results,
)

urlpatterns = [
    # =============================================================================
    # PREDICTION MANAGEMENT (CREATE, UPDATE, DELETE)
    # =============================================================================
    path('api/make-prediction/<int:game_id>/', make_prediction, name='make-prediction'),
    path('api/make-prop-bet/<int:prop_bet_id>/', make_prop_bet, name='make-prop-bet'),
    path('api/save-selection/', save_user_selection, name='save-selection'),
    
    # =============================================================================
    # DATA READS (READ OPERATIONS)  
    # =============================================================================
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
    path('api/game-results/', get_game_results, name='game-results'),
]