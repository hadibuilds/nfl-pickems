#!/bin/bash

echo "🔄 Starting full React → Django sync process..."

# 0. Remove old React build just in case
echo "🧼 Cleaning old React build..."
rm -rf frontend/dist/
rm -rf src/static/assets/
rm -rf staticfiles/
rm -f src/templates/index.html

# 1. Build React app
echo "📦 Building React app with Vite..."
cd frontend || { echo "❌ Could not cd into frontend/"; exit 1; }
npm install || { echo "❌ npm install failed"; exit 1; }
npx vite build || { echo "❌ Vite build failed"; exit 1; }
cd ..

# 2. Clean old Django static/template files
echo "🧹 Cleaning Django static + template..."
rm -rf src/static/assets/
rm -rf staticfiles/
rm -f src/templates/index.html

# 3. Copy new React build to Django
echo "📁 Copying React dist/ into Django..."
mkdir -p src/static/assets/
cp -R frontend/dist/assets/* src/static/assets/ || { echo "❌ Asset copy failed"; exit 1; }
cp frontend/dist/index.html src/templates/index.html || { echo "❌ index.html copy failed"; exit 1; }

# 4. Patch index.html with Django static tags (safe version)
echo "🧠 Patching index.html static asset paths..."
sed -i '' '1s;^;{% load static %}\n;' src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.js)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.css)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.png)|{% static 'assets/\1' %}|g" src/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.svg)|{% static 'assets/\1' %}|g" src/templates/index.html

# 5. Collect Django static files
echo "📦 Running collectstatic..."
source myenv/bin/activate || { echo "❌ Could not activate virtualenv"; exit 1; }
python src/manage.py collectstatic --noinput --settings=nfl_pickems.settings.dev || { echo "❌ collectstatic failed"; exit 1; }

echo "✅ Done! Restart Django and visit: http://localhost:8000"
