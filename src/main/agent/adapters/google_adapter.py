"""
Google Gemini LLM Adapter - Cloud inference using Google's Gemini models.

Free tier: 15 req/min, 1M tokens/day. 1M token context window.
Requires GOOGLE_API_KEY. Get a free key at: https://aistudio.google.com/apikey
"""

from typing import Any, AsyncIterator
import os
import logging

from src.main.agent.interfaces.llm_interface import (
    LLMInterface, LLMProvider, GenerationSettings, LLMResponse,
)
from src.main.agent.exceptions import LLMError, RateLimitError, ContextLengthError

logger = logging.getLogger(__name__)


class GoogleAdapter(LLMInterface):
    """Google Gemini adapter using langchain-google-genai."""

    DEFAULT_MODEL = "gemini-2.0-flash"

    MODELS = {
        "gemini-2.0-flash": 1048576,
        "gemini-2.0-flash-lite": 1048576,
        "gemini-1.5-pro": 2097152,
        "gemini-1.5-flash": 1048576,
        "gemini-1.5-flash-8b": 1048576,
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
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._max_retries = max_retries
        self._timeout = timeout
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(
                model=self._model,
                temperature=self._temperature,
                google_api_key=self._api_key,
                max_retries=self._max_retries,
                timeout=self._timeout,
            )
        except ImportError:
            raise LLMError("langchain-google-genai not installed. Run: pip install langchain-google-genai")

    def get_llm(self) -> Any:
        return self._llm

    def get_provider(self) -> LLMProvider:
        return LLMProvider.GOOGLE

    def get_context_window(self) -> int:
        return self.MODELS.get(self._model, 1048576)

    def get_max_output_tokens(self) -> int:
        return 8192

    def supports_function_calling(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return True

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
            if "rate" in err or "429" in err or "quota" in err:
                raise RateLimitError(f"Google API rate limit exceeded: {e}") from e
            if "context" in err or "maximum" in err or "too long" in err:
                raise ContextLengthError(f"Prompt exceeds context window: {e}") from e
            raise LLMError(f"Google Gemini generation failed: {e}") from e

    async def generate_stream(self, prompt: str, settings: GenerationSettings | None = None) -> AsyncIterator[str]:
        from langchain_core.messages import HumanMessage
        try:
            async for chunk in self._llm.astream([HumanMessage(content=prompt)]):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            raise LLMError(f"Google Gemini streaming failed: {e}") from e

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
            if "rate" in err or "429" in err or "quota" in err:
                raise RateLimitError(f"Google API rate limit: {e}") from e
            raise LLMError(f"Google Gemini message generation failed: {e}") from e
