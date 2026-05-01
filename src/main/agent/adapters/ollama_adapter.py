"""
Ollama LLM Adapter - Local LLM provider using Ollama.

This adapter implements LLMInterface for local models running
via Ollama (https://ollama.ai). No API key or subscription required.

Supports models like deepseek-coder-v2, codellama, qwen2.5-coder,
starcoder2, llama3.1, and any model available in Ollama's library.

Prerequisites:
    1. Install Ollama: https://ollama.ai/download
    2. Pull a model: ollama pull deepseek-coder-v2:16b
    3. Ensure server is running: ollama serve
"""

from typing import Any, AsyncIterator
import logging
import httpx

from src.main.agent.interfaces.llm_interface import (
    LLMInterface,
    LLMProvider,
    GenerationSettings,
    LLMResponse,
)
from src.main.agent.exceptions import LLMError, ContextLengthError

logger = logging.getLogger(__name__)


class OllamaAdapter(LLMInterface):
    """
    Ollama adapter for local LLM inference.

    Uses langchain-ollama's ChatOllama for LangChain-compatible
    local model inference. Completely free — no API key needed.

    Usage:
        adapter = OllamaAdapter(model="deepseek-coder-v2:16b")
        response = await adapter.generate("Write a Python class for a stack")
    """

    DEFAULT_MODEL = "deepseek-coder-v2:16b"
    FALLBACK_MODEL = "codellama:7b"
    BASE_URL = "http://localhost:11434"

    # Preferred coding models (checked in order during auto-select)
    CODING_MODELS = [
        "deepseek-coder-v2",
        "qwen2.5-coder",
        "codellama",
        "starcoder2",
        "codegemma",
        "phind-codellama",
    ]

    # Known context windows for popular models
    CONTEXT_WINDOWS = {
        "deepseek-coder-v2": 128000,
        "qwen2.5-coder": 32768,
        "codellama": 16384,
        "starcoder2": 16384,
        "codegemma": 8192,
        "llama3.1": 128000,
        "llama3.2": 128000,
        "llama3.3": 128000,
        "mistral": 32768,
        "mixtral": 32768,
        "gemma2": 8192,
        "phi3": 128000,
    }

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        base_url: str | None = None,
        timeout: float = 120.0,
        auto_select_coding_model: bool = True,
    ):
        """
        Initialize Ollama adapter.

        Args:
            model: Model name. If None, auto-selects best coding model.
            temperature: Sampling temperature.
            base_url: Ollama server URL (default: http://localhost:11434).
            timeout: Request timeout in seconds (local models can be slow).
            auto_select_coding_model: If True and model is None, picks
                the best available coding-specific model.
        """
        self._base_url = base_url or self.BASE_URL
        self._temperature = temperature
        self._timeout = timeout

        # Auto-select or use provided model
        if model:
            self._model = model
        elif auto_select_coding_model:
            self._model = self._find_best_coding_model() or self.DEFAULT_MODEL
        else:
            self._model = self.DEFAULT_MODEL

        # Lazy-initialize LangChain model (import may fail if not installed)
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialize the LangChain ChatOllama instance."""
        try:
            from langchain_ollama import ChatOllama

            self._llm = ChatOllama(
                model=self._model,
                temperature=self._temperature,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        except ImportError:
            raise LLMError(
                "langchain-ollama is not installed. "
                "Install it with: pip install langchain-ollama"
            )

    def _find_best_coding_model(self) -> str | None:
        """
        Query Ollama for available models and pick the best coding one.

        Returns:
            Best available coding model name, or None if none found.
        """
        try:
            available = self.list_local_models()
            if not available:
                return None

            # Check for coding-specific models first
            for preferred in self.CODING_MODELS:
                for model_name in available:
                    if preferred in model_name.lower():
                        logger.info(f"Auto-selected coding model: {model_name}")
                        return model_name

            # Fall back to first available model
            logger.info(f"No coding model found, using: {available[0]}")
            return available[0]

        except Exception:
            return None

    @staticmethod
    def is_server_running(base_url: str | None = None) -> bool:
        """
        Check if Ollama server is running.

        Args:
            base_url: Ollama server URL to check.

        Returns:
            True if server is reachable.
        """
        url = base_url or OllamaAdapter.BASE_URL
        try:
            response = httpx.get(f"{url}/api/version", timeout=5.0)
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            return False

    def list_local_models(self) -> list[str]:
        """
        List all models available locally in Ollama.

        Returns:
            List of model name strings.
        """
        try:
            response = httpx.get(
                f"{self._base_url}/api/tags",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
            return []
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    def get_llm(self) -> Any:
        """Return the underlying LangChain ChatOllama instance."""
        return self._llm

    def get_provider(self) -> LLMProvider:
        """Return the provider type."""
        return LLMProvider.LOCAL

    def get_context_window(self) -> int:
        """Return max context window for the model."""
        for model_prefix, window in self.CONTEXT_WINDOWS.items():
            if model_prefix in self._model.lower():
                return window
        return 4096  # Conservative default for unknown models

    def get_max_output_tokens(self) -> int:
        """Return max output tokens for the model."""
        # Most local models can output up to context window size
        return min(self.get_context_window(), 8192)

    def supports_function_calling(self) -> bool:
        """Some Ollama models support function calling."""
        supported = ["llama3.1", "llama3.2", "llama3.3", "mistral", "mixtral"]
        return any(s in self._model.lower() for s in supported)

    def supports_vision(self) -> bool:
        """Some Ollama models support vision."""
        vision_models = ["llava", "bakllava", "llama3.2-vision"]
        return any(v in self._model.lower() for v in vision_models)

    async def generate(
        self,
        prompt: str,
        settings: GenerationSettings | None = None,
    ) -> LLMResponse:
        """
        Generate from a text prompt using local Ollama model.

        Args:
            prompt: Input prompt string.
            settings: Optional generation settings.

        Returns:
            LLMResponse with content and metadata.

        Raises:
            LLMError: On generation failure.
            ContextLengthError: If prompt too long.
        """
        from langchain_core.messages import HumanMessage

        settings = settings or {}
        messages = [HumanMessage(content=prompt)]

        try:
            response = await self._llm.ainvoke(messages)

            content = response.content if hasattr(response, "content") else str(response)

            # Ollama doesn't always return token counts
            usage = {}
            if hasattr(response, "response_metadata"):
                meta = response.response_metadata
                if "prompt_eval_count" in meta:
                    usage = {
                        "prompt_tokens": meta.get("prompt_eval_count", 0),
                        "completion_tokens": meta.get("eval_count", 0),
                        "total_tokens": meta.get("prompt_eval_count", 0) + meta.get("eval_count", 0),
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

            if "context" in error_str or "too long" in error_str:
                raise ContextLengthError(f"Prompt exceeds model context: {e}") from e

            raise LLMError(
                f"Ollama generation failed (model={self._model}): {e}\n"
                f"Ensure Ollama is running: ollama serve"
            ) from e

    async def generate_stream(
        self,
        prompt: str,
        settings: GenerationSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate with streaming output from local Ollama model.

        Args:
            prompt: Input prompt string.
            settings: Optional generation settings.

        Yields:
            String chunks of the response.

        Raises:
            LLMError: On generation failure.
        """
        from langchain_core.messages import HumanMessage

        settings = settings or {}
        messages = [HumanMessage(content=prompt)]

        try:
            async for chunk in self._llm.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content

        except Exception as e:
            raise LLMError(f"Ollama streaming failed: {e}") from e

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
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

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
            if hasattr(response, "response_metadata"):
                meta = response.response_metadata
                if "prompt_eval_count" in meta:
                    usage = {
                        "prompt_tokens": meta.get("prompt_eval_count", 0),
                        "completion_tokens": meta.get("eval_count", 0),
                        "total_tokens": meta.get("prompt_eval_count", 0) + meta.get("eval_count", 0),
                    }

            return LLMResponse(
                content=content,
                usage=usage,
                model=self._model,
                finish_reason="stop",
                id=None,
            )

        except Exception as e:
            raise LLMError(f"Ollama message generation failed: {e}") from e

    def get_server_info(self) -> dict[str, Any]:
        """
        Get Ollama server information.

        Returns:
            Dict with server version and status.
        """
        try:
            response = httpx.get(f"{self._base_url}/api/version", timeout=5.0)
            if response.status_code == 200:
                return {
                    "running": True,
                    "version": response.json().get("version", "unknown"),
                    "base_url": self._base_url,
                    "model": self._model,
                    "available_models": self.list_local_models(),
                }
        except Exception:
            pass

        return {
            "running": False,
            "base_url": self._base_url,
            "model": self._model,
        }
