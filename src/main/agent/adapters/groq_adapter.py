"""
Groq LLM Adapter - Cloud inference using Groq's LPU hardware.

Groq offers a generous free tier (30 req/min, 6000 tokens/min).
Requires GROQ_API_KEY. Get a free key at: https://console.groq.com/keys
"""

from typing import Any, AsyncIterator
import os
import logging

from src.main.agent.interfaces.llm_interface import (
    LLMInterface, LLMProvider, GenerationSettings, LLMResponse,
)
from src.main.agent.exceptions import LLMError, RateLimitError, ContextLengthError

logger = logging.getLogger(__name__)


class GroqAdapter(LLMInterface):
    """Groq cloud adapter for ultra-fast LLM inference via LPU hardware."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    MODELS = {
        "llama-3.3-70b-versatile": 128000,
        "llama-3.1-70b-versatile": 128000,
        "llama-3.1-8b-instant": 128000,
        "llama3-70b-8192": 8192,
        "llama3-8b-8192": 8192,
        "mixtral-8x7b-32768": 32768,
        "gemma2-9b-it": 8192,
    }

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        api_key: str | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        self._model = model
        self._temperature = temperature
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._max_retries = max_retries
        self._timeout = timeout
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        try:
            from langchain_groq import ChatGroq
            self._llm = ChatGroq(
                model=self._model, temperature=self._temperature,
                api_key=self._api_key, max_retries=self._max_retries,
                timeout=self._timeout,
            )
        except ImportError:
            raise LLMError("langchain-groq not installed. Run: pip install langchain-groq")

    def get_llm(self) -> Any:
        return self._llm

    def get_provider(self) -> LLMProvider:
        return LLMProvider.GROQ

    def get_context_window(self) -> int:
        return self.MODELS.get(self._model, 8192)

    def get_max_output_tokens(self) -> int:
        return 8192

    def supports_function_calling(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return False

    async def generate(self, prompt: str, settings: GenerationSettings | None = None) -> LLMResponse:
        from langchain_core.messages import HumanMessage
        settings = settings or {}
        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content if hasattr(response, "content") else str(response)
            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
                    "completion_tokens": response.usage_metadata.get("output_tokens", 0),
                    "total_tokens": response.usage_metadata.get("total_tokens", 0),
                }
            return LLMResponse(content=content, usage=usage, model=self._model, finish_reason="stop", id=getattr(response, "id", None))
        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "429" in err or "limit" in err:
                raise RateLimitError(f"Groq rate limit exceeded (free tier: 30 req/min): {e}") from e
            if "context" in err or "maximum" in err or "too long" in err:
                raise ContextLengthError(f"Prompt exceeds context window: {e}") from e
            raise LLMError(f"Groq generation failed: {e}") from e

    async def generate_stream(self, prompt: str, settings: GenerationSettings | None = None) -> AsyncIterator[str]:
        from langchain_core.messages import HumanMessage
        try:
            async for chunk in self._llm.astream([HumanMessage(content=prompt)]):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            raise LLMError(f"Groq streaming failed: {e}") from e

    async def generate_with_messages(self, messages: list[dict[str, Any]], settings: GenerationSettings | None = None) -> LLMResponse:
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        lc_messages = []
        for msg in messages:
            role, content = msg.get("role", "user"), msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        try:
            response = await self._llm.ainvoke(lc_messages)
            content = response.content if hasattr(response, "content") else str(response)
            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
                    "completion_tokens": response.usage_metadata.get("output_tokens", 0),
                    "total_tokens": response.usage_metadata.get("total_tokens", 0),
                }
            return LLMResponse(content=content, usage=usage, model=self._model, finish_reason="stop", id=getattr(response, "id", None))
        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "429" in err:
                raise RateLimitError(f"Groq rate limit: {e}") from e
            raise LLMError(f"Groq message generation failed: {e}") from e
