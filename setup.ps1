# ==============================================================================
# Windows PowerShell Automated Setup Script for SyncOps Assistant
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "🚀 SYNCOPS ASSISTANT: WINDOWS POWERSHELL SETUP (AI & DATA UPGRADE)" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python was not found in PATH. Please install Python 3.10+ from python.org or via 'winget install Python.Python.3.12'."
}
Write-Host "✓ Found Python: $(python --version)" -ForegroundColor Green

# Create venv if missing
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}
Write-Host "✓ Virtual environment verified." -ForegroundColor Green

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
& .venv\Scripts\pip.exe install -r requirements.txt

# Seed Database
Write-Host "Seeding synthetic database..." -ForegroundColor Yellow
& .venv\Scripts\python.exe scripts\seed_data.py

# Run ETL Pipeline
Write-Host "Executing ETL Data Pipeline (Raw -> Clean Analytical Layer)..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m pipeline.run

# Train Forecasting Models
Write-Host "Training Time-Series Forecasting models..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m forecasting.train

# Build Frontend if Node is installed
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd -or (Test-Path "C:\Program Files\nodejs\npm.cmd")) {
    $env:PATH = "C:\Program Files\nodejs;$env:PATH"
    Write-Host "Building React frontend..." -ForegroundColor Yellow
    Push-Location frontend
    & "C:\Program Files\nodejs\npm.cmd" install
    & "C:\Program Files\nodejs\npm.cmd" run build
    Pop-Location
    Write-Host "✓ Frontend built successfully." -ForegroundColor Green
}

# Run Tests
Write-Host "Running automated pytest suite (87 tests)..." -ForegroundColor Yellow
& .venv\Scripts\pytest.exe -v

Write-Host "`nSetup successfully finished! You can now start the services:" -ForegroundColor Green
Write-Host "  FastAPI REST API:  .venv\Scripts\uvicorn app.main:app --reload --port 8000" -ForegroundColor White
Write-Host "  React Frontend:    cd frontend; npm run dev" -ForegroundColor White
Write-Host "  Streamlit Cockpit: .venv\Scripts\streamlit run dashboard/app.py --server.port 8501" -ForegroundColor White
Write-Host "  Slack Mock Mode:   .venv\Scripts\python -m app.slack.mock" -ForegroundColor White
