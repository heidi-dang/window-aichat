@echo off
setlocal enabledelayedexpansion

echo =========================================
echo AI Chat Desktop - PyInstaller Build
echo =========================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo ✓ PyInstaller found

REM Check if icon exists
if not exist "icon.ico" (
    echo ⚠ Warning: icon.ico not found
    echo Creating placeholder icon...
    set ICON_FLAG=
) else (
    echo ✓ Icon file found
    set ICON_FLAG=--icon=icon.ico
)

REM Clean old builds
echo.
echo Cleaning old build files...
if exist build (
    rmdir /s /q build
    echo ✓ Removed build folder
)
if exist dist (
    rmdir /s /q dist
    echo ✓ Removed dist folder
)
if exist AIChatDesktop.spec (
    del AIChatDesktop.spec
    echo ✓ Removed spec file
)

REM Check main.py exists
if not exist "main.py" (
    echo ❌ main.py not found!
    pause
    exit /b 1
)

echo ✓ main.py found

REM Build with PyInstaller
echo.
echo Starting PyInstaller build...
pyinstaller ^
    --name="AIChatDesktop" ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    %ICON_FLAG% ^
    --add-data ".:." ^
    --collect-all google.generativeai ^
    --collect-all requests ^
    main.py

if errorlevel 1 (
    echo ❌ Build failed!
    pause
    exit /b 1
)

echo.
echo =========================================
echo ✓ Build Successful!
echo =========================================
echo.
echo Your executable is here:
echo   dist\AIChatDesktop.exe
echo.
echo To run the app:
echo   1. Double-click dist\AIChatDesktop.exe
echo   2. Or run: dist\AIChatDesktop.exe
echo.
pause
    