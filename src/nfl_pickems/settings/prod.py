from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    'nfl-pickems-t60y.onrender.com',  
    'nfl-pickems.onrender.com',       
    '.onrender.com'                   
]

CORS_ALLOWED_ORIGINS = [
    "https://nfl-pickems-t60y.onrender.com",  
    "https://nfl-pickems.onrender.com",
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://nfl-pickems-t60y.onrender.com",  
    "https://nfl-pickems.onrender.com",
]   

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

# For production email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # or your email provider
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')  # your email
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')  # app password
