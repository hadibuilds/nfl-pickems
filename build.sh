#!/usr/bin/env bash
set -o errexit  # Exit immediately if a command fails

echo "📦 Installing Python packages..."
pip install -r src/requirements.txt

echo "🎨 Collecting static files..."
python src/manage.py collectstatic --noinput

echo "🧱 Running migrations..."
python src/manage.py migrate

echo "👤 Creating superuser if not exists..."
python src/manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin1234')
    print('✅ Superuser created: admin / admin1234')
else:
    print('ℹ️ Superuser already exists.')
END
