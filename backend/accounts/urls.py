from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    whoami,
    LoginAPIView,
    RegisterView,
    logout_view,
    get_csrf_token,
    CustomPasswordResetView,
    password_reset_api,
    password_reset_validate_api,
    password_reset_confirm_api,
    password_reset_email_redirect,
)

urlpatterns = [
    path('api/csrf/', get_csrf_token, name='csrf-token'),
    path('api/whoami/', whoami, name='whoami'),
    path('api/login/', LoginAPIView.as_view(), name='api-login'),
    path('api/register/', RegisterView.as_view(), name='api-register'),
    path('api/logout/', logout_view, name='logout'),

    # NEW: API endpoints for React frontend
    path('api/password-reset/', password_reset_api, name='password_reset_api'),
    path('api/password-reset-validate/', password_reset_validate_api, name='password_reset_validate_api'),
    path('api/password-reset-confirm/', password_reset_confirm_api, name='password_reset_confirm_api'),

    # EMAIL REDIRECT: These URLs are used in emails to redirect to React frontend
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),  
    path('password-reset-confirm/<uidb64>/<token>/', password_reset_email_redirect, name='password_reset_confirm'),
]