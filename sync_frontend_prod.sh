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

# Collect static files
echo "📦 Running collectstatic (prod)..."
python src/manage.py collectstatic --noinput --settings=nfl_pickems.settings.prod

# Make migrations before applying
echo "🧬 Making migrations..."
python src/manage.py makemigrations --settings=nfl_pickems.settings.prod

# Run migrations
echo "🧱 Running migrations..."
python src/manage.py migrate --settings=nfl_pickems.settings.prod

# Create superuser (if env vars are set)
echo "👤 Creating superuser..."
python src/manage.py shell --settings=nfl_pickems.settings.prod << END
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
