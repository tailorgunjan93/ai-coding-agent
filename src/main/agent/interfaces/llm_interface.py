"""
LLM Interface - Abstract contract for all LLM providers.

This module defines the core types and abstract base class that
every LLM adapter must implement. Supports cloud providers
(OpenAI, Anthropic, Groq, Google, AWS Bedrock) and local
providers (Ollama).
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, TypedDict, NotRequired
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    GOOGLE = "google"
    AWS_BEDROCK = "aws_bedrock"
    LOCAL = "local"


class GenerationSettings(TypedDict, total=False):
    """Optional settings for LLM generation."""
    temperature: float
    max_tokens: int
    top_p: float
    stop_sequences: list[str]
    cache_prefix: str | None


class LLMResponse(TypedDict):
    """Response from LLM generation."""
    content: str
    usage: dict[str, int]
    model: str
    finish_reason: str
    id: str | None


class LLMInterface(ABC):
    """
    Abstract base for all LLM interactions in the agent framework.

    Every LLM adapter (OpenAI, Anthropic, Groq, Google, Bedrock, Ollama)
    must implement this interface. This ensures the agent can swap
    providers transparently.

    Usage:
        adapter = SomeAdapter(model="model-name")
        response = await adapter.generate("Write a Python class")
        async for chunk in adapter.generate_stream("Stream this"):
            print(chunk)
    """

    @abstractmethod
    def get_llm(self) -> Any:
        """Return the underlying LangChain LLM/chat model instance."""
        pass

    @abstractmethod
    def get_provider(self) -> LLMProvider:
        """Return the LLM provider type."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        settings: GenerationSettings | None = None,
    ) -> LLMResponse:
        """
        Generate text/code from a prompt.

        Args:
            prompt: Input prompt string.
            settings: Optional generation settings override.

        Returns:
            LLMResponse with content, usage, and metadata.

        Raises:
            LLMError: On generation failure.
            RateLimitError: On rate limit exceeded.
            ContextLengthError: If prompt exceeds context window.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        settings: GenerationSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate text/code from a prompt with streaming output.

        Args:
            prompt: Input prompt string.
            settings: Optional generation settings override.

        Yields:
            String chunks of the response.

        Raises:
            LLMError: On generation failure.
        """
        pass

    @abstractmethod
    async def generate_with_messages(
        self,
        messages: list[dict[str, Any]],
        settings: GenerationSettings | None = None,
    ) -> LLMResponse:
        """
        Generate from a message history (multi-turn conversation).

        Args:
            messages: List of message dicts with 'role' and 'content'.
            settings: Optional generation settings override.

        Returns:
            LLMResponse with content, usage, and metadata.
        """
        pass

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Check if provider supports function/tool calling."""
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        """Check if provider supports image/vision input."""
        pass

    @abstractmethod
    def get_context_window(self) -> int:
        """Return max context window size in tokens."""
        pass

    @abstractmethod
    def get_max_output_tokens(self) -> int:
        """Return max output tokens for the model."""
        pass
