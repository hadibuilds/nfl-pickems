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

# Adjust the path if your requirements file lives elsewhere.
# If your requirements.txt is in repo root, change this COPY to `COPY requirements*.txt ./`
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
    # Let Django/Whitenoise find staticfiles inside the container
    STATIC_ROOT=/app/staticfiles

# Create an unprivileged user
RUN useradd -m appuser
WORKDIR /app

# Copy wheels and install
COPY --from=build /wheels /wheels
# Keep a copy of requirements for reproducibility/logging
COPY requirements*.txt ./ 
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

# Copy project code (only backend is needed to run Django)
COPY backend/ /app/

# Collect static at build time (safe: does not require DB)
# If you use S3 for static in prod (via env), this will still work locally thanks to your USE_CLOUD_STORAGE toggle.
RUN python manage.py collectstatic --noinput

# Copy entrypoint and use it as container entry
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Drop privileges
USER appuser

EXPOSE 8000

# Basic container healthcheck; add /healthz route (see below)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Start: run migrations, then gunicorn
CMD ["/entrypoint.sh"]
