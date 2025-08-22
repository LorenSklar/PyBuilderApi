#!/bin/bash

# Python Sandbox API - Run Script
# This script sets up a virtual environment and runs the backend server
#
# HOW TO RUN:
# 1. Make sure you have Python 3.8+ installed
# 2. Run: bash run.sh
# 3. Or if you prefer: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python main.py

set -e  # Exit on any error

echo "🐍 Setting up Python Sandbox API..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version (need 3.8+ for async features)
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python 3.8+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ All dependencies installed"

# Get port from environment or use default
PORT=${PORT:-8080}

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port $PORT is already in use. Please stop the other service first."
    exit 1
fi

echo "🚀 Starting Python Sandbox API server..."
echo "📍 Server will be available at: http://localhost:$PORT"
echo "🔌 WebSocket endpoint: ws://localhost:$PORT/ws/python"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server
python main.py
