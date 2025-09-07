#!/bin/bash
set -e

echo "🚀 Starting NFL Pickems Development Environment"

# Load development environment
if [ -f ".env.development" ]; then
    echo "📄 Loading development environment variables..."
    export $(grep -v '^#' .env.development | grep -v '^$' | xargs)
else
    echo "⚠️  .env.development not found, using defaults"
fi

# Check if virtual environment exists
if [ ! -d "venv_pickems" ]; then
    echo "🔧 Virtual environment not found, please run ./sync_dev.sh first"
    exit 1
fi

# Activate virtual environment
source venv_pickems/bin/activate

echo "✅ Environment loaded, starting development servers..."
echo ""
echo "🔗 Development URLs:"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   Admin:    http://localhost:8000/admin (admin/admin123)"
echo ""

# Start backend server in background
echo "🖥️  Starting Django backend server..."
cd backend
INVITE_CODE=dev-invite-code DJANGO_ADMIN_USERNAME=admin DJANGO_ADMIN_PASSWORD=admin123 python manage.py runserver &
BACKEND_PID=$!
cd ..

# Give backend a moment to start
sleep 2

# Start frontend server
echo "⚡ Starting Vite frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "🎉 Both servers are starting up!"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "📝 To stop servers: kill $BACKEND_PID $FRONTEND_PID"
echo "   Or use Ctrl+C to stop this script"

# Wait for user to stop
trap "echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep script running
wait