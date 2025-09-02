#!/usr/bin/env bash
set -euo pipefail

# Wait for DB by retrying migrate (safe & idempotent)
until python manage.py migrate --noinput; do
  echo "Waiting for database (migrate failed, retrying in 2s)..."
  sleep 2
done

echo "Migrations completed successfully"

# Start Gunicorn
exec gunicorn nfl_pickems.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --threads 2 \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
