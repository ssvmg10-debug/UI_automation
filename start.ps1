# Enterprise UI Automation Platform - Startup Script
# Run this script to start both API and UI

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  Enterprise UI Automation Platform" -ForegroundColor Cyan
Write-Host "  Starting API Server and UI Dashboard" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "C:\Users\gparavasthu\Workspace\Truvelocity\code_export\agentic-sdlc-platform\venv\Scripts\Activate.ps1"

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and add your OPENAI_API_KEY" -ForegroundColor Red
    exit 1
}

Write-Host "Environment configured" -ForegroundColor Green
Write-Host ""

# Start API server in background
Write-Host "Starting API server on port 8000..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    & "C:\Users\gparavasthu\Workspace\Truvelocity\code_export\agentic-sdlc-platform\venv\Scripts\Activate.ps1"
    python -m app.main
}

Write-Host "Waiting for API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if API is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "[OK] API server started successfully" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] API server failed to start" -ForegroundColor Red
    Write-Host "Check logs for errors" -ForegroundColor Red
    Stop-Job $apiJob
    Remove-Job $apiJob
    exit 1
}

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
    Stop-Job $apiJob
    Remove-Job $apiJob
    Write-Host "Services stopped" -ForegroundColor Green
}
