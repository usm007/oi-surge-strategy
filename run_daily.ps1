# OI Surge Daily Automated Update Script
# Designed for Windows Task Scheduler - runs locally to bypass cloud IP blocks

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   OI SURGE DAILY UPDATER (LOCAL PIPELINE)   " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Local Time: $(Get-Date)" -ForegroundColor Gray
Write-Host "Directory:  $ScriptDir" -ForegroundColor Gray

# 1. Run Python Script to Fetch NSE and update signal.js
Write-Host "`n[1/3] Running Signal Generator..." -ForegroundColor Yellow
python generate_signal.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] Python script failed. Aborting deployment." -ForegroundColor Red
    Exit $LASTEXITCODE
}

# 2. Check for Git changes
Write-Host "`n[2/3] Checking for signal changes..." -ForegroundColor Yellow
$gitDiff = git status --porcelain docs/signal.js

if ([string]::IsNullOrEmpty($gitDiff)) {
    Write-Host "No changes detected in signal.js. Up-to-date!" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Cyan
    Exit 0
}

# 3. Commit and push to GitHub
Write-Host "`n[3/3] Committing & Pushing to GitHub..." -ForegroundColor Yellow
git add docs/signal.js

# We include [skip ci] so the push does not trigger GitHub Actions runs unnecessarily
git commit -m "signal: daily local update [skip ci]"

# Attempt push
git push origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] Push failed. Please verify that your GitHub remote is set up correctly (run: git remote add origin <url>)" -ForegroundColor Red
} else {
    Write-Host "`n[+] Successfully pushed daily signal update to GitHub Pages!" -ForegroundColor Green
}
Write-Host "==============================================" -ForegroundColor Cyan
