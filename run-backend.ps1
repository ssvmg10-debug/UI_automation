# Run BACKEND only - all logs go to this terminal
# Use this when debugging: open a second terminal and run run-ui.ps1 there

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$venvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env not found. Copy .env.example to .env" -ForegroundColor Red
    exit 1
}

# Load .env into process env (for API_PORT etc.)
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $val = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($key, $val, 'Process')
    }
}

$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

# Check if port is already in use (e.g. previous backend still running)
$portInUse = netstat -ano | findstr "LISTENING" | findstr ":$apiPort "
if ($portInUse) {
    $pidLine = $portInUse.Trim() -split "\s+"
    $pidOnPort = $pidLine[-1]
    Write-Host "Port $apiPort is in use by process $pidOnPort (likely a previous backend)." -ForegroundColor Yellow
    Write-Host "Stopping that process so this backend can start..." -ForegroundColor Yellow
    Get-Process -Id $pidOnPort -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Backend API (logs in this window + log files)" -ForegroundColor Cyan
Write-Host "  API: http://localhost:$apiPort (set API_PORT in .env)" -ForegroundColor White
Write-Host "  Start UI in another terminal: .\run-ui.ps1" -ForegroundColor Yellow
Write-Host "  Log files: logs\uvicorn.log, logs\backend.log, logs\automation.log" -ForegroundColor Gray
Write-Host "  To enable auto-reload: `$env:RELOAD='1'; .\run-backend.ps1" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONUNBUFFERED = "1"
python -m app.main
