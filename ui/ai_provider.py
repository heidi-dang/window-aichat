"""
Abstract base class for AI providers to make developer tools pluggable.
This allows different AI models to be used for different tools.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger('ui.ai_provider')


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """Generate a response from the AI model."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the provider."""
        pass


class GeminiProvider(AIProvider):
    """Gemini AI provider implementation."""
    
    def __init__(self, chat_client):
        self.chat_client = chat_client
        self.logger = logging.getLogger('ui.ai_provider.GeminiProvider')
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using Gemini."""
        if not self.is_available():
            return f"{self.get_name()} is not available. Please configure your API key in Settings."
        return self.chat_client.ask_gemini(prompt)
    
    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return self.chat_client and self.chat_client.gemini_available
    
    def get_name(self) -> str:
        """Get provider name."""
        return "Gemini"


class DeepSeekProvider(AIProvider):
    """DeepSeek AI provider implementation."""
    
    def __init__(self, chat_client):
        self.chat_client = chat_client
        self.logger = logging.getLogger('ui.ai_provider.DeepSeekProvider')
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using DeepSeek."""
        if not self.is_available():
            return f"{self.get_name()} is not available. Please configure your API key in Settings."
        return self.chat_client.ask_deepseek(prompt)
    
    def is_available(self) -> bool:
        """Check if DeepSeek is available."""
        return self.chat_client and self.chat_client.deepseek_available
    
    def get_name(self) -> str:
        """Get provider name."""
        return "DeepSeek"


class AutoProvider(AIProvider):
    """Auto provider that tries multiple providers in order."""
    
    def __init__(self, providers: list):
        self.providers = providers
        self.logger = logging.getLogger('ui.ai_provider.AutoProvider')
    
    def generate_response(self, prompt: str) -> str:
        """Try providers in order until one succeeds."""
        for provider in self.providers:
            if provider.is_available():
                return provider.generate_response(prompt)
        return "No AI providers are available. Please configure at least one API key in Settings."
    
    def is_available(self) -> bool:
        """Check if any provider is available."""
        return any(provider.is_available() for provider in self.providers)
    
    def get_name(self) -> str:
        """Get provider name."""
        return "Auto"


class ProviderFactory:
    """Factory for creating AI providers."""
    
    @staticmethod
    def create_provider(provider_type: str, chat_client) -> Optional[AIProvider]:
        """Create a provider based on type."""
        if provider_type.lower() == "gemini":
            return GeminiProvider(chat_client)
        elif provider_type.lower() == "deepseek":
            return DeepSeekProvider(chat_client)
        elif provider_type.lower() == "auto":
            return AutoProvider([
                GeminiProvider(chat_client),
                DeepSeekProvider(chat_client)
            ])
        else:
            logger.warning(f"Unknown provider type: {provider_type}")
            return None
