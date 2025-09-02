#!/bin/bash
set -e

echo "🚀 [AMPLIFY] Building frontend for deployment..."

# Navigate to frontend directory
cd frontend

# Clean old builds and caches
echo "🧼 Cleaning previous builds and caches..."
rm -rf dist/
rm -rf node_modules/.cache/
rm -rf .cache/

# Install dependencies
echo "📦 Installing Node.js dependencies..."
npm ci --omit=dev

# Verify environment variable is available
echo "🔍 Checking environment variables..."
if [ -z "$VITE_API_URL" ]; then
    echo "⚠️  Warning: VITE_API_URL not set, using default"
    export VITE_API_URL="https://api.pickems.fun"
else
    echo "✅ VITE_API_URL: $VITE_API_URL"
fi

# Build the React application
echo "🔨 Building React application..."
npm run build

# Verify build output
echo "📋 Build verification..."
if [ ! -d "dist" ]; then
    echo "❌ Build failed: dist directory not found"
    exit 1
fi

if [ ! -f "dist/index.html" ]; then
    echo "❌ Build failed: index.html not found"
    exit 1
fi

echo "📊 Build statistics..."
ls -la dist/
echo "📁 Asset files:"
ls -la dist/assets/ 2>/dev/null || echo "No assets directory"

# Check if API URL is correctly baked into the build
echo "🔍 Verifying API URL in build..."
if grep -q "api.pickems.fun" dist/assets/*.js 2>/dev/null; then
    echo "✅ Production API URL found in build"
else
    echo "⚠️  Warning: Production API URL not found in JavaScript files"
fi

# Display final build size
echo "📦 Final build size:"
du -sh dist/

echo "✅ [AMPLIFY] Frontend build complete!"
echo "📁 Build output ready in: $(pwd)/dist/"