#!/usr/bin/env bash

echo "🧱 Removing db.sqlite3..."
rm -f db.sqlite3

echo "🧱 Removing migration files..."
find backend/accounts/migrations -type f -not -name "__init__.py" -delete
echo "🧱 Removed accounts/migrations"
find backend/games/migrations -type f -not -name "__init__.py" -delete
echo "🧱 Removed games/migrations"
find backend/analytics/migrations -type f -not -name "__init__.py" -delete
echo "🧱 Removed analytics/migrations"
find backend/predictions/migrations -type f -not -name "__init__.py" -delete
echo "🧱 Removed predictions/migrations"