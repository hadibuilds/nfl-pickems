#!/bin/bash

echo "🔄 Starting full React → Django sync process..."

# 0. Clean previous build
echo "🧼 Cleaning old builds..."
rm -rf frontend/dist/
rm -rf src/static/assets/
rm -rf staticfiles/
rm -f src/templates/index.html

# 1. Build React app
echo "📦 Installing frontend dependencies & building with Vite..."
cd frontend || { echo "❌ Could not cd into frontend/"; exit 1; }
npm install || { echo "❌ npm install failed"; exit 1; }
npx vite build || { echo "❌ Vite build failed"; exit 1; }
cd ..

# 2. Copy React build into Django
echo "📁 Copying React build into Django..."
mkdir -p src/static/assets/
cp -R frontend/dist/assets/* src/static/assets/ || { echo "❌ Asset copy failed"; exit 1; }
cp frontend/dist/index.html src/templates/index.html || { echo "❌ index.html copy failed"; exit 1; }

# 3. Patch static tags for Django
echo "🧠 Patching index.html static asset paths..."
sed -i '' '1s;^;{% load static %}\n;' src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.js)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.css)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.png)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.svg)|{% static 'assets/\1' %}|g" src/templates/index.html

# 4. Detect environment
if [ "$RENDER" = "true" ] || [[ "$DJANGO_SETTINGS_MODULE" == *prod* ]]; then
  SETTINGS="nfl_pickems.settings.prod"
else
  SETTINGS="nfl_pickems.settings.dev"

  # Only activate virtualenv locally
  if [ -d "myenv" ]; then
    echo "🐍 Activating local virtualenv..."
    source myenv/bin/activate || { echo "❌ Failed to activate myenv"; exit 1; }
  fi
fi

# 5. Collect static files
echo "📦 Running collectstatic using $SETTINGS..."
python src/manage.py collectstatic --noinput --settings=$SETTINGS || { echo "❌ collectstatic failed"; exit 1; }

echo "✅ Done! Restart Django and visit: http://localhost:8000"
