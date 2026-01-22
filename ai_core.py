import os
import json
import time
import random
import requests
import google.generativeai as genai
from typing import Dict, Optional
from cryptography.fernet import Fernet
import logging

def setup_logging():
    log_dir = os.path.join(os.path.expanduser('~'), '.aichatdesktop')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class SecureConfig:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.key_file = config_path.replace('.json', '.key')
        self.cipher = self._get_cipher()

    def _get_cipher(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
        return Fernet(key)

    def save_config(self, config: dict):
        encrypted = self.cipher.encrypt(json.dumps(config).encode())
        with open(self.config_path, 'wb') as f:
            f.write(encrypted)
        os.chmod(self.config_path, 0o600)

    def load_config(self) -> Dict[str, str]:
        default_config = {
            "gemini_api_key": os.getenv('GEMINI_API_KEY', ''),
            "deepseek_api_key": os.getenv('DEEPSEEK_API_KEY', ''),
            "github_token": os.getenv('GITHUB_TOKEN', ''),
            "gemini_model": os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
            "gemini_max_retries": os.getenv('GEMINI_MAX_RETRIES', '3')
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'rb') as f:
                    encrypted = f.read()
                decrypted = self.cipher.decrypt(encrypted).decode()
                file_config = json.loads(decrypted)
                default_config.update(file_config)
        except Exception as e:
            logging.warning(f"Could not load or decrypt config file: {e}. Using defaults.")
        return default_config

class AIChatClient:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.secure_config = SecureConfig(config_path)
        self.config = self.secure_config.load_config()
        self.gemini_available = False
        self.deepseek_available = False
        self.configure_apis()

    def configure_apis(self):
        if self.config.get("gemini_api_key"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config["gemini_api_key"])
                self.gemini_model = genai.GenerativeModel(self.config["gemini_model"])
                self.gemini_available = True
            except Exception as e:
                logging.error(f"Gemini config error: {e}")
                self.gemini_available = False
        else:
            self.gemini_available = False

        self.deepseek_available = bool(self.config.get("deepseek_api_key"))

    def ask_gemini(self, prompt: str) -> str:
        if not self.gemini_available:
            return "Gemini API not configured. Please set your API key in Settings."

        max_retries = 3
        base_delay = 2  # Start with a 2-second delay

        for attempt in range(max_retries):
            try:
                response = self.gemini_model.generate_content(prompt)
                # The response might be empty if blocked.
                if not response.parts:
                    return "Gemini Error: Response was blocked, likely due to safety filters or an empty prompt."
                return response.text
            except Exception as e:
                # Check if the error is a rate limit error
                if "429" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Gemini API rate limit hit (429). Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    # For other errors or if it's the last retry
                    logging.error(f"Gemini Error: {e}")
                    return f"Gemini Error: {str(e)}"

        return "Gemini Error: Failed to get a response after multiple retries due to rate limiting."

    def ask_deepseek(self, prompt: str) -> str:
        if not self.deepseek_available:
            return "DeepSeek API not configured. Please set your API key in Settings."

        headers = {
            'Authorization': f'Bearer {self.config["deepseek_api_key"]}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        try:
            import requests
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logging.error(f"DeepSeek HTTP Error: {response.status_code}")
                return f"DeepSeek HTTP Error: {response.status_code}"
        except Exception as e:
            logging.error(f"DeepSeek Error: {e}")
            return f"DeepSeek Error: {str(e)}"

    def ask_both(self, prompt: str) -> Dict[str, str]:
        gemini_response = self.ask_gemini(prompt)
        deepseek_response = self.ask_deepseek(prompt)
        return {"gemini": gemini_response, "deepseek": deepseek_response}
