import os
import json
import logging
from typing import Dict
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class SecureConfig:
    def __init__(self, config_path: str):
        self.config_path = os.path.abspath(config_path)
        self.key_file = self.config_path.replace(".json", ".key")
        self.cipher = self._get_cipher()

    def _get_cipher(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
        return Fernet(key)

    def save_config(self, config: dict):
        encrypted = self.cipher.encrypt(json.dumps(config).encode())
        with open(self.config_path, "wb") as f:
            f.write(encrypted)
        os.chmod(self.config_path, 0o600)

    def load_config(self) -> Dict[str, str]:
        default_config = {
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "github_token": os.getenv("GITHUB_TOKEN", ""),
            "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            "gemini_max_retries": os.getenv("GEMINI_MAX_RETRIES", "3"),
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "rb") as f:
                    encrypted = f.read()
                decrypted = self.cipher.decrypt(encrypted).decode()
                file_config = json.loads(decrypted)
                default_config.update(file_config)
        except Exception as e:
            logging.warning(
                f"Could not load or decrypt config file: {e}. Using defaults."
            )
        return default_config

    def validate_keys(self):
        """
        Check if at least one AI provider key is available.
        Raises ValueError if no keys are found.
        """
        config = self.load_config()
        if not config.get("gemini_api_key") and not config.get("deepseek_api_key"):
            raise ValueError(
                "Missing API Keys: Please set GEMINI_API_KEY or DEEPSEEK_API_KEY "
                "in environment variables or configuration file."
            )
