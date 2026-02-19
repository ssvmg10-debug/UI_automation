# Run UI only - ensure backend is already running in another terminal (run-backend.ps1)
# API must be at http://localhost:8000

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$venvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Streamlit UI only" -ForegroundColor Cyan
Write-Host "  UI: http://localhost:8501" -ForegroundColor White
Write-Host "  Start backend first in another terminal: .\run-backend.ps1" -ForegroundColor Yellow
Write-Host "  Auto-reload: UI reloads when you save files" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

streamlit run ui/streamlit_app.py --server.runOnSave true
