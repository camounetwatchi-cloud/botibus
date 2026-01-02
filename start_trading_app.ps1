# Antigravity Trading Bot - Auto Launcher (PowerShell Version)
# This script starts both the trading bot and the monitoring dashboard

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "     ANTIGRAVITY TRADING BOT - AUTO LAUNCHER" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Starting trading bot and monitoring dashboard..." -ForegroundColor Yellow
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Start the trading bot in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir'; `$env:PYTHONPATH='.'; .\venv\Scripts\python.exe scripts\live_trade.py" -WindowStyle Normal

Write-Host "✓ Trading bot started in separate window" -ForegroundColor Green

# Wait 3 seconds before launching the dashboard
Start-Sleep -Seconds 3

# Start the Streamlit dashboard
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir'; `$env:PYTHONPATH='.'; .\venv\Scripts\python.exe -m streamlit run src\monitoring\dashboard.py" -WindowStyle Normal

Write-Host "✓ Dashboard started in separate window" -ForegroundColor Green
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Both services are starting in separate windows..." -ForegroundColor Yellow
Write-Host "The dashboard will open in your browser shortly." -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to close this launcher window..." -ForegroundColor Gray

# Wait for user input before closing
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
