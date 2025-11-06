#!/bin/bash
# Run script for NQESH Question Generator

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "NQESH Question Generator"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found."
    echo "Please run ./scripts/setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found"
    echo "Using environment variable GEMINI_API_KEY"
    echo ""
fi

# Check if files directory has files
FILE_COUNT=$(find files -type f ! -name "README.txt" 2>/dev/null | wc -l)
if [ "$FILE_COUNT" -eq 0 ]; then
    echo "WARNING: No files found in 'files/' directory"
    echo "Please add DepEd Order documents before running."
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    echo ""
fi

# Run the application
echo "Starting NQESH Question Generator..."
echo ""
python3 -m src.nqesh_generator.core.generator

# Deactivate virtual environment
deactivate
