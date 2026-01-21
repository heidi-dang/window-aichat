@echo off
setlocal enabledelayedexpansion

echo =========================================
echo AI Chat Desktop - PyInstaller Build
echo =========================================
echo.

REM Install/update dependencies from requirements.txt
if exist requirements.txt (
    echo Installing/updating required packages from requirements.txt...
    pip install -r requirements.txt
) else (
    echo ⚠ Warning: requirements.txt not found. Build might fail if packages are missing.
)

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
echo Cleaning old distribution files...
REM The 'build' folder is kept for caching to speed up subsequent builds.
REM If you encounter build issues, you can manually delete the 'build' folder.
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
