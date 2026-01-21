@echo off
setlocal enabledelayedexpansion

echo ====================================
echo AI Chat Desktop - Automated Setup
echo ====================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found
    pause
    exit /b 1
)

echo ✓ Python found

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Updating pip...
python -m pip install --upgrade pip setuptools wheel

echo Creating requirements file...
(
    echo google-generativeai
    echo requests
    echo Pillow
    echo cryptography
) > requirements.txt

echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Installation failed
    pause
    exit /b 1
)

echo.
echo ====================================
echo ✓ Setup Complete!
echo ====================================
echo.
pause
