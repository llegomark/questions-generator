#!/bin/bash
# Setup script for NQESH Question Generator

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "NQESH Question Generator Setup"
echo "======================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv --copies
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Install/upgrade dependencies using venv's pip directly
echo "Installing/upgrading dependencies..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found"
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "Please edit .env file and add your GEMINI_API_KEY"
    echo "Or the API key is already configured."
else
    echo "✓ .env file exists"
fi
echo ""

# Check if files directory exists
if [ ! -d "files" ]; then
    echo "Creating 'files' directory..."
    mkdir files
    echo "✓ 'files' directory created"
else
    echo "✓ 'files' directory exists"
fi
echo ""

echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Add DepEd Order documents to the 'files/' directory"
echo "2. Run the application:"
echo "   ./scripts/run.sh"
echo ""
echo "Or manually:"
echo "   source venv/bin/activate"
echo "   python3 -m src.nqesh_generator.core.generator"
echo ""
