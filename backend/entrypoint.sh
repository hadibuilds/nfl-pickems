#!/usr/bin/env bash
set -euo pipefail

# Optional: allow DB to come up if you use RDS or a sidecar proxy
# sleep 2

# Make sure DB schema is up to date
python manage.py migrate --noinput

# You can re-run collectstatic at boot if you prefer (harmless):
# python manage.py collectstatic --noinput

# Start Gunicorn
# Tune workers/threads based on CPU/Memory in your Fargate task
exec gunicorn nfl_pickems.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --threads 2 \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
