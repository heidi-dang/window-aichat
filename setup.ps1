$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "AI Chat Desktop - Automated Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Install from https://python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Updating pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Create requirements
@"
google-generativeai==0.4.0
requests==2.31.0
pillow==10.1.0
"@ | Out-File -FilePath requirements.txt -Encoding UTF8

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run: python main.py" -ForegroundColor White
Write-Host "2. Configure API keys in Settings" -ForegroundColor White
Write-Host "3. Add GitHub repo URL and fetch context" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
