#!/bin/bash

echo "🔄 [RENDER] Syncing React → Django..."

# Clean old builds
echo "🧼 Cleaning previous builds..."
rm -rf frontend/dist/
rm -rf src/static/assets/
rm -rf staticfiles/
rm -f src/templates/index.html

# Build React
echo "📦 Installing & building frontend (Render)..."
cd frontend || exit 1
npm install
npx vite build
cd ..

# Copy assets to Django
echo "📁 Copying built assets..."
mkdir -p src/static/assets/
cp -R frontend/dist/assets/* src/static/assets/
cp frontend/dist/index.html src/templates/index.html

# Patch index.html for Django using Linux-compatible sed
echo "🧠 Patching index.html (Linux sed)..."
sed -i '1s;^;{% load static %}\n;' src/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.js)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.css)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.png)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.svg)|{% static 'assets/\1' %}|g" src/templates/index.html

# Collect static (Django handles venv automatically on Render)
echo "📦 Running collectstatic (prod)..."
python src/manage.py collectstatic --noinput --settings=nfl_pickems.settings.prod

echo "✅ [RENDER] Sync complete."
