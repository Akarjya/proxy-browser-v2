#!/bin/bash

# Proxy Browser V2 Startup Script

echo "╔══════════════════════════════════════════════════════╗"
echo "║                                                      ║"
echo "║            🌐 Proxy Browser V2 Launcher 🌐           ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if ! python -c "import fastapi" 2> /dev/null; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
    
    echo "🎭 Installing Playwright browsers..."
    playwright install chromium
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your proxy credentials"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after updating .env file..."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Create static directory if it doesn't exist
mkdir -p app/static

# Start the application
echo ""
echo "🚀 Starting Proxy Browser V2..."
echo "🌐 Open http://localhost:8000 in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
