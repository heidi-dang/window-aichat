@echo off
title AI Chat Desktop - Windows Deployment

echo =================================================
echo  AI Chat Desktop - Windows Deployment Script
echo =================================================
echo.

REM Step 1: Check for Python
echo [1/2] Checking for Python installation...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)
echo      ... Python found.
echo.

REM Step 2: Run the main Python setup script
echo [2/2] Executing the main Python deployment script (test_on_windows.py)...
echo This will install dependencies, generate the web app, and start the servers.
echo This may take several minutes.
echo.

python test_on_windows.py

echo.
echo =================================================
echo  Deployment script finished.
echo =================================================
echo.
pause