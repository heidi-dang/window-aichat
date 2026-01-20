import requests
import base64
import os

class GitHubHandler:
    def __init__(self, token=None):
        self.headers = {"Authorization": f"token {token}"} if token else {}
        self.base_url = "https://api.github.com/repos"

    def fetch_repo_context(self, repo_url):
        try:
            # Parse owner and repo name
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]

            # Get the recursive file tree
            tree_url = f"{self.base_url}/{owner}/{repo}/git/trees/main?recursive=1"
            res = requests.get(tree_url, headers=self.headers)

            if res.status_code != 200:
                tree_url = tree_url.replace("/main?", "/master?")
                res = requests.get(tree_url, headers=self.headers)

            if res.status_code != 200:
                return "Error: Could not access repository. Ensure it is public."

            tree_data = res.json()
            context = ""
            # Filter for text/code files only
            allowed_ext = ('.py', '.js', '.ts', '.tsx', '.html', '.css', '.md', '.txt')

            for item in tree_data.get('tree', []):
                if item['type'] == 'blob' and item['path'].lower().endswith(allowed_ext):
                    file_res = requests.get(item['url'], headers=self.headers)
                    content = base64.b64decode(file_res.json()['content']).decode('utf-8', errors='ignore')
                    context += f"\n--- FILE: {item['path']} ---\n{content}\n"

            return context
        except Exception as e:
            return f"Error fetching repository: {str(e)}"