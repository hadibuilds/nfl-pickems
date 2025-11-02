from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env.development if it exists (for local development)
env_file = BASE_DIR.parent / '.env.development'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Only set if not already set (environment takes precedence)
                if key not in os.environ:
                    os.environ[key] = value

# ─── Core toggles ────────────────────────────────────────────────────────────
DJANGO_ENV = os.getenv("DJANGO_ENV", "dev").lower()  # dev | prod
DEBUG = os.getenv("DEBUG", "True" if DJANGO_ENV == "dev" else "False").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")

USE_CLOUD_STORAGE = os.getenv("USE_CLOUD_STORAGE", "False").lower() == "true"

ROOT_URLCONF = "nfl_pickems.urls"
WSGI_APPLICATION = "nfl_pickems.wsgi.application"
ASGI_APPLICATION = "nfl_pickems.asgi.application"
AUTH_USER_MODEL = "accounts.CustomUser"

# ─── Hosts ───────────────────────────────────────────────────────────────────
def csv(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

if DEBUG:
    ALLOWED_HOSTS = csv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
else:
    default_hosts = "api.pickems.fun,nfl-pickems-alb-1597755509.us-east-2.elb.amazonaws.com,pickems.fun,www.pickems.fun"
    ALLOWED_HOSTS = csv("ALLOWED_HOSTS", default_hosts)

# ─── Installed apps ──────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "accounts",
    "games",
    "predictions",
    "analytics",
]

if USE_CLOUD_STORAGE:
    INSTALLED_APPS.append("storages")

# ─── Middleware ──────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ─── Templates ───────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600 if not DEBUG else 0,
            ssl_require=True,  # Always require SSL
        )
    }
    # Add additional database security options
    DATABASES["default"]["OPTIONS"] = DATABASES["default"].get("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].update({
        "sslmode": "require",
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    })
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Auth redirects ──────────────────────────────────────────────────────────
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "/")
LOGIN_URL = os.getenv("LOGIN_URL", "/admin/login/")

# ─── Static & Media ──────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

if USE_CLOUD_STORAGE:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-2")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_DEFAULT_ACL = "private"
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        # swap to S3StaticStorage if you want static also in S3
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
    }
    MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))
    MEDIA_URL = "/media/"

# ─── Email ───────────────────────────────────────────────────────────────────
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

# ─── CORS / CSRF ─────────────────────────────────────────────────────────────
local_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
prod_spa_origins = ["https://pickems.fun", "https://www.pickems.fun", "https://new-amplify.dnice32pxn4n2.amplifyapp.com"]

CORS_ALLOWED_ORIGINS = csv(
    "CORS_ALLOWED_ORIGINS",
    ",".join((local_origins if DEBUG else []) + (prod_spa_origins if not DEBUG else [])),
)
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https:\/\/[a-z0-9_-]+\.amplifyapp\.com$"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

default_csrf = (
    ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"]
    if DEBUG
    else []
) + [
    "https://pickems.fun",
    "https://www.pickems.fun",
    "https://api.pickems.fun",
    "https://nfl-pickems-alb-1597755509.us-east-2.elb.amazonaws.com",
]
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS", ",".join(default_csrf))

# ─── Security ────────────────────────────────────────────────────────────────
SESSION_COOKIE_SAMESITE = "Strict" if not DEBUG else "Lax"
CSRF_COOKIE_SAMESITE = "Strict" if not DEBUG else "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_DOMAIN = ".pickems.fun"
    CSRF_COOKIE_DOMAIN = ".pickems.fun"
    
    # Additional production security headers
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ─── i18n ────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── App-specific ───────────────────────────────────────────────────────────
INVITE_CODE = os.getenv("INVITE_CODE")
DJANGO_ADMIN_USERNAME = os.getenv("DJANGO_ADMIN_USERNAME")
DJANGO_ADMIN_PASSWORD = os.getenv("DJANGO_ADMIN_PASSWORD")
VITE_API_URL = os.getenv("VITE_API_URL", "https://api.pickems.fun")

# ─── Scoring Configuration ───────────────────────────────────────────────────
# Week when moneyline predictions increase from 1pt to 2pts
MONEYLINE_POINTS_INCREASE_WEEK = int(os.getenv("MONEYLINE_POINTS_INCREASE_WEEK", "9"))

# Validate required environment variables (skip during collectstatic)
import sys
RUNNING_COLLECTSTATIC = 'collectstatic' in sys.argv

if not RUNNING_COLLECTSTATIC:
    if not INVITE_CODE:
        raise ValueError("INVITE_CODE environment variable is required")
    if not DJANGO_ADMIN_USERNAME:
        raise ValueError("DJANGO_ADMIN_USERNAME environment variable is required")
    if not DJANGO_ADMIN_PASSWORD:
        raise ValueError("DJANGO_ADMIN_PASSWORD environment variable is required")

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose" if not DEBUG else "simple",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO" if not DEBUG else "DEBUG"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO" if not DEBUG else "DEBUG", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "accounts": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "analytics": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "accounts.media_views": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
