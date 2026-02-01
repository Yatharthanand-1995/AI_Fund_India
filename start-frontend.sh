#!/bin/bash
cd "/Users/yatharthanand/Indian Stock Fund/frontend"

echo "🎨 Starting AI Hedge Fund Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    echo "VITE_API_URL=http://localhost:8010" > .env
fi

echo ""
echo "🚀 Starting development server..."
echo "📍 Frontend will be available at: http://localhost:5173"
echo "📍 API is running at: http://localhost:8010"
echo ""

npm run dev
