import os
import time
import logging
import threading
from typing import Dict, Generator, Optional
from window_aichat.config import SecureConfig
from window_aichat.core.engine import AIEngine

class AIChatClient:
    def __init__(self, config_path: str):
        self.logger = logging.getLogger("window_aichat.core.ai_client")
        self.config_path = config_path
        
        try:
            self.secure_config = SecureConfig(config_path)
            self.config = self.secure_config.load_config()
            
            # Initialize the new engine
            self.engine = AIEngine(self.config)
            
            # Legacy properties for backward compatibility with Desktop UI
            self.gemini_available = self.engine.get_model("gemini") is not None
            self.deepseek_available = self.engine.get_model("deepseek") is not None
            self.gemini_error = None
            self.deepseek_error = None
            self.gemini_latency = None
            self.deepseek_latency = None
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AIChatClient: {e}", exc_info=True)
            raise

    def configure_apis(self):
        """
        Re-initialize the engine with current config.
        Called by Desktop UI after settings update.
        """
        self.config = self.secure_config.load_config()
        self.engine = AIEngine(self.config)
        self.gemini_available = self.engine.get_model("gemini") is not None
        self.deepseek_available = self.engine.get_model("deepseek") is not None
        self.logger.info("APIs re-configured via Engine")

    def ask_gemini(self, prompt: str) -> str:
        start_time = time.time()
        try:
            response = self.engine.generate(prompt, "gemini")
            self.gemini_latency = time.time() - start_time
            if response.startswith("Error:"):
                self.gemini_error = response
            else:
                self.gemini_error = None
            return response
        except Exception as e:
            self.gemini_error = str(e)
            return f"Error: {str(e)}"

    def ask_deepseek(self, prompt: str) -> str:
        start_time = time.time()
        try:
            response = self.engine.generate(prompt, "deepseek")
            self.deepseek_latency = time.time() - start_time
            if response.startswith("Error:"):
                self.deepseek_error = response
            else:
                self.deepseek_error = None
            return response
        except Exception as e:
            self.deepseek_error = str(e)
            return f"Error: {str(e)}"

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

    def stream_chat(self, prompt: str, model_name: str = "gemini") -> Generator[str, None, None]:
        """New method for streaming chat responses."""
        return self.engine.stream_generate(prompt, model_name)
