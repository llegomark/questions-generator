#!/bin/bash

# NQESH Question Validator Runner Script
# This script runs the question validator with context caching

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "NQESH Question Bank Validator"
echo "======================================================================"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found"
    echo "Please create a .env file with your GEMINI_API_KEY"
    echo ""
    echo "Example .env file:"
    echo "GEMINI_API_KEY=your-api-key-here"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if files directory exists
if [ ! -d "files" ]; then
    echo "ERROR: 'files' directory not found"
    echo "Please create a 'files' directory and add your DepEd Order source files"
    exit 1
fi

# Check if there are files in the files directory
file_count=$(ls -1 files | wc -l)
if [ "$file_count" -eq 0 ]; then
    echo "ERROR: No files found in 'files' directory"
    echo "Please add DepEd Order source files to the 'files' directory"
    exit 1
fi

echo "Found $file_count source file(s) in 'files' directory"
echo ""

# Check if question bank file exists
QUESTION_BANK="output/nqesh_questions.json"
if [ ! -f "$QUESTION_BANK" ]; then
    echo "ERROR: Question bank file '$QUESTION_BANK' not found"
    echo "Please generate questions first using ./scripts/run.sh"
    exit 1
fi

echo "Question bank file found: $QUESTION_BANK"
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

echo "Starting validation..."
echo ""

# Run the validator
python3 -m src.nqesh_generator.core.validator

# Deactivate virtual environment
deactivate

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "Validation completed successfully!"
    echo "======================================================================"
    echo ""
    echo "Output files:"
    if [ -f "output/validation_report.json" ]; then
        echo "  ✓ output/validation_report.json (JSON format)"
    fi
    if [ -f "output/validation_report.md" ]; then
        echo "  ✓ output/validation_report.md (Markdown format)"
    fi
    echo ""
else
    echo ""
    echo "======================================================================"
    echo "Validation failed with errors"
    echo "======================================================================"
    echo ""
    echo "Please check the error messages above and try again"
    exit 1
fi
