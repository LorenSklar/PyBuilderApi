#!/bin/bash

# Test runner script for pybuilderapi
# This script sets up the virtual environment and runs the test suite

set -e  # Exit on any error

echo "🧪 Setting up test environment for pybuilderapi..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install/upgrade requirements
echo "📚 Installing/upgrading requirements..."
pip install -r requirements.txt

# Run tests
echo "🚀 Running test suite..."
python -m pytest tests/ -v --tb=short

echo "✅ Tests completed!"
