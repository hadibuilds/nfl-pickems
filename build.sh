#!/usr/bin/env bash
set -o errexit  # Exit immediately if a command fails

echo "🔄 [RENDER] Syncing React → Django..."

# Clean old builds
echo "🧼 Cleaning previous builds..."
rm -rf frontend/dist/
rm -rf backend/static/assets/
rm -rf staticfiles/
rm -f backend/templates/index.html

echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Build React
echo "📦 Installing & building frontend (Render)..."
cd frontend
npm install
npx vite build
cd ..

# Copy assets to Django
echo "📁 Copying built assets..."
mkdir -p backend/static/assets/
cp -R frontend/dist/assets/* backend/static/assets/
cp frontend/dist/index.html backend/templates/index.html

# Patch index.html for Django using Linux-compatible sed
echo "🧠 Patching index.html (Linux sed)..."
sed -i '1s;^;{% load static %}\n;' backend/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.js)|{% static 'assets/\1' %}|g" backend/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.css)|{% static 'assets/\1' %}|g" backend/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.png)|{% static 'assets/\1' %}|g" backend/templates/index.html
sed -i -E "s|/static/assets/([^\"]+\.svg)|{% static 'assets/\1' %}|g" backend/templates/index.html

# Collect static files
echo "📦 Running collectstatic (prod)..."
python backend/manage.py collectstatic --noinput --settings=nfl_pickems.settings.prod

# Make migrations before applying
echo "🧬 Making migrations..."
python backend/manage.py makemigrations --settings=nfl_pickems.settings.prod

# Run migrations
echo "🧱 Running migrations..."
python backend/manage.py migrate --settings=nfl_pickems.settings.prod

echo "🧱 Populating NFL games HOE..."
python backend/manage.py populate_nfl_games --limit 0 --settings=nfl_pickems.settings.prod

# Create superuser (if env vars are set)
echo "👤 Creating superuser..."
python backend/manage.py shell --settings=nfl_pickems.settings.prod << END
from django.contrib.auth import get_user_model
User = get_user_model()
username = "${DJANGO_ADMIN_USERNAME}"
email = "${DJANGO_ADMIN_EMAIL}"
password = "${DJANGO_ADMIN_PASSWORD}"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("✅ Superuser created.")
else:
    print("ℹ️ Superuser already exists.")
END

echo "✅ [RENDER] Sync complete."
