import os
import requests
import base64
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger("window_aichat.services.github")


class GitHubHandler:
    def __init__(self, cache_dir: str, token: Optional[str] = None):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.session = requests.Session()
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.token_valid = False
        self.token_error = None
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            # Validate token on initialization
            self._validate_token()
        else:
            logger.warning("GitHub token not provided. Some features may be limited.")

    def _validate_token(self) -> bool:
        """Validate the GitHub token by making a test API call."""
        if not self.token:
            self.token_valid = False
            self.token_error = "No token provided"
            return False

        try:
            # Test token by getting authenticated user info
            response = self.session.get(
                "https://api.github.com/user", headers=self.headers, timeout=5
            )

            if response.status_code == 200:
                self.token_valid = True
                self.token_error = None
                user_data = response.json()
                logger.info(
                    f"GitHub token validated for user: {user_data.get('login', 'unknown')}"
                )
                return True
            elif response.status_code == 401:
                self.token_valid = False
                self.token_error = "Invalid or revoked token"
                logger.error("GitHub token is invalid or has been revoked")
                return False
            else:
                self.token_valid = False
                self.token_error = (
                    f"Token validation failed: HTTP {response.status_code}"
                )
                logger.warning(
                    f"GitHub token validation failed: {response.status_code}"
                )
                return False
        except requests.exceptions.RequestException as e:
            self.token_valid = False
            self.token_error = f"Network error: {str(e)}"
            logger.warning(f"Could not validate GitHub token: {e}")
            # Don't fail completely on network errors - token might still be valid
            return False

    def update_token(self, new_token: Optional[str]):
        """Update the GitHub token and revalidate."""
        self.token = new_token
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            self._validate_token()
        else:
            self.token_valid = False
            self.token_error = "No token provided"
            if "Authorization" in self.headers:
                del self.headers["Authorization"]

    def fetch_repo_structure(self, repo_url: str) -> Dict[str, Any]:
        """Fetch repository structure (file tree) only"""
        if not self._validate_github_url(repo_url):
            return {"error": "Invalid GitHub URL format"}

        owner, repo_name = self._extract_owner_repo(repo_url)
        if not owner or not repo_name:
            return {"error": "Could not extract owner and repo name"}

        try:
            repo_info = self.get_repo_info(owner, repo_name)
            default_branch = repo_info.get("default_branch", "main")
            tree_data = self.get_directory_tree(owner, repo_name, default_branch)

            return {
                "owner": owner,
                "repo": repo_name,
                "branch": default_branch,
                "tree": tree_data.get("tree", []),
                "info": repo_info,
            }
        except Exception as e:
            return {"error": f"Error fetching repository structure: {str(e)}"}

    def fetch_file_content(
        self, owner: str, repo: str, path: str, branch: str = "main"
    ) -> str:
        """Fetch content of a single file"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            data = self._api_request(url)
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode(
                    "utf-8", errors="replace"
                )
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
        allowed_extensions = {
            ".py",
            ".js",
            ".ts",
            ".html",
            ".css",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".md",
            ".txt",
            ".json",
            ".yml",
            ".yaml",
            ".sql",
            ".rs",
            ".go",
        }
        files_to_fetch = [
            item["path"]
            for item in tree
            if item["type"] == "blob"
            and os.path.splitext(item["path"])[1].lower() in allowed_extensions
        ]

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
            if not url or "github.com" not in url:
                return False
            path = url.split("github.com/")[-1].replace(".git", "").strip("/")
            return len([p for p in path.split("/") if p]) >= 2
        except Exception:
            return False

    def _extract_owner_repo(self, url: str) -> tuple[Optional[str], Optional[str]]:
        url = url.rstrip("/").replace(".git", "")
        if "github.com" in url:
            parts = url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        return None, None

    def _api_request(self, url: str) -> Any:
        """Make an API request with proper error handling for token issues."""
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)

            # Handle token revocation
            if response.status_code == 401:
                self.token_valid = False
                self.token_error = "Token revoked or invalid"
                logger.error("GitHub API returned 401 - token may be revoked")
                raise requests.exceptions.HTTPError(
                    f"401 Client Error: Token authentication failed. "
                    f"Please update your GitHub token in Settings."
                )

            # Handle rate limiting
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get(
                    "X-RateLimit-Remaining", "0"
                )
                if rate_limit_remaining == "0":
                    reset_time = response.headers.get("X-RateLimit-Reset", "0")
                    logger.warning(
                        f"GitHub API rate limit exceeded. Reset at: {reset_time}"
                    )
                    raise requests.exceptions.HTTPError(
                        f"403 Client Error: Rate limit exceeded. "
                        f"Please wait before making more requests."
                    )

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            raise

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        return self._api_request(url)

    def get_directory_tree(
        self, owner: str, repo: str, branch: str = "main"
    ) -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        return self._api_request(url)
