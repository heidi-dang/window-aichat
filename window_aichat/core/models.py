from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, Optional, List
import logging
import requests
import warnings

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r"(?s).*All support for the `google\.generativeai` package has ended\..*",
)
import google.generativeai as genai
import time
import random

logger = logging.getLogger(__name__)


class BaseAIModel(ABC):
    def __init__(self, api_key: str, model_name: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        pass


class GeminiModel(BaseAIModel):
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        config: Dict[str, Any] = None,
    ):
        super().__init__(api_key, model_name, config)
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise

    def generate(self, prompt: str) -> str:
        max_retries = int(self.config.get("max_retries", 3))
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(prompt)
                if not response.parts:
                    return "Error: Response blocked by safety filters."
                return response.text
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt) + random.uniform(0, 1)
                    time.sleep(delay)
                elif attempt == max_retries - 1:
                    logger.error(f"Gemini generation failed: {e}")
                    return f"Error: {str(e)}"
        return "Error: Failed after retries."

    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        try:
            response = self.client.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            yield f"Error: {str(e)}"


class DeepSeekModel(BaseAIModel):
    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        config: Dict[str, Any] = None,
    ):
        super().__init__(api_key, model_name, config)
        self.api_url = "https://api.deepseek.com/chat/completions"

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str) -> str:
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            response = requests.post(
                self.api_url, headers=self._get_headers(), json=data, timeout=30
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"Error: HTTP {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            return f"Error: {str(e)}"

    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        try:
            import json

            with requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=data,
                stream=True,
                timeout=30,
            ) as response:
                if response.status_code != 200:
                    yield f"Error: HTTP {response.status_code}"
                    return

                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            if line_str == "data: [DONE]":
                                break
                            try:
                                json_str = line_str[6:]  # Remove "data: " prefix
                                chunk = json.loads(json_str)
                                content = chunk["choices"][0]["delta"].get(
                                    "content", ""
                                )
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"DeepSeek streaming failed: {e}")
            yield f"Error: {str(e)}"


class ModelFactory:
    @staticmethod
    def get_model(
        provider: str, api_key: str, config: Dict[str, Any] = None
    ) -> Optional[BaseAIModel]:
        if provider == "gemini":
            return GeminiModel(api_key, config=config)
        elif provider == "deepseek":
            return DeepSeekModel(api_key, config=config)
        return None
