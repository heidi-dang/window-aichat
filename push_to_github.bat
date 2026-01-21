@echo off
setlocal enabledelayedexpansion

echo ====================================
echo AI Chat Desktop - GitHub Push Script
echo ====================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git not found. Install from https://git-scm.com
    pause
    exit /b 1
)

echo ✓ Git found

REM Check if we're in a git repository
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo ❌ Not a git repository
    pause
    exit /b 1
)

echo ✓ Git repository found

REM Create .gitignore if it doesn't exist
if not exist ".gitignore" (
    echo Creating .gitignore...
    (
        echo venv/
        echo __pycache__/
        echo *.pyc
        echo *.pyo
        echo .env
        echo config.json
        echo .DS_Store
        echo *.spec
        echo build/
        echo dist/
        echo *.egg-info/
        echo repo_cache/
    ) > .gitignore
    echo ✓ .gitignore created
)

REM Show git status
echo.
echo Current repository status:
git status

REM Stage all changes (excluding .gitignore patterns)
echo.
echo Staging changes...
git add -A

REM Check if there are changes to commit
git diff --cached --quiet
if errorlevel 1 (
    echo ✓ Changes staged
) else (
    echo No changes to commit
    pause
    exit /b 0
)

REM Commit with user input
echo.
set /p commit_msg="Enter commit message (default: 'Update: Auto push from local'): "
if "!commit_msg!"=="" set commit_msg=Update: Auto push from local

git commit -m "!commit_msg!"

if errorlevel 1 (
    echo ❌ Commit failed
    pause
    exit /b 1
)

echo ✓ Commit successful

REM Push to remote
echo.
echo Pushing to remote (origin/main)...
git push origin main

if errorlevel 1 (
    echo ❌ Push failed. Check your remote URL and permissions
    pause
    exit /b 1
)

echo.
echo ====================================
echo ✓ Push Complete!
echo ====================================
echo.
pause
