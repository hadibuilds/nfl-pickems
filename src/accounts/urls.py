from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    whoami,
    LoginAPIView,
    RegisterView,
    logout_view,
    get_csrf_token,
    CustomPasswordResetView,  # Add this import
)

urlpatterns = [
    path('api/csrf/', get_csrf_token, name='csrf-token'),
    path('api/whoami/', whoami, name='whoami'),
    path('api/login/', LoginAPIView.as_view(), name='api-login'),
    path('api/register/', RegisterView.as_view(), name='api-register'),
    path('api/logout/', logout_view, name='logout'),

    # Use the custom view instead of the default one
    path('api/password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),

    path('api/password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/reset_link_sent.html',
    ), name='password_reset_done'),

    path('api/password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/reset_password_form.html',
    ), name='password_reset_confirm'),

    path('api/password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_success.html',
    ), name='password_reset_complete'),
]