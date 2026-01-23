import os
import time
import random
import logging
import threading
import warnings
from typing import Dict
from window_aichat.config import SecureConfig

# Suppress deprecation warning for google.generativeai
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import google.generativeai as genai

class AIChatClient:
    def __init__(self, config_path: str):
        self.logger = logging.getLogger("window_aichat.core.ai_client")
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
