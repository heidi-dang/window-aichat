@echo off
echo Cleaning old build files...
if exist build rd /s /q build
if exist dist rd /s /q dist

echo Starting PyInstaller Build...
:: --onefile: Bundles everything into one EXE
:: --windowed: Hides the console window when running the app
:: --noconfirm: Overwrites existing files without asking
pyinstaller --name="AIChatDesktop" --onefile --windowed --noconfirm main.py

echo.
echo ==========================================
echo Build Finished! Your app is in the 'dist' folder.
echo ==========================================
pause