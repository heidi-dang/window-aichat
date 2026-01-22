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

    def fetch_repo_structure(self, repo_url: str) -> Dict[str, Any]:
        """Fetch repository structure (file tree) only"""
        if not self._validate_github_url(repo_url):
            return {"error": "Invalid GitHub URL format"}

        owner, repo_name = self._extract_owner_repo(repo_url)
        if not owner or not repo_name:
             return {"error": "Could not extract owner and repo name"}

        try:
            repo_info = self.get_repo_info(owner, repo_name)
            default_branch = repo_info.get('default_branch', 'main')
            tree_data = self.get_directory_tree(owner, repo_name, default_branch)

            return {
                "owner": owner,
                "repo": repo_name,
                "branch": default_branch,
                "tree": tree_data.get('tree', []),
                "info": repo_info
            }
        except Exception as e:
            return {"error": f"Error fetching repository structure: {str(e)}"}

    def fetch_file_content(self, owner: str, repo: str, path: str, branch: str = "main") -> str:
        """Fetch content of a single file"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            data = self._api_request(url)
            if data.get('encoding') == 'base64':
                return base64.b64decode(data['content']).decode('utf-8', errors='replace')
            else:
                return "Error: Unknown encoding or file too large"
        except Exception as e:
            return f"Error fetching file: {str(e)}"

    def fetch_repo_context(self, repo_url: str) -> str:
        """Legacy method: Fetch and cache GitHub repository context (full codebase) - kept for compatibility but optimized"""
        # This method is now a wrapper that fetches a limited set of files to avoid overwhelming the context
        structure = self.fetch_repo_structure(repo_url)
        if "error" in structure:
            return structure["error"]

        owner = structure["owner"]
        repo = structure["repo"]
        branch = structure["branch"]
        tree = structure["tree"]

        # Filter for interesting files
        allowed_extensions = {'.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.h', '.md', '.txt', '.json', '.yml', '.yaml', '.sql', '.rs', '.go'}
        files_to_fetch = [item['path'] for item in tree if item['type'] == 'blob' and os.path.splitext(item['path'])[1].lower() in allowed_extensions]

        # Limit to top 10 files for the "auto-context" feature to be safe
        files_to_fetch = files_to_fetch[:10]

        context = []
        context.append(f"REPOSITORY: {owner}/{repo}")
        context.append(f"Description: {structure['info'].get('description', 'N/A')}")
        context.append("=" * 50)
        context.append("FILE TREE:")
        for item in tree:
             context.append(f"- {item['path']}")
        context.append("=" * 50)

        for path in files_to_fetch:
            context.append(f"FILE: {path}")
            context.append("-" * 20)
            content = self.fetch_file_content(owner, repo, path, branch)
            context.append(content)
            context.append("=" * 50)

        return "\n".join(context)

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
