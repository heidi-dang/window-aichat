@echo off
chcp 65001 >nul
echo ==========================================
echo AI Chat Desktop Installation
echo ==========================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo ? Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ? Python detected
echo.
echo Installing packages...
pip install google-generativeai requests Pillow --quiet
echo.
set EXE_PATH=%~dp0AIChatDesktop.exe
if exist "%EXE_PATH%" (
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\AI Chat Desktop.lnk'); $Shortcut.TargetPath = '%EXE_PATH%'; $Shortcut.Save()"
    echo ? Desktop shortcut created
)
echo.
echo Installation complete! Run AIChatDesktop.exe to start.
pause
