from django.urls import path
from .views import save_user_selection, get_user_predictions, get_standings

urlpatterns = [
    path('api/save-selection/', save_user_selection, name='save-selection'),
    path('api/get-user-predictions/', get_user_predictions, name='get-user-predictions'),
    path('api/standings/', get_standings, name='api-standings'),
]
