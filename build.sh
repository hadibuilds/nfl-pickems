#!/usr/bin/env bash
set -o errexit  # Exit immediately if a command fails

echo "📦 Installing Python packages..."
pip install -r requirements.txt

echo "🎨 Collecting static files..."
python src/manage.py collectstatic --noinput

echo "🧱 Running migrations..."
python src/manage.py migrate
