import logging
from typing import Dict, Any, Generator, Optional
from window_aichat.core.models import ModelFactory, BaseAIModel
from window_aichat.core.context import PromptTemplate
from window_aichat.core.tokens import Tokenizer

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models: Dict[str, BaseAIModel] = {}
        self.tokenizer = Tokenizer()
        self.prompt_template = PromptTemplate()
        
        self._initialize_models()

    def _initialize_models(self):
        gemini_key = self.config.get("gemini_api_key")
        deepseek_key = self.config.get("deepseek_api_key")

        if gemini_key:
            try:
                self.models["gemini"] = ModelFactory.get_model(
                    "gemini", 
                    gemini_key, 
                    config={"max_retries": self.config.get("gemini_max_retries", 3)}
                )
            except Exception as e:
                logger.error(f"Failed to load Gemini model: {e}")

        if deepseek_key:
            try:
                self.models["deepseek"] = ModelFactory.get_model("deepseek", deepseek_key)
            except Exception as e:
                logger.error(f"Failed to load DeepSeek model: {e}")

    def get_model(self, model_name: str) -> Optional[BaseAIModel]:
        return self.models.get(model_name)

    def generate(self, prompt: str, model_name: str = "gemini") -> str:
        model = self.get_model(model_name)
        if not model:
            return f"Error: Model '{model_name}' not available."
        
        return model.generate(prompt)

    def stream_generate(self, prompt: str, model_name: str = "gemini") -> Generator[str, None, None]:
        model = self.get_model(model_name)
        if not model:
            yield f"Error: Model '{model_name}' not available."
            return

        yield from model.stream_generate(prompt)
