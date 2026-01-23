#!/bin/bash
# Backend startup script

echo "Starting LaTeXTrans Backend..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start server
echo "Starting uvicorn server..."
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
