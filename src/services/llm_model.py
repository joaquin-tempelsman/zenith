"""
LLM Model wrapper for OpenAI integration.
Provides a unified interface for model interactions with rate limiting and call tracking.
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from ..config import settings


class OpenAIModel:
    """
    Wrapper for OpenAI ChatGPT models with call tracking and configuration.
    
    Provides a single interface for model initialization with all necessary settings.
    Tracks model calls for middleware use.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize OpenAI model wrapper.
        
        Args:
            model: Model identifier (default: gpt-4o-mini)
            temperature: Sampling temperature (0-2, default: 0.7)
            max_tokens: Maximum tokens in response (optional)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._call_count = 0
        self._instance: Optional[BaseChatModel] = None
    
    @property
    def instance(self) -> BaseChatModel:
        """
        Get or create the ChatOpenAI instance.
        
        Returns:
            BaseChatModel instance ready for use
        """
        if self._instance is None:
            self._instance = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=settings.openai_api_key,
            )
        return self._instance
    
    def reset_call_count(self) -> None:
        """Reset the call counter to zero."""
        self._call_count = 0
    
    def increment_call_count(self) -> int:
        """
        Increment call count and return the new count.
        
        Returns:
            Updated call count
        """
        self._call_count += 1
        return self._call_count
    
    def get_call_count(self) -> int:
        """
        Get current call count.
        
        Returns:
            Number of model calls made
        """
        return self._call_count


def create_openai_model(
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> OpenAIModel:
    """
    Factory function to create an OpenAI model wrapper.
    
    Args:
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        
    Returns:
        OpenAIModel instance
    """
    return OpenAIModel(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
