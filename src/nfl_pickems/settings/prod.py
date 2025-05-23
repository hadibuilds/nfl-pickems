from .base import *

DEBUG = False

ALLOWED_HOSTS = ['nfl-pickems.onrender.com']

CORS_ALLOWED_ORIGINS = [
    "https://nfl-pickems.onrender.com",
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://nfl-pickems.onrender.com",
]

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True
