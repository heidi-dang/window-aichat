import os
import json
import requests
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class GitHubHandler:
    def __init__(self, cache_dir: str, token: Optional[str] = None):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.session = requests.Session()
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def fetch_repo_context(self, repo_url: str) -> str:
        """Fetch and cache GitHub repository context (full codebase)"""
        if not self._validate_github_url(repo_url):
            return "Error: Invalid GitHub URL format"

        owner, repo_name = self._extract_owner_repo(repo_url)
        if not owner or not repo_name:
             return "Error: Could not extract owner and repo name"

        # Use a cache file specific to this repo
        cache_file = os.path.join(self.cache_dir, f"{owner}_{repo_name}_full_context.json")
        
        # Check cache (valid for 24 hours)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data.get('timestamp'))
                    if datetime.now() - timestamp < timedelta(hours=24):
                        return data.get('context', '')
            except Exception:
                pass

        try:
            context = self.load_codebase_to_memory(owner, repo_name)
            self._save_to_cache(cache_file, context)
            return context
        except Exception as e:
            return f"Error fetching repository: {str(e)}"

    def _validate_github_url(self, url: str) -> bool:
        try:
            if not url or 'github.com' not in url:
                return False
            path = url.split('github.com/')[-1].replace('.git', '').strip('/')
            return len([p for p in path.split('/') if p]) >= 2
        except Exception:
            return False

    def _extract_owner_repo(self, url: str) -> tuple[Optional[str], Optional[str]]:
        url = url.rstrip('/').replace('.git', '')
        if 'github.com' in url:
            parts = url.split('github.com/')[-1].split('/')
            if len(parts) >= 2:
                return parts[0], parts[1]
        return None, None

    def _api_request(self, url: str) -> Any:
        response = self.session.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        return self._api_request(url)

    def get_directory_tree(self, owner: str, repo: str, branch: str = "main") -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        return self._api_request(url)

    def load_codebase_to_memory(self, owner: str, repo: str, branch: str = None) -> str:
        """Load entire codebase structure and content into a string"""
        # Get default branch if not specified
        repo_info = self.get_repo_info(owner, repo)
        if not branch:
            branch = repo_info.get('default_branch', 'main')

        tree_data = self.get_directory_tree(owner, repo, branch)
        
        allowed_extensions = {'.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.h', '.md', '.txt', '.json', '.yml', '.yaml', '.sql', '.rs', '.go'}
        
        files_to_fetch = []
        structure = []
        
        for item in tree_data.get('tree', []):
            path = item['path']
            structure.append(path)
            if item['type'] == 'blob':
                ext = os.path.splitext(path)[1].lower()
                if ext in allowed_extensions:
                    files_to_fetch.append(item)

        # Limit to prevent context overflow (fetch top 40 relevant files)
        files_to_fetch = files_to_fetch[:40] 

        memory = []
        memory.append("=" * 80)
        memory.append(f"REPOSITORY: {owner}/{repo}")
        memory.append(f"Description: {repo_info.get('description', 'N/A')}")
        memory.append(f"Language: {repo_info.get('language', 'N/A')}")
        memory.append(f"Stars: {repo_info.get('stargazers_count', 0)}")
        memory.append(f"Last Updated: {repo_info.get('updated_at', 'N/A')}")
        memory.append("=" * 80)
        memory.append("")
        
        memory.append("DIRECTORY STRUCTURE:")
        memory.append("\n".join(structure[:100]))
        if len(structure) > 100:
            memory.append(f"... and {len(structure) - 100} more files.")
        memory.append("")
        memory.append("=" * 80)
        memory.append("")

        for file_item in files_to_fetch:
            path = file_item['path']
            url = file_item['url']
            
            memory.append(f"FILE: {path}")
            memory.append("-" * 40)
            
            try:
                blob_data = self._api_request(url)
                content = ""
                if blob_data.get('encoding') == 'base64':
                    content = base64.b64decode(blob_data['content']).decode('utf-8', errors='replace')
                else:
                    content = "Error: Unknown encoding"
                memory.append(content)
            except Exception as e:
                memory.append(f"Error loading file content: {e}")
            
            memory.append("\n" + "=" * 80 + "\n")

        return "\n".join(memory)

    def get_specific_files(self, owner: str, repo: str, file_paths: List[str], branch: str = None) -> Dict[str, str]:
        """Fetch content for specific files"""
        repo_info = self.get_repo_info(owner, repo)
        if not branch:
            branch = repo_info.get('default_branch', 'main')
            
        results = {}
        for path in file_paths:
            try:
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
                data = self._api_request(url)
                if data.get('encoding') == 'base64':
                    content = base64.b64decode(data['content']).decode('utf-8')
                    results[path] = content
                else:
                    results[path] = "Error: Not base64 encoded"
            except Exception as e:
                results[path] = f"Error: {str(e)}"
        return results

    def _save_to_cache(self, cache_file: str, context: str):
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'context': context,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
