@echo off
cls
echo.
echo =========================================
echo Developer Tools Installation Script
echo =========================================
echo.
echo This will add 15 AI-powered developer tools to your app
echo A backup of main.py will be created automatically
echo.
pause

python setup_developer_tools.py

if errorlevel 1 (
    echo.
    echo ❌ Installation failed!
    pause
    exit /b 1
)

echo.
echo =========================================
echo Ready to rebuild your app!
echo =========================================
echo.
echo Run: build_app.cmd
echo.
pause
