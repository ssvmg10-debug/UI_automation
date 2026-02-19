# Fix Playwright Browser Installation
# Run this script to manually install Playwright browsers

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  Playwright Browser Installation Fix" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill Chrome/Chromium processes
Write-Host "Step 1: Stopping browser processes..." -ForegroundColor Yellow

$processesToKill = @("chrome", "chromium", "msedge")
$killedAny = $false

foreach ($procName in $processesToKill) {
    $processes = Get-Process -Name $procName -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "  Found $($processes.Count) $procName process(es) - stopping..." -ForegroundColor Yellow
        try {
            $processes | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
            Write-Host "  ✓ Stopped $procName" -ForegroundColor Green
            $killedAny = $true
        } catch {
            Write-Host "  ⚠ Could not stop $procName" -ForegroundColor Yellow
        }
    }
}

if (-not $killedAny) {
    Write-Host "  No browser processes found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Waiting for file handles to release..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Write-Host ""

# Step 2: Clean up directories
Write-Host "Step 2: Cleaning up browser directories..." -ForegroundColor Yellow

$playwrightDir = "$env:LOCALAPPDATA\ms-playwright"

if (Test-Path $playwrightDir) {
    Write-Host "Found Playwright directory: $playwrightDir" -ForegroundColor White
    
    # Try to remove chromium directories
    $chromiumDirs = Get-ChildItem -Path $playwrightDir -Filter "chromium-*" -Directory -ErrorAction SilentlyContinue
    
    foreach ($dir in $chromiumDirs) {
        Write-Host "  Attempting to remove: $($dir.Name)" -ForegroundColor Gray
        try {
            Remove-Item -Path $dir.FullName -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ Removed $($dir.Name)" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠ Could not remove $($dir.Name) (may be locked)" -ForegroundColor Yellow
            Write-Host "    $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "Playwright directory not found (will be created)" -ForegroundColor White
}

Write-Host ""

# Step 3: Try installation with retries
Write-Host "Step 3: Installing Chromium browser..." -ForegroundColor Yellow
Write-Host ""

$maxRetries = 3
$retryCount = 0
$success = $false

while ($retryCount -lt $maxRetries -and -not $success) {
    $retryCount++
    
    if ($retryCount -gt 1) {
        Write-Host "  Retry attempt $($retryCount - 1) of $($maxRetries - 1)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
    
    try {
        $output = & python -m playwright install chromium 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $success = $true
            Write-Host ""
            Write-Host "✅ Chromium installed successfully!" -ForegroundColor Green
        } else {
            Write-Host $output
            throw "Installation failed with exit code $LASTEXITCODE"
        }
    } catch {
        if ($retryCount -lt $maxRetries) {
            Write-Host "  ⚠ Installation failed, retrying..." -ForegroundColor Yellow
        } else {
            Write-Host "  ❌ Installation failed after $maxRetries attempts" -ForegroundColor Red
        }
    }
}

Write-Host ""

if (-not $success) {
    Write-Host ("=" * 70) -ForegroundColor Red
    Write-Host "  ❌ Installation Failed" -ForegroundColor Red
    Write-Host ("=" * 70) -ForegroundColor Red
    Write-Host ""
    Write-Host "The Chromium files are locked by another process." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Option 1: Restart Computer (Most Reliable)" -ForegroundColor White
    Write-Host "  1. Save your work and restart Windows" -ForegroundColor Gray
    Write-Host "  2. After restart, run: python -m playwright install chromium" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2: Use Task Manager" -ForegroundColor White
    Write-Host "  1. Open Task Manager (Ctrl+Shift+Esc)" -ForegroundColor Gray
    Write-Host "  2. End all Chrome/Chromium/Edge processes" -ForegroundColor Gray
    Write-Host "  3. End any node.exe processes" -ForegroundColor Gray
    Write-Host "  4. Wait 10 seconds, then run: .\fix_playwright.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 3: Continue Without Browser" -ForegroundColor White
    Write-Host "  The platform can still:" -ForegroundColor Gray
    Write-Host "  - Generate test scripts (JavaScript/TypeScript)" -ForegroundColor Gray
    Write-Host "  - Plan test execution" -ForegroundColor Gray
    Write-Host "  - Show UI dashboard" -ForegroundColor Gray
    Write-Host "  You just won't be able to run live browser tests" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To start platform anyway: .\start.ps1" -ForegroundColor Cyan
    Write-Host ""
    exit 1
} else {
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host "  ✅ Setup Complete!" -ForegroundColor Green
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host ""
    Write-Host "Playwright is ready to use!" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Ensure .env file has your OPENAI_API_KEY" -ForegroundColor White
    Write-Host "  2. Run: .\start.ps1" -ForegroundColor White
    Write-Host ""
    exit 0
}
