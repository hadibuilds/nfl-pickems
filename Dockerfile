# syntax=docker/dockerfile:1

############################
# 1) Build stage (wheels)
############################
FROM python:3.11-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OS deps only needed to build wheels (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Adjust if requirements are elsewhere
COPY requirements*.txt ./ 
RUN pip install --upgrade pip && pip wheel --wheel-dir=/wheels -r requirements.txt

############################
# 2) Runtime stage
############################
FROM python:3.11-slim AS runtime

# Minimal runtime libs (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENV=prod \
    DJANGO_SETTINGS_MODULE=nfl_pickems.settings \
    STATIC_ROOT=/app/backend/staticfiles \
    PYTHONPATH=/app/backend

# Create an unprivileged user
RUN useradd -m appuser
WORKDIR /app

# Copy wheels and install
COPY --from=build /wheels /wheels
COPY requirements*.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

# Copy project code (preserve backend structure)
COPY backend/ /app/backend/
WORKDIR /app/backend

# Collect static at build time (safe: no DB needed)
RUN python manage.py collectstatic --noinput

# Copy entrypoint
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ensure non-root user owns the app dir
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Start: run migrations, create superuser, seed data, then gunicorn (entrypoint.sh handles it)
CMD ["/entrypoint.sh"]