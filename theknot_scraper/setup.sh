#!/bin/bash

# Setup script for TheKnot Scraper
# This script automates the installation and configuration process

set -e  # Exit on error

echo "========================================="
echo "TheKnot Scraper Setup"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
required_version="3.8"

if (( $(echo "$python_version < $required_version" | bc -l) )); then
    echo "Error: Python $required_version or higher is required"
    echo "Current version: $python_version"
    exit 1
fi

echo "✓ Python $python_version detected"
echo ""

# Check if Chrome is installed
echo "Checking for Chrome/Chromium..."
if command -v google-chrome &> /dev/null; then
    chrome_version=$(google-chrome --version)
    echo "✓ $chrome_version"
elif command -v chromium &> /dev/null; then
    chrome_version=$(chromium --version)
    echo "✓ $chrome_version"
elif command -v chromium-browser &> /dev/null; then
    chrome_version=$(chromium-browser --version)
    echo "✓ $chrome_version"
else
    echo "⚠ Warning: Chrome/Chromium not found"
    echo "Please install Chrome or Chromium browser"
    echo "Installation will continue, but you may need to install it later"
fi
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p output
mkdir -p logs
mkdir -p cookies
echo "✓ Directories created"
echo ""

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠ Please edit .env to configure your settings"
else
    echo "✓ .env file already exists"
fi
echo ""

# Test import
echo "Testing installation..."
if python -c "from theknot_scraper import TheKnotScraper; print('✓ Import successful')" 2>/dev/null; then
    echo "✓ Installation test passed"
else
    echo "⚠ Warning: Import test failed"
    echo "You may need to check your installation"
fi
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env to configure settings (optional)"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run example: python example_single_vendor.py"
echo ""
echo "For more information, see README.md"
echo ""
