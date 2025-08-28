# predictions/urls.py (unchanged routes; views were slimmed)

from django.urls import path
from .views import (
    save_selection,
    save_selections,
    get_recent_games_only,
    window_completeness,
    get_user_predictions,
)

urlpatterns = [
    # Core predictions
    path("api/save-selection/", save_selection, name="save-selection"),
    path("api/save-selections/", save_selections, name="save-selections"),  # bulk-save endpoint
    path("api/get-recent-games-only/", get_recent_games_only, name="get-recent-games-only"),
    path("api/window-completeness/", window_completeness, name="window-completeness"),
    path("api/get-user-predictions/", get_user_predictions, name="get-user-predictions"),
]
