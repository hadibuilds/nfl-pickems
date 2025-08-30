#!/bin/bash

echo "Starting full React → Django sync process..."

# 0. Remove old React build just in case
echo "🧼 Cleaning old React build..."
rm -rf frontend/dist/
rm -rf backend/static/assets/
rm -rf staticfiles/
rm -f backend/templates/index.html

# 1. Build React app
echo "📦 Building React app with Vite..."
cd frontend || { echo "❌ Could not cd into frontend/"; exit 1; }
npm run build || { echo "❌ React build failed"; exit 1; }
cd ..

# 2. Clean old Django static/template files
echo "🧹 Cleaning Django static + template..."
rm -rf backend/static/assets/
rm -rf staticfiles/
rm -f backend/templates/index.html

# 3. Copy new React build to Django
echo "📁 Copying React dist/ into Django..."
mkdir -p backend/static/assets/
cp -R frontend/dist/assets/* backend/static/assets/ || { echo "❌ Asset copy failed"; exit 1; }
cp frontend/dist/index.html backend/templates/index.html || { echo "❌ index.html copy failed"; exit 1; }

# 4. Patch index.html with Django static tags (safe version for macOS/BSD sed)
echo "🧠 Patching index.html static asset paths..."
sed -i '' '1s;^;{% load static %}\n;' backend/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.js)|{% static 'assets/\1' %}|g" backend/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.css)|{% static 'assets/\1' %}|g" backend/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.png)|{% static 'assets/\1' %}|g" backend/templates/index.html
sed -i '' -E "s|/static/assets/([^\"]+\.svg)|{% static 'assets/\1' %}|g" backend/templates/index.html

# 5. Collect Django static files
echo "📦 Running collectstatic..."
source venv_pickems/bin/activate || { echo "❌ Could not activate virtualenv"; exit 1; }
python backend/manage.py collectstatic --noinput --settings=nfl_pickems.settings.dev || { echo "❌ collectstatic failed"; exit 1; }

echo "✅ Done! Restart Django and visit: http://localhost:8000"