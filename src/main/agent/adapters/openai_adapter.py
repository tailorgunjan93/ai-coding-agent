"""
OpenAI LLM Adapter - Concrete implementation using LangChain.

This adapter implements LLMInterface using OpenAI's GPT models
via LangChain's chat model interface.
"""

from typing import Any, AsyncIterator
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.main.agent.interfaces.llm_interface import (
    LLMInterface,
    LLMProvider,
    GenerationSettings,
    LLMResponse,
)
from src.main.agent.exceptions import LLMError, RateLimitError, ContextLengthError


class OpenAIAdapter(LLMInterface):
    """
    OpenAI GPT adapter using LangChain.

    Requires OPENAI_API_KEY environment variable.

    Usage:
        adapter = OpenAIAdapter(model="gpt-4", temperature=0.7)
        response = await adapter.generate("Hello, world!")
    """

    DEFAULT_MODEL = "gpt-4"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4096

    # Context windows by model
    CONTEXT_WINDOWS = {
        "gpt-4": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-3.5-turbo": 16385,
    }

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """
        Initialize OpenAI adapter.

        Args:
            model: Model name (gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.).
            temperature: Default sampling temperature.
            api_key: OpenAI API key (reads from OPENAI_API_KEY if None).
            base_url: Optional custom base URL for API proxies.
            max_retries: Max retry attempts for API calls.
            timeout: Request timeout in seconds.
        """
        self._model = model
        self._temperature = temperature
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url
        self._max_retries = max_retries
        self._timeout = timeout

        # Initialize LangChain chat model
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=self._api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            streaming=False,
        )

    def get_llm(self) -> ChatOpenAI:
        """Return the underlying LangChain ChatOpenAI instance."""
        return self._llm

    def get_provider(self) -> LLMProvider:
        """Return the provider type."""
        return LLMProvider.OPENAI

    def get_context_window(self) -> int:
        """Return max context window for the model."""
        return self.CONTEXT_WINDOWS.get(self._model, 8192)

    def get_max_output_tokens(self) -> int:
        """Return max output tokens for the model."""
        if "gpt-4" in self._model:
            return 8192
        return 4096

    def supports_function_calling(self) -> bool:
        """OpenAI supports function calling."""
        return True

    def supports_vision(self) -> bool:
        """GPT-4 Vision supports images."""
        return "gpt-4" in self._model and "vision" not in self._model.lower()

    async def generate(
        self,
        prompt: str,
        settings: GenerationSettings | None = None,
    ) -> LLMResponse:
        """
        Generate from a text prompt.

        Args:
            prompt: Input prompt string.
            settings: Optional generation settings.

        Returns:
            LLMResponse with content and metadata.

        Raises:
            LLMError: On generation failure.
            RateLimitError: On rate limit.
            ContextLengthError: If prompt too long.
        """
        settings = settings or {}

        # Build messages
        messages = [HumanMessage(content=prompt)]

        try:
            # Invoke with LangChain
            response = await self._llm.ainvoke(messages)

            # Extract content
            content = response.content if hasattr(response, "content") else str(response)

            # Extract usage info
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            # Extract finish reason
            finish_reason = "stop"
            if hasattr(response, "usage") and response.usage:
                finish_reason = "length" if response.usage.completion_tokens == settings.get("max_tokens") else "stop"

            return LLMResponse(
                content=content,
                usage=usage,
                model=self._model,
                finish_reason=finish_reason,
                id=None,
            )

        except Exception as e:
            error_str = str(e).lower()

            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"OpenAI rate limit exceeded: {e}") from e
            if "context" in error_str or "maximum" in error_str or "too long" in error_str:
                raise ContextLengthError(f"Prompt exceeds context window: {e}") from e

            raise LLMError(f"OpenAI generation failed: {e}") from e

    async def generate_stream(
        self,
        prompt: str,
        settings: GenerationSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate with streaming output.

        Args:
            prompt: Input prompt string.
            settings: Optional generation settings.

        Yields:
            String chunks of the response.

        Raises:
            LLMError: On generation failure.
        """
        settings = settings or {}
        messages = [HumanMessage(content=prompt)]

        try:
            # Use streaming
            self._llm.streaming = True

            async for chunk in self._llm.astream(messages):
                if hasattr(chunk, "content"):
                    content = chunk.content
                    if content:
                        yield content

        except Exception as e:
            raise LLMError(f"OpenAI streaming failed: {e}") from e
        finally:
            self._llm.streaming = False

    async def generate_with_messages(
        self,
        messages: list[dict[str, Any]],
        settings: GenerationSettings | None = None,
    ) -> LLMResponse:
        """
        Generate from message history.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            settings: Optional generation settings.

        Returns:
            LLMResponse with content and metadata.
        """
        settings = settings or {}

        # Convert to LangChain messages
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        try:
            response = await self._llm.ainvoke(lc_messages)

            content = response.content if hasattr(response, "content") else str(response)

            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                usage=usage,
                model=self._model,
                finish_reason="stop",
                id=None,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(f"OpenAI rate limit: {e}") from e
            raise LLMError(f"OpenAI message generation failed: {e}") from e
