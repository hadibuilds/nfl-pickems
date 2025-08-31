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

# Media files for production
# Option 1: Use cloud storage (recommended)
if config('USE_CLOUD_STORAGE', default=False, cast=bool):
    # AWS S3 settings (add these to your environment variables)
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'private'  # IMPORTANT: Keep avatars private
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    # Option 2: Local storage with nginx/apache serving
    MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'media'))
    # Media files will be served by your web server (nginx/apache) with authentication
