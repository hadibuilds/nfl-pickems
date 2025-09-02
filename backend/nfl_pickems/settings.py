from pathlib import Path
import os

# ──────────────────────────────────────────────────────────────────────────────
# Core toggles
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

DJANGO_ENV = os.getenv("DJANGO_ENV", "dev").lower()  # dev | prod
DEBUG = os.getenv("DEBUG", "True" if DJANGO_ENV == "dev" else "False").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")

USE_CLOUD_STORAGE = os.getenv("USE_CLOUD_STORAGE", "False").lower() == "true"

ROOT_URLCONF = "nfl_pickems.urls"
WSGI_APPLICATION = "nfl_pickems.wsgi.application"
ASGI_APPLICATION = "nfl_pickems.asgi.application"

AUTH_USER_MODEL = "accounts.CustomUser"

# ──────────────────────────────────────────────────────────────────────────────
# Allowed hosts
# ──────────────────────────────────────────────────────────────────────────────
def csv(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

if DEBUG:
    ALLOWED_HOSTS = csv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
else:
    # Your prod hosts + ALB; extend via env if needed
    default_hosts = "api.pickems.fun,nfl-pickems-alb-1597755509.us-east-2.elb.amazonaws.com"
    ALLOWED_HOSTS = csv("ALLOWED_HOSTS", default_hosts)

# ──────────────────────────────────────────────────────────────────────────────
# Installed apps
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "corsheaders",          
    # Your apps
    "accounts",
    "games",
    "predictions",
    "analytics",
    # add others...
]

if USE_CLOUD_STORAGE:
    INSTALLED_APPS.append("storages")

# ──────────────────────────────────────────────────────────────────────────────
# Middleware (CORS must be at the top)
# ──────────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────
# Database: DATABASE_URL if present, else SQLite (local dev)
# ──────────────────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASES = {}
if DATABASE_URL:
    try:
        import dj_database_url  # make sure it's in requirements
    except ImportError:
        raise RuntimeError("dj_database_url is required when DATABASE_URL is set.")
    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600 if not DEBUG else 0,
        ssl_require=not DEBUG,
    )
else:
    # Safe default for local dev
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }

# ──────────────────────────────────────────────────────────────────────────────
# Authentication redirects
# ──────────────────────────────────────────────────────────────────────────────
# After successful login, send to site home by default (adjust as you like)
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "/")
# Where to send unauthenticated users to log in (admin is fine for staff-only apps)
LOGIN_URL = os.getenv("LOGIN_URL", "/admin/login/")

# ──────────────────────────────────────────────────────────────────────────────
# Static & Media
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# WhiteNoise compression/manifest
if USE_CLOUD_STORAGE:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")  # e.g. nfl-pickems-avatars-prod
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-2")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_DEFAULT_ACL = "private"
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    
    # Configure both static and media storage
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        }
    }
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
else:
    STORAGES = {
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
    }
    MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))
    MEDIA_URL = "/media/"

# ──────────────────────────────────────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────────────────────────────────────
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

# ──────────────────────────────────────────────────────────────────────────────
# CORS / CSRF
# ──────────────────────────────────────────────────────────────────────────────
# Local Vite defaults + optional env overrides
# CORS

local_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000",
]
prod_spa_origins = ["https://pickems.fun", "https://www.pickems.fun"]

def csv(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

CORS_ALLOWED_ORIGINS = csv(
    "CORS_ALLOWED_ORIGINS",
    ",".join((local_origins if DEBUG else []) + (prod_spa_origins if not DEBUG else [])),
)
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https:\/\/[a-z0-9-]+\.amplifyapp\.com$"]  # regex ok for CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# CSRF: must be explicit FQDNs, no wildcards
default_csrf = (
    ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"]
    if DEBUG else []
) + [
    "https://pickems.fun",
    "https://www.pickems.fun",
    "https://api.pickems.fun",
    "https://nfl-pickems-alb-1597755509.us-east-2.elb.amazonaws.com",
]
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS", ",".join(default_csrf))

# ──────────────────────────────────────────────────────────────────────────────
# Security & proxy headers (prod)
# ──────────────────────────────────────────────────────────────────────────────
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

if not DEBUG:
    # Trust ALB/ELB forwarded proto/host
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SECURE_SSL_REDIRECT = True
    # Share cookies across subdomains in prod
    SESSION_COOKIE_DOMAIN = ".pickems.fun"
    CSRF_COOKIE_DOMAIN = ".pickems.fun"

# ──────────────────────────────────────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────────────────────────────────────
# App-specific envs
# ──────────────────────────────────────────────────────────────────────────────
INVITE_CODE = os.getenv("INVITE_CODE", "fallbackcode")
DJANGO_ADMIN_USERNAME = os.getenv("DJANGO_ADMIN_USERNAME", "admin")
DJANGO_ADMIN_PASSWORD = os.getenv("DJANGO_ADMIN_PASSWORD", "admin123!")
VITE_API_URL = os.getenv("VITE_API_URL", "https://api.pickems.fun")

# ──────────────────────────────────────────────────────────────────────────────
# Logging (console → CloudWatch in ECS)
# ──────────────────────────────────────────────────────────────────────────────
""" LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO" if not DEBUG else "DEBUG"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO" if not DEBUG else "DEBUG", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "accounts.media_views": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
} """
