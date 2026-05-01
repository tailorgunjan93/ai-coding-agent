"""
AWS Bedrock LLM Adapter - Enterprise-grade cloud inference via AWS Bedrock.

Supports Claude, Llama, Titan, Mistral models through AWS infrastructure.
Requires AWS credentials: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION.
"""

from typing import Any, AsyncIterator
import os
import logging

from src.main.agent.interfaces.llm_interface import (
    LLMInterface, LLMProvider, GenerationSettings, LLMResponse,
)
from src.main.agent.exceptions import LLMError, RateLimitError, ContextLengthError

logger = logging.getLogger(__name__)


class BedrockAdapter(LLMInterface):
    """AWS Bedrock adapter for enterprise LLM inference."""

    DEFAULT_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"

    MODELS = {
        "anthropic.claude-3-sonnet-20240229-v1:0": 200000,
        "anthropic.claude-3-haiku-20240307-v1:0": 200000,
        "anthropic.claude-3-opus-20240229-v1:0": 200000,
        "meta.llama3-1-70b-instruct-v1:0": 128000,
        "meta.llama3-1-8b-instruct-v1:0": 128000,
        "amazon.titan-text-express-v1": 8192,
        "mistral.mistral-7b-instruct-v0:2": 32768,
        "mistral.mixtral-8x7b-instruct-v0:1": 32768,
    }

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        region: str | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        self._model = model
        self._temperature = temperature
        self._region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self._max_retries = max_retries
        self._timeout = timeout
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        try:
            from langchain_aws import ChatBedrock
            self._llm = ChatBedrock(
                model_id=self._model,
                model_kwargs={"temperature": self._temperature},
                region_name=self._region,
            )
        except ImportError:
            raise LLMError("langchain-aws not installed. Run: pip install langchain-aws")

    @staticmethod
    def has_credentials() -> bool:
        """Check if AWS credentials are configured."""
        return bool(
            os.getenv("AWS_ACCESS_KEY_ID")
            and os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def get_llm(self) -> Any:
        return self._llm

    def get_provider(self) -> LLMProvider:
        return LLMProvider.AWS_BEDROCK

    def get_context_window(self) -> int:
        return self.MODELS.get(self._model, 8192)

    def get_max_output_tokens(self) -> int:
        if "claude" in self._model:
            return 8192
        return 4096

    def supports_function_calling(self) -> bool:
        return "claude" in self._model or "mistral" in self._model

    def supports_vision(self) -> bool:
        return "claude-3" in self._model

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
            if "throttl" in err or "429" in err or "rate" in err:
                raise RateLimitError(f"AWS Bedrock rate limit exceeded: {e}") from e
            if "context" in err or "maximum" in err or "too long" in err:
                raise ContextLengthError(f"Prompt exceeds context window: {e}") from e
            raise LLMError(f"AWS Bedrock generation failed: {e}") from e

    async def generate_stream(self, prompt: str, settings: GenerationSettings | None = None) -> AsyncIterator[str]:
        from langchain_core.messages import HumanMessage
        try:
            async for chunk in self._llm.astream([HumanMessage(content=prompt)]):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            raise LLMError(f"AWS Bedrock streaming failed: {e}") from e

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
            if "throttl" in err or "429" in err:
                raise RateLimitError(f"AWS Bedrock rate limit: {e}") from e
            raise LLMError(f"AWS Bedrock message generation failed: {e}") from e
