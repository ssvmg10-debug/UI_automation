# Enterprise UI Automation Platform - Startup Script
# Run this script to start both API and UI in one go.
# For debugging (see backend logs): run run-backend.ps1 in one terminal, run-ui.ps1 in another.

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  Enterprise UI Automation Platform" -ForegroundColor Cyan
Write-Host "  Starting API Server and UI Dashboard" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Project root (where this script lives)
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# Activate virtual environment if present
$venvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & $venvActivate
} else {
    Write-Host "No venv found at $venvActivate, using current Python" -ForegroundColor Yellow
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and add your OPENAI_API_KEY" -ForegroundColor Red
    exit 1
}

Write-Host "Environment configured" -ForegroundColor Green
Write-Host ""

# Start API server in background (use venv Python if present)
$pythonExe = if (Test-Path (Join-Path $ProjectRoot "venv\Scripts\python.exe")) {
    Join-Path $ProjectRoot "venv\Scripts\python.exe"
} else {
    (Get-Command python -ErrorAction Stop).Source
}
$apiLog = Join-Path $ProjectRoot "api_startup.log"
Write-Host "Starting API server on port 8000..." -ForegroundColor Yellow
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "app.main" -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $apiLog -RedirectStandardError (Join-Path $ProjectRoot "api_startup_err.log")

Write-Host "Waiting for API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# Check if API is running (retry a few times; uvicorn reloader can be slow)
$apiOk = $false
foreach ($attempt in 1..4) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        $apiOk = $true
        break
    } catch {
        if ($attempt -lt 4) { Start-Sleep -Seconds 3 }
    }
}
if (-not $apiOk) {
    Write-Host "[FAIL] API server failed to start" -ForegroundColor Red
    if (Test-Path (Join-Path $ProjectRoot "api_startup_err.log")) {
        Write-Host "Last 20 lines of API error log:" -ForegroundColor Yellow
        Get-Content (Join-Path $ProjectRoot "api_startup_err.log") -Tail 20
    }
    Write-Host "Check that port 8000 is free and run: python -m app.main" -ForegroundColor Red
    if ($apiProcess -and -not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue }
    exit 1
}
Write-Host "[OK] API server started successfully" -ForegroundColor Green

Write-Host ""

# Start Streamlit UI
Write-Host "Starting Streamlit UI on port 8501..." -ForegroundColor Yellow
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  Platform is running!" -ForegroundColor Green
Write-Host "  API: http://localhost:8000" -ForegroundColor White
Write-Host "  UI:  http://localhost:8501" -ForegroundColor White
Write-Host "" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

try {
    streamlit run ui/streamlit_app.py
} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "API server stopped" -ForegroundColor Green
    }
    Write-Host "Services stopped" -ForegroundColor Green
}
