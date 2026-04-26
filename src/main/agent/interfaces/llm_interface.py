"""
LLM Interface - Abstract contract for LLM providers.

This interface defines the contract that all LLM providers must implement,
enabling interchangeable LLM backends (OpenAI, Anthropic, Cohere, local models).
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, TypedDict
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    COHERE = "cohere"
    BEDROCK = "bedrock"
    VERTEX = "vertex"


class GenerationSettings(TypedDict, total=False):
    """Settings for LLM generation. All fields optional."""
    temperature: float
    max_tokens: int
    top_p: float
    top_k: int
    stop_sequences: list[str]
    cache_prefix: str | None
    response_format: dict[str, str]  # e.g., {"type": "json_object"}


class LLMResponse(TypedDict):
    """Response from LLM generation."""
    content: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    model: str
    finish_reason: str
    id: str | None  # Provider-specific response ID


class LLMInterface(ABC):
    """
    Abstract base for all LLM interactions in the agent framework.

    This interface ensures all LLM implementations provide a consistent contract,
    enabling the LLMWrapper to add orthogonal concerns (caching, rate-limiting, fallback)
    without knowing the specifics of any provider.

    Implementations must be thread-safe for concurrent access.
    """

    @abstractmethod
    def get_llm(self) -> Any:
        """
        Return the underlying LangChain LLM/tool object.

        Returns:
            The underlying LLM instance (e.g., ChatOpenAI, ChatAnthropic).
        """
        pass

    @abstractmethod
    def get_provider(self) -> LLMProvider:
        """
        Return the LLM provider type.

        Returns:
            LLMProvider enum value identifying the provider.
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> LLMResponse:
        """
        Generate text/code from a text prompt.

        Args:
            prompt: The input prompt string.
            settings: Optional generation settings overrides.

        Returns:
            LLMResponse with generated content and metadata.

        Raises:
            RateLimitError: When rate limit is exceeded.
            ContextLengthError: When prompt exceeds model limits.
            LLMError: On other generation failures.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> AsyncIterator[str]:
        """
        Generate text/code from a text prompt with streaming output.

        Args:
            prompt: The input prompt string.
            settings: Optional generation settings overrides.

        Yields:
            String chunks of the generated response.

        Raises:
            RateLimitError: When rate limit is exceeded.
            ContextLengthError: When prompt exceeds model limits.
            LLMError: On other generation failures.
        """
        pass

    @abstractmethod
    async def generate_with_messages(
        self,
        messages: list[dict[str, Any]],
        settings: GenerationSettings | None = None
    ) -> LLMResponse:
        """
        Generate from a message history (chat format).

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles: 'system', 'user', 'assistant'.
            settings: Optional generation settings overrides.

        Returns:
            LLMResponse with generated content and metadata.

        Raises:
            RateLimitError: When rate limit is exceeded.
            ContextLengthError: When messages exceed model limits.
            LLMError: On other generation failures.
        """
        pass

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """
        Check if the provider supports function/tool calling.

        Returns:
            True if function calling is supported.
        """
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        """
        Check if the provider supports image inputs (vision).

        Returns:
            True if vision is supported.
        """
        pass

    @abstractmethod
    def get_context_window(self) -> int:
        """
        Return the maximum context window size in tokens.

        Returns:
            Maximum tokens the model can accept.
        """
        pass

    @abstractmethod
    def get_max_output_tokens(self) -> int:
        """
        Return the maximum output tokens the model can generate.

        Returns:
            Maximum tokens for generation.
        """
        pass
