"""
Anthropic LLM Adapter - Concrete implementation using LangChain.

This adapter implements LLMInterface using Anthropic's Claude models
via LangChain's chat model interface.
"""

from typing import Any, AsyncIterator
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.main.agent.interfaces.llm_interface import (
    LLMInterface,
    LLMProvider,
    GenerationSettings,
    LLMResponse,
)
from src.main.agent.exceptions import LLMError, RateLimitError, ContextLengthError


class AnthropicAdapter(LLMInterface):
    """
    Anthropic Claude adapter using LangChain.

    Requires ANTHROPIC_API_KEY environment variable.

    Usage:
        adapter = AnthropicAdapter(model="claude-3-5-sonnet-20241022", temperature=0.7)
        response = await adapter.generate("Hello, world!")
    """

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    # Context windows by model
    CONTEXT_WINDOWS = {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-5-haiku": 200000,
        "claude-3-5-sonnet": 200000,
        "claude-3-5-haiku-20241022": 200000,
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
    }

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        api_key: str | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """
        Initialize Anthropic adapter.

        Args:
            model: Model name (claude-3-5-sonnet-20241022, etc.).
            temperature: Default sampling temperature.
            api_key: Anthropic API key (reads from ANTHROPIC_API_KEY if None).
            max_retries: Max retry attempts for API calls.
            timeout: Request timeout in seconds.
        """
        self._model = model
        self._temperature = temperature
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._max_retries = max_retries
        self._timeout = timeout

        # Initialize LangChain chat model
        self._llm = ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=self._api_key,
            max_retries=max_retries,
            timeout=timeout,
            anthropic_api_url=None,  # Use default
        )

    def get_llm(self) -> ChatAnthropic:
        """Return the underlying LangChain ChatAnthropic instance."""
        return self._llm

    def get_provider(self) -> LLMProvider:
        """Return the provider type."""
        return LLMProvider.ANTHROPIC

    def get_context_window(self) -> int:
        """Return max context window for the model."""
        # Find best match for model prefix
        for model_prefix, window in self.CONTEXT_WINDOWS.items():
            if model_prefix in self._model:
                return window
        return 200000  # Default

    def get_max_output_tokens(self) -> int:
        """Return max output tokens for the model."""
        # Claude models can output up to 8192 tokens
        return 8192

    def supports_function_calling(self) -> bool:
        """Claude 3+ supports function calling via tool use."""
        return True

    def supports_vision(self) -> bool:
        """Claude 3+ Vision supports images."""
        return True

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

        # Build messages - Anthropic uses HumanMessage
        messages = [HumanMessage(content=prompt)]

        try:
            response = await self._llm.ainvoke(messages)

            # Extract content
            content = response.content if hasattr(response, "content") else str(response)

            # Handle different response formats
            if isinstance(content, list):
                # Claude returns content as list of content blocks
                content = "".join(
                    block.text if hasattr(block, "text") else str(block)
                    for block in content
                )

            # Extract usage info
            usage = {}
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
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

            if "rate" in error_str or "429" in error_str or "overloaded" in error_str:
                raise RateLimitError(f"Anthropic rate limit exceeded: {e}") from e
            if "context" in error_str or "maximum" in error_str or "too long" in error_str:
                raise ContextLengthError(f"Prompt exceeds context window: {e}") from e

            raise LLMError(f"Anthropic generation failed: {e}") from e

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
            async for chunk in self._llm.astream(messages):
                if hasattr(chunk, "content"):
                    content = chunk.content
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text"):
                                yield block.text
                    elif content:
                        yield str(content)

        except Exception as e:
            raise LLMError(f"Anthropic streaming failed: {e}") from e

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
                # Anthropic uses system prompt parameter, not message
                lc_messages.append(HumanMessage(content=f"[SYSTEM]{content}"))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        try:
            response = await self._llm.ainvoke(lc_messages)

            content = response.content if hasattr(response, "content") else str(response)
            if isinstance(content, list):
                content = "".join(
                    block.text if hasattr(block, "text") else str(block)
                    for block in content
                )

            usage = {}
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
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
                raise RateLimitError(f"Anthropic rate limit: {e}") from e
            raise LLMError(f"Anthropic message generation failed: {e}") from e
