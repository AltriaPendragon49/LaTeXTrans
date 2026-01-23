# Backend startup script for Windows

Write-Host "Starting LaTeXTrans Backend..." -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "venv") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Start server
Write-Host "Starting uvicorn server..." -ForegroundColor Green
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
