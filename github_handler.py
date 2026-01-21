import os
import json
from pathlib import Path
from typing import Dict, Optional
import requests
from datetime import datetime
from urllib.parse import urlparse
import re

class GitHubHandler:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.session = requests.Session()

    def fetch_repo_context(self, repo_url: str) -> str:
        """Fetch and cache GitHub repository context"""
        if not self._validate_github_url(repo_url):
            return "Error: Invalid GitHub URL format"

        repo_name = self._extract_repo_name(repo_url)
        cache_file = os.path.join(self.cache_dir, f"{repo_name}_context.json")

        if os.path.exists(cache_file):
            return self._load_from_cache(cache_file)

        context = self._fetch_from_github(repo_url)
        self._save_to_cache(cache_file, context)
        return context

    def _validate_github_url(self, url: str) -> bool:
        """Validate GitHub URL format"""
        try:
            if not url or 'github.com' not in url:
                return False
            path = url.split('github.com/')[-1].replace('.git', '').strip('/')
            return len([p for p in path.split('/') if p]) >= 2
        except Exception:
            return False

    def _extract_repo_name(self, url: str) -> str:
        """Extract repo name from GitHub URL"""
        url = url.rstrip('/')
        parts = url.split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}_{parts[-1]}".replace('.git', '')
        return "unknown_repo"

    def _fetch_from_github(self, repo_url: str) -> str:
        """Fetch repository info from GitHub API"""
        try:
            api_url = self._convert_to_api_url(repo_url)
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()

            repo_data = response.json()
            context = self._build_context(repo_data)
            return context
        except Exception as e:
            return f"Error fetching repository: {str(e)}"

    def _convert_to_api_url(self, url: str) -> str:
        """Convert GitHub web URL to API URL"""
        url = url.rstrip('/').replace('.git', '')
        if 'github.com' in url:
            parts = url.split('github.com/')[-1].split('/')
            return f"https://api.github.com/repos/{parts[0]}/{parts[1]}"
        raise ValueError("Invalid GitHub URL")

    def _build_context(self, repo_data: Dict) -> str:
        """Build context summary from repository data"""
        context = f"""
Repository: {repo_data.get('name', 'N/A')}
Owner: {repo_data.get('owner', {}).get('login', 'N/A')}
Description: {repo_data.get('description', 'No description')}
Language: {repo_data.get('language', 'N/A')}
Stars: {repo_data.get('stargazers_count', 0)}
Forks: {repo_data.get('forks_count', 0)}
Open Issues: {repo_data.get('open_issues_count', 0)}
URL: {repo_data.get('html_url', 'N/A')}
Created: {repo_data.get('created_at', 'N/A')}
Updated: {repo_data.get('updated_at', 'N/A')}
"""
        return context.strip()

    def _load_from_cache(self, cache_file: str) -> str:
        """Load context from cache file"""
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return data.get('context', '')
        except Exception as e:
            return f"Cache error: {str(e)}"

    def _save_to_cache(self, cache_file: str, context: str):
        """Save context to cache file"""
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'context': context,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Cache save error: {e}")
