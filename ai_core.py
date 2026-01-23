import os
import json
import time
import random
import requests
import google.generativeai as genai
from typing import Dict, Optional
from cryptography.fernet import Fernet
import logging
import threading

def setup_logging():
    log_dir = os.path.join(os.path.expanduser("~"), ".aichatdesktop")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Get root logger
    root_logger = logging.getLogger()
    # Avoid adding duplicate handlers
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

    # Set up module-specific loggers
    logging.getLogger("ai_core").setLevel(logging.INFO)


class SecureConfig:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.key_file = config_path.replace(".json", ".key")
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


class AIChatClient:
    def __init__(self, config_path: str):
        self.logger = logging.getLogger("ai_core.AIChatClient")
        self.config_path = config_path
        try:
            self.secure_config = SecureConfig(config_path)
            self.config = self.secure_config.load_config()
            self.gemini_available = False
            self.deepseek_available = False
            self.gemini_error = None
            self.deepseek_error = None
            self.gemini_latency = None
            self.deepseek_latency = None
            self.configure_apis()
        except Exception as e:
            self.logger.error(f"Failed to initialize AIChatClient: {e}", exc_info=True)
            raise

    def configure_apis(self):
        if self.config.get("gemini_api_key"):
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.config["gemini_api_key"])
                self.gemini_model = genai.GenerativeModel(self.config["gemini_model"])
                self.gemini_available = True
                self.gemini_error = None
                self.logger.info("Gemini API configured successfully")
            except Exception as e:
                self.logger.error(f"Gemini config error: {e}", exc_info=True)
                self.gemini_available = False
                self.gemini_error = str(e)
        else:
            self.gemini_available = False
            self.gemini_error = "API key not configured"

        if self.config.get("deepseek_api_key"):
            self.deepseek_available = True
            self.deepseek_error = None
            self.logger.info("DeepSeek API key found")
        else:
            self.deepseek_available = False
            self.deepseek_error = "API key not configured"

    def ask_gemini(self, prompt: str) -> str:
        if not self.gemini_available:
            error_msg = f"Gemini API not configured. {self.gemini_error or 'Please set your API key in Settings.'}"
            self.logger.warning(error_msg)
            return error_msg

        max_retries = int(self.config.get("gemini_max_retries", 3))
        base_delay = 2  # Start with a 2-second delay
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"Gemini API call attempt {attempt + 1}/{max_retries}"
                )
                response = self.gemini_model.generate_content(prompt)
                elapsed = time.time() - start_time
                self.gemini_latency = elapsed

                # The response might be empty if blocked.
                if not response.parts:
                    error_msg = "Gemini Error: Response was blocked, likely due to safety filters or an empty prompt."
                    self.logger.warning(error_msg)
                    self.gemini_error = "Response blocked by safety filters"
                    return error_msg

                self.gemini_error = None
                self.logger.info(
                    f"Gemini API call successful (latency: {elapsed:.2f}s)"
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                # Check if the error is a rate limit error
                if "429" in error_str and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt) + random.uniform(0, 1)
                    self.logger.warning(
                        f"Gemini API rate limit hit (429). Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    # For other errors or if it's the last retry
                    self.logger.error(f"Gemini Error: {e}", exc_info=True)
                    self.gemini_error = error_str
                    if attempt == max_retries - 1:
                        return f"Gemini Error: {error_str}"

        return "Gemini Error: Failed to get a response after multiple retries due to rate limiting."

    def ask_deepseek(self, prompt: str) -> str:
        if not self.deepseek_available:
            error_msg = f"DeepSeek API not configured. {self.deepseek_error or 'Please set your API key in Settings.'}"
            self.logger.warning(error_msg)
            return error_msg

        headers = {
            "Authorization": f'Bearer {self.config["deepseek_api_key"]}',
            "Content-Type": "application/json",
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        start_time = time.time()
        try:
            import requests

            self.logger.debug("DeepSeek API call initiated")
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
            )
            elapsed = time.time() - start_time
            self.deepseek_latency = elapsed

            if response.status_code == 200:
                result = response.json()
                self.deepseek_error = None
                self.logger.info(
                    f"DeepSeek API call successful (latency: {elapsed:.2f}s)"
                )
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"DeepSeek HTTP Error: {response.status_code}"
                if response.status_code == 401:
                    error_msg += " (Invalid API key)"
                    self.deepseek_error = "Invalid API key"
                elif response.status_code == 429:
                    error_msg += " (Rate limit exceeded)"
                    self.deepseek_error = "Rate limit exceeded"
                else:
                    self.deepseek_error = f"HTTP {response.status_code}"
                self.logger.error(error_msg)
                return error_msg
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            error_msg = "DeepSeek Error: Request timeout"
            self.deepseek_error = "Request timeout"
            self.logger.error(error_msg, exc_info=True)
            return error_msg
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"DeepSeek Error: {str(e)}"
            self.deepseek_error = str(e)
            self.logger.error(error_msg, exc_info=True)
            return error_msg

    def ask_both(self, prompt: str) -> Dict[str, str]:
        responses = {}

        def ask_gemini_thread():
            responses["gemini"] = self.ask_gemini(prompt)

        def ask_deepseek_thread():
            responses["deepseek"] = self.ask_deepseek(prompt)

        gemini_thread = threading.Thread(target=ask_gemini_thread)
        deepseek_thread = threading.Thread(target=ask_deepseek_thread)

        gemini_thread.start()
        deepseek_thread.start()

        gemini_thread.join()
        deepseek_thread.join()

        return responses
