# ============================================================================
# AI Chat Desktop - Complete Automated Setup Script
# Windows 11, PowerShell 7, Python 3.14.2
# 
# This script does EVERYTHING automatically:
# - Creates directory structure
# - Sets up virtual environment
# - Installs all dependencies
# - Creates all necessary files (GitHub tool, integration example, etc.)
# - Configures environment
# - Tests the setup
#
# Just double-click and follow the prompts!
# ============================================================================

$ErrorActionPreference = "Stop"

# Color functions
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "ℹ️  $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Error-Custom { param($msg) Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Header { 
    param($msg) 
    Write-Host "`n$('=' * 80)" -ForegroundColor Magenta
    Write-Host "  $msg" -ForegroundColor Magenta
    Write-Host "$('=' * 80)`n" -ForegroundColor Magenta
}

# Main setup function
function Start-Setup {
    Write-Header "AI Chat Desktop - Automated Setup"
    Write-Info "This script will set up everything you need automatically!"
    Write-Host ""
    
    # Check prerequisites
    Write-Info "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python found: $pythonVersion"
    } catch {
        Write-Error-Custom "Python not found! Please install Python 3.14.2 first."
        Write-Info "Download from: https://www.python.org/downloads/"
        pause
        exit 1
    }
    
    # Check Git
    try {
        $gitVersion = git --version 2>&1
        Write-Success "Git found: $gitVersion"
    } catch {
        Write-Error-Custom "Git not found! Please install Git for Windows first."
        Write-Info "Download from: https://git-scm.com/download/win"
        pause
        exit 1
    }
    
    Write-Host ""
    
    # Get user inputs
    Write-Header "Configuration"
    
    Write-Info "Please provide the following information:"
    Write-Host ""
    
    $githubToken = Read-Host "Enter your GitHub Personal Access Token (or press Enter to set later)"
    $geminiKey = Read-Host "Enter your Gemini API Key (or press Enter to set later)"
    $deepseekKey = Read-Host "Enter your DeepSeek API Key (or press Enter to set later)"
    
    Write-Host ""
    
    # Step 1: Create directory structure
    Write-Header "Step 1: Creating Directory Structure"
    
    $directories = @(
        "src",
        "src\config",
        "src\ui",
        "src\models",
        "src\utils",
        "src\github_tools",
        "tests",
        "logs",
        ".github_cache"
    )
    
    foreach ($dir in $directories) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Success "Created: $dir"
    }
    
    # Step 2: Create virtual environment
    Write-Header "Step 2: Setting Up Virtual Environment"
    
    if (Test-Path "venv") {
        Write-Warning "Virtual environment already exists. Removing old one..."
        Remove-Item -Recurse -Force venv
    }
    
    Write-Info "Creating virtual environment..."
    python -m venv venv
    Write-Success "Virtual environment created"
    
    Write-Info "Activating virtual environment..."
    & .\venv\Scripts\Activate.ps1
    Write-Success "Virtual environment activated"
    
    # Step 3: Upgrade pip
    Write-Header "Step 3: Upgrading pip"
    python -m pip install --upgrade pip --quiet
    Write-Success "pip upgraded"
    
    # Step 4: Install dependencies
    Write-Header "Step 4: Installing Dependencies"
    
    # Create requirements.txt
    $requirements = @'
google-generativeai>=0.3.0
requests>=2.31.0
pyinstaller>=6.0.0
pydantic>=2.5.0
keyring>=24.3.0
aiohttp>=3.9.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.12.0
flake8>=6.1.0
mypy>=1.7.0
rich>=13.7.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
'@
    
    $requirements | Out-File -FilePath "requirements.txt" -Encoding utf8
    Write-Success "requirements.txt created"
    
    Write-Info "Installing packages (this may take a few minutes)..."
    pip install -r requirements.txt --quiet
    Write-Success "All dependencies installed"
    
    # Step 5: Create __init__.py files
    Write-Header "Step 5: Creating Package Files"
    
    $initFiles = @(
        "src\__init__.py",
        "src\config\__init__.py",
        "src\ui\__init__.py",
        "src\models\__init__.py",
        "src\utils\__init__.py",
        "src\github_tools\__init__.py",
        "tests\__init__.py"
    )
    
    foreach ($file in $initFiles) {
        New-Item -ItemType File -Force -Path $file | Out-Null
        Write-Success "Created: $file"
    }
    
    # Step 6: Create GitHub Tool
    Write-Header "Step 6: Creating GitHub Repository Tool"
    
    $githubToolCode = @'
"""
GitHub Repository Tool for AI Chat Application
Enables AI models to fetch, analyze, and maintain context from GitHub repositories
Optimized for Windows 11, PowerShell 7, Python 3.14.2
"""

import os
import sys
import json
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64
from datetime import datetime, timedelta
import pickle


class GitHubRepoTool:
    """
    Tool for AI models to interact with GitHub repositories.
    Provides caching, content fetching, and memory management.
    """
    
    def __init__(
        self,
        owner: str,
        repo: str,
        token: Optional[str] = None,
        cache_dir: str = ".github_cache",
        cache_duration_hours: int = 24
    ):
        """
        Initialize GitHub repository tool.
        
        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            token: GitHub personal access token (optional, but recommended)
            cache_dir: Directory to store cached repository data
            cache_duration_hours: How long to cache data before refreshing
        """
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.cache_dir = Path(cache_dir)
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # Create cache directory
        self.cache_dir.mkdir(exist_ok=True)
        
        # Headers for API requests
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a given key."""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_key}.cache"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid."""
        if not cache_path.exists():
            return False
        
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mtime < self.cache_duration
    
    def _read_cache(self, key: str) -> Optional[Any]:
        """Read data from cache if valid."""
        cache_path = self._get_cache_path(key)
        if self._is_cache_valid(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        return None
    
    def _write_cache(self, key: str, data: Any):
        """Write data to cache."""
        cache_path = self._get_cache_path(key)
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
    
    def _api_request(self, endpoint: str, use_cache: bool = True) -> Any:
        """Make API request with caching support."""
        cache_key = f"api_{endpoint}"
        
        # Try cache first
        if use_cache:
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached
        
        # Make API request
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        # Cache the result
        self._write_cache(cache_key, data)
        return data
    
    def get_repo_info(self) -> Dict[str, Any]:
        """Get repository metadata."""
        return self._api_request("")
    
    def list_files(self, path: str = "", branch: str = "main") -> List[Dict[str, Any]]:
        """
        List files in a repository directory.
        
        Args:
            path: Directory path (empty string for root)
            branch: Branch name
            
        Returns:
            List of file/directory information
        """
        endpoint = f"contents/{path}?ref={branch}"
        return self._api_request(endpoint)
    
    def get_file_content(
        self,
        file_path: str,
        branch: str = "main",
        decode: bool = True
    ) -> str:
        """
        Get content of a specific file.
        
        Args:
            file_path: Path to file in repository
            branch: Branch name
            decode: Whether to decode base64 content
            
        Returns:
            File content as string
        """
        endpoint = f"contents/{file_path}?ref={branch}"
        data = self._api_request(endpoint)
        
        if decode and 'content' in data:
            content = base64.b64decode(data['content']).decode('utf-8')
            return content
        
        return data
    
    def get_directory_tree(
        self,
        path: str = "",
        branch: str = "main",
        max_depth: int = 5,
        current_depth: int = 0
    ) -> Dict[str, Any]:
        """
        Get recursive directory tree structure.
        
        Args:
            path: Starting directory path
            branch: Branch name
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth (internal)
            
        Returns:
            Nested dictionary representing directory structure
        """
        if current_depth >= max_depth:
            return {}
        
        try:
            items = self.list_files(path, branch)
        except Exception as e:
            print(f"Error fetching {path}: {e}")
            return {}
        
        tree = {}
        for item in items:
            if item['type'] == 'dir':
                tree[item['name']] = self.get_directory_tree(
                    item['path'],
                    branch,
                    max_depth,
                    current_depth + 1
                )
            else:
                tree[item['name']] = {
                    'type': 'file',
                    'size': item['size'],
                    'path': item['path']
                }
        
        return tree
    
    def get_all_python_files(self, branch: str = "main") -> List[str]:
        """Get list of all Python files in repository."""
        tree = self.get_directory_tree(branch=branch)
        
        def extract_python_files(tree_node, current_path=""):
            files = []
            for name, content in tree_node.items():
                path = f"{current_path}/{name}" if current_path else name
                if isinstance(content, dict):
                    if content.get('type') == 'file' and name.endswith('.py'):
                        files.append(path)
                    else:
                        files.extend(extract_python_files(content, path))
            return files
        
        return extract_python_files(tree)
    
    def get_codebase_summary(self, branch: str = "main") -> Dict[str, Any]:
        """
        Get comprehensive summary of the codebase.
        
        Returns:
            Dictionary with repository statistics and structure
        """
        cache_key = f"summary_{branch}"
        cached = self._read_cache(cache_key)
        if cached:
            return cached
        
        repo_info = self.get_repo_info()
        tree = self.get_directory_tree(branch=branch)
        python_files = self.get_all_python_files(branch)
        
        summary = {
            "repository": {
                "name": repo_info['name'],
                "description": repo_info.get('description', ''),
                "language": repo_info.get('language', ''),
                "stars": repo_info.get('stargazers_count', 0),
                "forks": repo_info.get('forks_count', 0),
                "updated_at": repo_info.get('updated_at', ''),
            },
            "structure": tree,
            "python_files": python_files,
            "total_python_files": len(python_files),
            "timestamp": datetime.now().isoformat()
        }
        
        self._write_cache(cache_key, summary)
        return summary
    
    def load_codebase_to_memory(self, branch: str = "main") -> str:
        """
        Load entire codebase into a formatted string suitable for AI context.
        
        Returns:
            Formatted string with all code files and structure
        """
        cache_key = f"memory_{branch}"
        cached = self._read_cache(cache_key)
        if cached:
            return cached
        
        summary = self.get_codebase_summary(branch)
        python_files = summary['python_files']
        
        memory = []
        memory.append("=" * 80)
        memory.append(f"REPOSITORY: {self.owner}/{self.repo}")
        memory.append(f"Description: {summary['repository']['description']}")
        memory.append(f"Last Updated: {summary['repository']['updated_at']}")
        memory.append(f"Total Python Files: {summary['total_python_files']}")
        memory.append("=" * 80)
        memory.append("")
        
        # Add directory structure
        memory.append("DIRECTORY STRUCTURE:")
        memory.append(json.dumps(summary['structure'], indent=2))
        memory.append("")
        memory.append("=" * 80)
        memory.append("")
        
        # Add all Python files
        for file_path in python_files:
            memory.append(f"\n{'=' * 80}")
            memory.append(f"FILE: {file_path}")
            memory.append('=' * 80)
            try:
                content = self.get_file_content(file_path, branch)
                memory.append(content)
            except Exception as e:
                memory.append(f"Error loading file: {e}")
            memory.append("")
        
        result = "\n".join(memory)
        self._write_cache(cache_key, result)
        return result
    
    def clear_cache(self):
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        print(f"Cache cleared: {self.cache_dir}")
    
    def get_specific_files(
        self,
        file_paths: List[str],
        branch: str = "main"
    ) -> Dict[str, str]:
        """
        Get content of specific files.
        
        Args:
            file_paths: List of file paths to retrieve
            branch: Branch name
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        contents = {}
        for path in file_paths:
            try:
                contents[path] = self.get_file_content(path, branch)
            except Exception as e:
                contents[path] = f"Error: {e}"
        return contents


# Example usage function
def main():
    """Example usage of GitHubRepoTool."""
    # Configuration
    OWNER = "heidi-dang"
    REPO = "window-aichat"
    TOKEN = os.getenv("GITHUB_TOKEN")
    
    # Initialize tool
    gh_tool = GitHubRepoTool(OWNER, REPO, TOKEN)
    
    # Get repository summary
    print("Fetching repository summary...")
    summary = gh_tool.get_codebase_summary()
    print(f"\nRepository: {summary['repository']['name']}")
    print(f"Description: {summary['repository']['description']}")
    print(f"Python files found: {summary['total_python_files']}")
    print(f"\nFiles: {summary['python_files']}")
    
    # Load specific files
    print("\nLoading main.py...")
    files = gh_tool.get_specific_files(["main.py"])
    if "main.py" in files:
        print(f"\nmain.py preview (first 500 chars):")
        print(files["main.py"][:500])
    
    # Load entire codebase to memory
    print("\nLoading entire codebase to memory...")
    memory = gh_tool.load_codebase_to_memory()
    print(f"Total memory size: {len(memory)} characters")
    print(f"Memory can now be used as context for AI models")
    
    # Save memory to file for inspection
    output_file = Path("codebase_memory.txt")
    output_file.write_text(memory, encoding='utf-8')
    print(f"\nCodebase memory saved to: {output_file}")


if __name__ == "__main__":
    main()
'@
    
    $githubToolCode | Out-File -FilePath "src\github_tools\repo_memory.py" -Encoding utf8
    Write-Success "GitHub tool created: src\github_tools\repo_memory.py"
    
    # Step 7: Create Integration Example
    Write-Header "Step 7: Creating Integration Example"
    
    $integrationCode = @'
"""
Complete Integration Example: AI Chat with GitHub Repository Tool
Demonstrates how to integrate the GitHub tool with your AI chat application
Windows 11, PowerShell 7, Python 3.14.2
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from github_tools.repo_memory import GitHubRepoTool


def main():
    """Main demonstration."""
    print("=" * 80)
    print("AI Chat Desktop - GitHub Integration Demo")
    print("=" * 80)
    
    # Configuration
    OWNER = "heidi-dang"
    REPO = "window-aichat"
    TOKEN = os.getenv("GITHUB_TOKEN")
    
    if not TOKEN:
        print("\n⚠️  Warning: GITHUB_TOKEN not set!")
        print("   Some features may be rate-limited.")
        print("   Set it with: $env:GITHUB_TOKEN = 'your_token'")
        print()
    
    # Initialize tool
    print("\n1. Initializing GitHub Repository Tool...")
    gh_tool = GitHubRepoTool(OWNER, REPO, TOKEN)
    print("   ✅ Tool initialized")
    
    # Get repository info
    print("\n2. Fetching repository information...")
    try:
        repo_info = gh_tool.get_repo_info()
        print(f"   Name: {repo_info['name']}")
        print(f"   Description: {repo_info.get('description', 'N/A')}")
        print(f"   Language: {repo_info.get('language', 'N/A')}")
        print(f"   Stars: {repo_info.get('stargazers_count', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # List files
    print("\n3. Listing repository files...")
    try:
        files = gh_tool.list_files()
        print(f"   Found {len(files)} files/directories:")
        for f in files[:10]:  # Show first 10
            print(f"      {f['type']}: {f['name']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Get Python files
    print("\n4. Finding all Python files...")
    try:
        py_files = gh_tool.get_all_python_files()
        print(f"   Found {len(py_files)} Python files:")
        for pf in py_files:
            print(f"      {pf}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Get codebase summary
    print("\n5. Getting codebase summary...")
    try:
        summary = gh_tool.get_codebase_summary()
        print(f"   Total Python files: {summary['total_python_files']}")
        print(f"   Last updated: {summary['repository']['updated_at']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Load codebase to memory
    print("\n6. Loading codebase to AI memory...")
    try:
        memory = gh_tool.load_codebase_to_memory()
        print(f"   ✅ Loaded {len(memory)} characters into memory")
        
        # Save to file
        output_file = Path("codebase_memory.txt")
        output_file.write_text(memory, encoding='utf-8')
        print(f"   ✅ Saved to: {output_file}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Demo completed! Check codebase_memory.txt for the full context.")
    print("=" * 80)


if __name__ == "__main__":
    main()
'@
    
    $integrationCode | Out-File -FilePath "test_integration.py" -Encoding utf8
    Write-Success "Integration example created: test_integration.py"
    
    # Step 8: Create .env file
    Write-Header "Step 8: Creating Configuration Files"
    
    $envContent = @"
# GitHub Configuration
GITHUB_TOKEN=$githubToken
GITHUB_OWNER=heidi-dang
GITHUB_REPO=window-aichat

# API Keys
GEMINI_API_KEY=$geminiKey
DEEPSEEK_API_KEY=$deepseekKey

# Application Settings
APP_NAME=AI Chat Desktop
CACHE_DIR=.github_cache
LOG_LEVEL=INFO
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding utf8
    Write-Success ".env file created"
    
    # Update .gitignore
    $gitignoreContent = @'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
*.log

# Cache
.github_cache/
*.cache

# OS
.DS_Store
Thumbs.db
'@
    
    $gitignoreContent | Out-File -FilePath ".gitignore" -Encoding utf8
    Write-Success ".gitignore updated"
    
    # Step 9: Create helper scripts
    Write-Header "Step 9: Creating Helper Scripts"
    
    # dev.ps1
    $devScript = @'
# dev.ps1 - Start development session

Write-Host "Starting AI Chat Desktop development..." -ForegroundColor Green

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Load environment variables
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    Write-Host "✅ Environment variables loaded" -ForegroundColor Green
}

# Show status
Write-Host "`nPython version:" -ForegroundColor Yellow
python --version

Write-Host "`nEnvironment check:" -ForegroundColor Yellow
if ($env:GITHUB_TOKEN) {
    Write-Host "✅ GITHUB_TOKEN is set" -ForegroundColor Green
} else {
    Write-Host "❌ GITHUB_TOKEN not found" -ForegroundColor Red
}

Write-Host "`nAvailable commands:" -ForegroundColor Cyan
Write-Host "  python main.py              - Run main application" -ForegroundColor White
Write-Host "  python test_integration.py  - Test GitHub integration" -ForegroundColor White
Write-Host "  pytest tests/               - Run tests" -ForegroundColor White
Write-Host "  black src/                  - Format code" -ForegroundColor White

Write-Host "`nReady to code! 🚀" -ForegroundColor Green
'@
    
    $devScript | Out-File -FilePath "dev.ps1" -Encoding utf8
    Write-Success "dev.ps1 created"
    
    # test.ps1
    $testScript = @'
# test.ps1 - Run tests

Write-Host "Running tests..." -ForegroundColor Green

.\venv\Scripts\Activate.ps1

pytest tests/ -v

Write-Host "`nTests complete!" -ForegroundColor Green
'@
    
    $testScript | Out-File -FilePath "test.ps1" -Encoding utf8
    Write-Success "test.ps1 created"
    
    # Step 10: Set environment variables
    Write-Header "Step 10: Setting Environment Variables"
    
    if ($githubToken) {
        $env:GITHUB_TOKEN = $githubToken
        [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', $githubToken, 'User')
        Write-Success "GITHUB_TOKEN set (permanent)"
    } else {
        Write-Warning "GITHUB_TOKEN not provided - set it later with dev.ps1"
    }
    
    # Step 11: Store API keys securely (if provided)
    Write-Header "Step 11: Storing API Keys Securely"
    
    if ($geminiKey -or $deepseekKey) {
        $storeKeysScript = @"
import keyring

service_name = 'AIChatDesktop'

gemini_key = '$geminiKey'
deepseek_key = '$deepseekKey'

if gemini_key:
    keyring.set_password(service_name, 'gemini_api_key', gemini_key)
    print('✅ Gemini API key stored securely')

if deepseek_key:
    keyring.set_password(service_name, 'deepseek_api_key', deepseek_key)
    print('✅ DeepSeek API key stored securely')

print('API keys are now stored in Windows Credential Manager')
"@
        
        $storeKeysScript | python
    } else {
        Write-Warning "No API keys provided - you can add them later"
    }
    
    # Step 12: Test the setup
    Write-Header "Step 12: Testing Setup"
    
    Write-Info "Running integration test..."
    python test_integration.py
    
    # Step 13: Create README
    Write-Header "Step 13: Creating Documentation"
    
    $readmeContent = @"
# AI Chat Desktop - Enhanced Edition

A powerful Windows desktop application for chatting with multiple AI models (Gemini & DeepSeek) with GitHub repository integration.

## 🚀 Quick Start

### First Time Setup
1. Double-click \`SETUP_COMPLETE.ps1\` to run the automated setup
2. Follow the prompts to enter your API keys
3. Done! The application is ready to use

### Daily Use
- Double-click \`dev.ps1\` to start your development session
- Run \`python test_integration.py\` to test GitHub integration
- Run \`python main.py\` to start the main application

## 📁 Project Structure

\`\`\`
window-aichat/
├── src/                      # Source code
│   ├── config/              # Configuration
│   ├── ui/                  # User interface
│   ├── models/              # AI model integrations
│   ├── utils/               # Utilities
│   └── github_tools/        # GitHub integration
├── tests/                   # Test files
├── venv/                    # Virtual environment
├── .github_cache/           # GitHub API cache
├── dev.ps1                  # Development starter script
├── test.ps1                 # Test runner script
└── test_integration.py      # GitHub integration demo
\`\`\`

## 🔑 API Keys

API keys are stored securely in Windows Credential Manager:
- Gemini API Key: https://aistudio.google.com/app/apikey
- DeepSeek API Key: https://platform.deepseek.com/
- GitHub Token: https://github.com/settings/tokens

## 🛠️ Development

\`\`\`powershell
# Start development session
.\dev.ps1

# Run tests
.\test.ps1

# Format code
black src/

# Test GitHub integration
python test_integration.py
\`\`\`

## 📖 Features

- ✅ Dual AI model comparison (Gemini + DeepSeek)
- ✅ GitHub repository integration
- ✅ Smart caching system
- ✅ Secure API key storage
- ✅ Export conversations
- ✅ Async API calls (no UI freezing)

## 🆘 Troubleshooting

### GITHUB_TOKEN not set
\`\`\`powershell
`$env:GITHUB_TOKEN = 'your_token_here'
\`\`\`

### Virtual environment not activated
\`\`\`powershell
.\venv\Scripts\Activate.ps1
\`\`\`

### Import errors
\`\`\`powershell
pip install -r requirements.txt
\`\`\`

## 📝 License

MIT License - feel free to modify and use!
"@
    
    $readmeContent | Out-File -FilePath "README_NEW.md" -Encoding utf8
    Write-Success "README_NEW.md created"
    
    # Final summary
    Write-Header "🎉 Setup Complete!"
    
    Write-Success "Everything is set up and ready to go!"
    Write-Host ""
    Write-Info "What was created:"
    Write-Host "  ✅ Integration example"
    Write-Host "  ✅ Directory structure (src/, tests/, logs/)"
    Write-Host "  ✅ Virtual environment (venv/)"
    Write-Host "  ✅ All dependencies installed"
    Write-Host "  ✅ GitHub repository tool"
    Write-Host "  ✅