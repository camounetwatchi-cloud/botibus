@echo off
setlocal enabledelayedexpansion
title Trading Bot - Antigravity Terminal
color 0B

echo =====================================================
echo      ANTIGRAVITY TRADING BOT - AUTO LAUNCHER
echo =====================================================
echo.

rem Check for existing processes to avoid DuckDB locks
echo [1/4] Cleaning up previous sessions...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /i "python.exe" > nul
if %ERRORLEVEL% == 0 (
    echo [*] Closing existing Python processes...
    taskkill /F /IM python.exe /T > nul 2>&1
    timeout /t 2 /nobreak > nul
)

echo.
echo [2/4] Checking environment and dependencies...

REM Create venv if not exists
if not exist venv (
    echo [*] Creating virtual environment...
    python -m venv venv
)

REM Install/Update dependencies
echo [*] Ensuring dependencies are installed...
venv\Scripts\python.exe -m pip install -q -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to install requirements. Please check your internet connection.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Starting trading bot (Live Session)...
set "PYTHONPATH=%CD%"
start "Trading Bot (Live)" cmd /k "title Trading Bot - LIVE && color 0E && set PYTHONPATH=%CD% && venv\Scripts\python.exe scripts\live_trade.py"

echo.
echo [4/4] Launching monitoring dashboard...
timeout /t 3 /nobreak >nul
start "Trading Dashboard" cmd /k "title Trading Dashboard && color 09 && set PYTHONPATH=%CD% && venv\Scripts\python.exe -m streamlit run src\monitoring\dashboard.py --server.port 8501"

echo.
echo =====================================================
echo ALL SERVICES STARTED SUCCESSFULLY
echo =====================================================
echo.
echo The dashboard will open in your browser automatically.
echo You can close this launcher window now.
echo.
timeout /t 10
exit
