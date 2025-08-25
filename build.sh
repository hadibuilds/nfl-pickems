#!/usr/bin/env bash
# Render-friendly, production-safe build script (LF endings)
# Usage in Render Build Command:  bash build.sh

set -Eeuo pipefail
IFS=$'\n\t'

log() { printf "\n\033[1;36m%s\033[0m\n" "🔧 $*"; }
ok()  { printf "\033[1;32m%s\033[0m\n" "✅ $*"; }
warn(){ printf "\033[1;33m%s\033[0m\n" "⚠️  $*"; }

trap 'warn "Build failed at line $LINENO"' ERR

ROOT_DIR="$(pwd)"
log "[RENDER] Starting build in $ROOT_DIR"

# -----------------------------------------------------------------------------
# Clean previous builds (idempotent)
# -----------------------------------------------------------------------------
log "Cleaning previous builds..."
rm -rf frontend/dist/ src/static/assets/ staticfiles/
rm -f src/templates/index.html

# -----------------------------------------------------------------------------
# Python deps
# -----------------------------------------------------------------------------
log "Installing Python packages..."
python -m pip install --upgrade pip setuptools wheel
pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Frontend build (Vite)
# -----------------------------------------------------------------------------
log "Installing & building frontend (Vite)..."
pushd frontend >/dev/null

# Ensure devDependencies are installed even in CI
export NPM_CONFIG_PRODUCTION=false

if [ -f package-lock.json ]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi

# Sanity: ensure vite is present in node_modules (handles edge cases)
if [ ! -d "node_modules/vite" ]; then
  warn "vite not found in node_modules — installing as devDependency"
  npm install -D vite @vitejs/plugin-react vite-plugin-static-copy --no-audit --no-fund
fi

# Build in production mode
NODE_ENV=production npx vite build --mode production

popd >/dev/null

# -----------------------------------------------------------------------------
# Copy assets into Django and patch index.html for {% static %}
# -----------------------------------------------------------------------------
log "Copying built assets into Django..."
mkdir -p src/static/assets/ src/templates/
cp -R frontend/dist/assets/* src/static/assets/ || warn "No assets directory found (is Vite output empty?)"
cp frontend/dist/index.html src/templates/index.html

log "Patching index.html for Django static tags..."
# Prepend {% load static %}
sed -i '1s;^;{% load static %}\n;' src/templates/index.html

# Replace asset paths with {% static %} template tags for common extensions
for ext in js css png svg jpg jpeg gif webp ico mp4 webm; do
  sed -i -E "s|/static/assets/([^\"']+\.${ext})|{% static 'assets/\1' %}|g" src/templates/index.html || true
  sed -i -E "s|/assets/([^\"']+\.${ext})|{% static 'assets/\1' %}|g" src/templates/index.html || true
done

# -----------------------------------------------------------------------------
# Django collectstatic & database migrations
# -----------------------------------------------------------------------------
log "Collecting static files (prod settings)..."
python src/manage.py collectstatic --noinput --settings=nfl_pickems.settings.prod

log "Applying database migrations (prod settings)..."
python src/manage.py migrate --settings=nfl_pickems.settings.prod

# -----------------------------------------------------------------------------
# Optional bootstrap steps (guarded by env flags)
# -----------------------------------------------------------------------------

if [[ "${CREATE_SUPERUSER:-0}" == "1" ]]; then
  log "Creating Django superuser (one-time)..."
  python src/manage.py shell --settings=nfl_pickems.settings.prod <<'PY'
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get("DJANGO_ADMIN_USERNAME")
email    = os.environ.get("DJANGO_ADMIN_EMAIL")
password = os.environ.get("DJANGO_ADMIN_PASSWORD")
if not all([username, email, password]):
    print("Missing DJANGO_ADMIN_* env vars; skipping superuser creation.")
else:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print("Superuser created:", username)
    else:
        print("Superuser already exists:", username)
PY
fi

if [[ "${RUN_DATA_BOOTSTRAP:-0}" == "1" ]]; then
  log "Populating NFL games (limit=0)..."
  python src/manage.py populate_nfl_games --limit 0 --settings=nfl_pickems.settings.prod || warn "populate_nfl_games failed (continuing)"
fi

ok "[RENDER] Build completed successfully."
