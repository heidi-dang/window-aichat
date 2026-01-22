@echo off
echo ========================================================
echo      AI Chat Desktop - Clean & Push to GitHub
echo ========================================================

:: 1. Run the project cleanup script
echo.
echo [1/4] Cleaning up project files...
python scripts/cleanup_project.py
if %errorlevel% neq 0 (
    echo ❌ Cleanup script failed.
    pause
    exit /b %errorlevel%
)

:: 2. Ensure .gitignore exists and is correct
echo.
echo [2/4] Verifying .gitignore...
if not exist .gitignore (
    echo Creating .gitignore...
    (
        echo # Virtual Environment
        echo venv/
        echo env/
        echo ENV/
        echo.
        echo # Python
        echo __pycache__/
        echo *.py[cod]
        echo *$py.class
        echo *.so
        echo .Python
        echo build/
        echo develop-eggs/
        echo dist/
        echo downloads/
        echo eggs/
        echo .eggs/
        echo lib/
        echo lib64/
        echo parts/
        echo sdist/
        echo var/
        echo wheels/
        echo *.egg-info/
        echo .installed.cfg
        echo *.egg
        echo.
        echo # Configuration ^& Secrets
        echo config.json
        echo .env
        echo .env.local
        echo *.key
        echo *.pem
        echo secrets.json
        echo.
        echo # Cache
        echo .cache/
        echo repo_cache/
        echo *.cache
        echo server_cache/
        echo.
        echo # IDE
        echo .vscode/
        echo .idea/
        echo *.swp
        echo *.swo
        echo *~
        echo .DS_Store
        echo.
        echo # Logs
        echo *.log
        echo logs/
        echo.
        echo # Generated files
        echo *.spec
        echo icon_info.txt
        echo .history-memo/
        echo _gemini_code_review/
        echo *.backup*
    ) > .gitignore
    echo ✓ .gitignore created.
) else (
    echo ✓ .gitignore already exists.
)

:: 3. Git operations
echo.
echo [3/4] Staging files for Git...
git add .

echo.
echo [4/4] Committing and Pushing...
set /p commit_msg="Enter commit message (default: 'Update project'): "
if "%commit_msg%"=="" set commit_msg=Update project

git commit -m "%commit_msg%"
git push origin main

if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Push failed. You might need to set up the remote origin or pull changes first.
    echo    Try: git remote add origin ^<your-repo-url^>
    echo    Or:  git pull origin main --rebase
) else (
    echo.
    echo ✅ Successfully pushed to GitHub!
)

echo.
pause
