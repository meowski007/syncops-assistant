# ==============================================================================
# Windows PowerShell Automated Setup Script for SyncOps Assistant
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "🚀 SYNCOPS ASSISTANT: WINDOWS POWERSHELL SETUP" -ForegroundColor Cyan
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

# Run Tests
Write-Host "Running automated pytest suite..." -ForegroundColor Yellow
& .venv\Scripts\pytest.exe -v

Write-Host "`nSetup successfully finished! You can now start the services:" -ForegroundColor Green
Write-Host "  API:       .venv\Scripts\uvicorn app.main:app --reload --port 8000" -ForegroundColor White
Write-Host "  Dashboard: .venv\Scripts\streamlit run dashboard/app.py" -ForegroundColor White
Write-Host "  Slack Mock:.venv\Scripts\python -m app.slack.mock" -ForegroundColor White
