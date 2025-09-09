#!/bin/bash
set -e

echo "🔄 [DEV] Syncing React → Django for development..."

# Load development environment
export $(grep -v '^#' .env.development | grep -v '^$' | xargs)

# Clean old builds
echo "🧼 Cleaning previous builds..."
rm -rf frontend/dist/
rm -rf backend/static/assets/
rm -rf backend/staticfiles/
rm -f backend/templates/index.html

# Install dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
echo "📦 Building frontend for development..."
npm run build
cd ..

echo "📦 Installing Python dependencies..."
if [ ! -d "venv_pickems" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv_pickems
fi
source venv_pickems/bin/activate
pip install -r requirements.txt

# Copy assets to Django
echo "📁 Copying built assets to Django static..."
mkdir -p backend/static/assets/
cp -R frontend/dist/assets/* backend/static/assets/

# Copy index.html template
echo "📄 Copying index.html template..."
mkdir -p backend/templates
cp frontend/dist/index.html backend/templates/index.html

# Patch index.html for Django (macOS sed syntax)
echo "🧠 Patching index.html for Django template tags..."
f=backend/templates/index.html

# Add Django static loader at the top
grep -q "{% load static %}" "$f" || sed -i '' '1s;^;{% load static %}\n;' "$f"

# Replace asset paths with Django static template tags
sed -i '' -E "s|/(static/)?assets/([^\"]+\.js)|{% static 'assets/\\2' %}|g" "$f"
sed -i '' -E "s|/(static/)?assets/([^\"]+\.css)|{% static 'assets/\\2' %}|g" "$f"
sed -i '' -E "s|/(static/)?assets/([^\"]+\.png)|{% static 'assets/\\2' %}|g" "$f"
sed -i '' -E "s|/(static/)?assets/([^\"]+\.svg)|{% static 'assets/\\2' %}|g" "$f"

# Also fix image paths in JavaScript files
echo "🔧 Patching JavaScript files for Django static paths..."
for jsfile in backend/static/assets/*.js; do
    if [ -f "$jsfile" ]; then
        # Fix quoted image paths in strings
        sed -i '' -E 's|"/assets/([^"]+\.(png\|svg\|jpg\|jpeg\|gif))"|"/static/assets/\1"|g' "$jsfile"
        # Fix image paths in variable assignments (By="/assets/...)
        sed -i '' 's|="/assets/|="/static/assets/|g' "$jsfile"
    fi
done

# Django operations
echo "📦 Collecting static files..."
cd backend
INVITE_CODE=dev-invite-code DJANGO_ADMIN_USERNAME=admin DJANGO_ADMIN_PASSWORD=admin123 python manage.py collectstatic --noinput

echo "🧬 Making migrations..."
INVITE_CODE=dev-invite-code DJANGO_ADMIN_USERNAME=admin DJANGO_ADMIN_PASSWORD=admin123 python manage.py makemigrations

echo "🧱 Running migrations..."
INVITE_CODE=dev-invite-code DJANGO_ADMIN_USERNAME=admin DJANGO_ADMIN_PASSWORD=admin123 python manage.py migrate

echo "✅ [DEV] Development sync complete!"
echo ""
echo "🚀 Ready to start development servers:"
echo "   Frontend: cd frontend && npm run dev"
echo "   Backend:  cd backend && python manage.py runserver"
echo ""
echo "💡 Development tips:"
echo "   - Frontend will run on http://localhost:5173"
echo "   - Backend will run on http://localhost:8000"
echo "   - Admin panel: http://localhost:8000/admin (admin/admin123)"