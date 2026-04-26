from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, TypedDict

class LLMResponse(TypedDict):
    """Response from LLM generation."""
    content: str
    usage: dict[str, int]
    model: str

class LLMInterface(ABC):
    """
    Interface for LLM providers.
    Every file must expose get_llm() or generate().
    """

    @abstractmethod
    def get_llm(self) -> Any:
        """Return the underlying LLM provider instance."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text from a prompt."""
        pass

