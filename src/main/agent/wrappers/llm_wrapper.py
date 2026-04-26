"""
LLM Wrapper - Composition wrapper adding caching, rate-limiting, and fallback.

This wrapper uses composition (not inheritance) to add orthogonal concerns
to any LLMInterface implementation without modifying it.
"""

from typing import Any, AsyncIterator, Dict, List, Optional, Union
from datetime import datetime, timedelta
import hashlib
import asyncio
import logging

from langchain_core.language_models import BaseLanguageModel
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import LLMResult, Generation
from langchain_core.prompts import BasePromptTemplate

from src.main.agent.interfaces.llm_interface import (
    LLMInterface,
    LLMProvider,
    GenerationSettings,
    LLMResponse,
)
from src.main.agent.exceptions import RateLimitError, LLMError

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cached LLM response with TTL."""

    def __init__(self, response: LLMResponse, ttl_seconds: int = 300):
        self.response = response
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class LLMWrapper:
    """
    Wrapper that adds caching, rate limiting, and fallback to LLMInterface.

    This wrapper uses composition to add orthogonal concerns:
    - Caching: Avoid duplicate LLM calls for identical prompts
    - Rate limiting: Prevent exceeding provider limits
    - Fallback: Seamlessly switch to backup provider on failure
    - LangChain integration: Wrap LangChain LLMs for seamless usage

    Usage:
        llm = OpenAIAdapter(api_key="...")
        wrapped = LLMWrapper(llm, fallback=AnthropicAdapter(...))
        response = await wrapped.generate("Hello")
    """

    def __init__(
        self,
        primary: LLMInterface,
        fallback: LLMInterface | None = None,
        cache_ttl_seconds: int = 300,
        rate_limit_rpm: int = 60,
        rate_limit_window_seconds: int = 60,
        enable_langchain_integration: bool = True,
    ):
        """
        Initialize the LLM wrapper.

        Args:
            primary: The primary LLM interface to wrap.
            fallback: Optional fallback LLM for when primary fails.
            cache_ttl_seconds: How long to cache responses (default 5 min).
            rate_limit_rpm: Max requests per minute (default 60).
            rate_limit_window_seconds: Rate limit window (default 60s).
            enable_langchain_integration: Enable LangChain LLM wrapping.
        """
        self._primary = primary
        self._fallback = fallback
        self._cache: dict[str, CacheEntry] = {}
        self._cache_ttl = cache_ttl_seconds
        self._rate_limit_rpm = rate_limit_rpm
        self._rate_limit_window = timedelta(seconds=rate_limit_window_seconds)
        self._request_timestamps: list[datetime] = []
        self._enable_langchain_integration = enable_langchain_integration
        self._langchain_llm: Optional[BaseLanguageModel] = None
        
        if enable_langchain_integration:
            self._setup_langchain_integration()

    def _setup_langchain_integration(self) -> None:
        """Setup LangChain integration by creating a LangChain-compatible LLM."""
        try:
            # Create a LangChain LLM that delegates to our LLMInterface
            from langchain_core.language_models.llms import LLM
            from langchain_core.callbacks.manager import CallbackManagerForLLMRun
            from langchain_core.outputs import Generation
            
            class LangChainAdapter(LLM):
                """Adapter to make LLMInterface compatible with LangChain."""
                
                llm_interface: LLMInterface
                
                @property
                def _llm_type(self) -> str:
                    return f"ai-coding-agent-{self.llm_interface.get_provider().value}"
                
                def _call(
                    self,
                    prompt: str,
                    stop: Optional[List[str]] = None,
                    run_manager: Optional[CallbackManagerForLLMRun] = None,
                    **kwargs: Any,
                ) -> str:
                    # This is a sync call - in practice, we'd need to handle async properly
                    # For now, we'll raise NotImplementedError and rely on async methods
                    raise NotImplementedError("Use async methods instead")
                
                async def _acall(
                    self,
                    prompt: str,
                    stop: Optional[List[str]] = None,
                    run_manager: Optional[CallbackManagerForLLMRun] = None,
                    **kwargs: Any,
                ) -> str:
                    """Async call to the LLM interface."""
                    settings = GenerationSettings(
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens"),
                        top_p=kwargs.get("top_p"),
                        stop_sequences=stop,
                    )
                    
                    response = await self.llm_interface.generate(prompt, settings)
                    return response["content"]
            
            self._langchain_llm = LangChainAdapter(llm_interface=self._primary)
            logger.info("LangChain integration enabled")
        except ImportError:
            logger.warning("LangChain not available, skipping LangChain integration")
            self._enable_langchain_integration = False

    async def generate(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> LLMResponse:
        """
        Generate with caching, rate limiting, and fallback.

        Args:
            prompt: Input prompt.
            settings: Generation settings.

        Returns:
            LLMResponse from the LLM.

        Raises:
            RateLimitError: When rate limit is exceeded.
            LLMError: When all providers fail.
        """
        self._check_rate_limit()

        cache_key = self._make_cache_key(prompt, settings)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            response = await self._primary.generate(prompt, settings)
            self._cache_response(cache_key, response)
            return response
        except Exception as primary_error:
            if self._fallback:
                try:
                    response = await self._fallback.generate(prompt, settings)
                    self._cache_response(cache_key, response)
                    return response
                except Exception:
                    raise LLMError(
                        f"Both primary and fallback LLM failed. Primary: {primary_error}",
                        details={"primary_error": str(primary_error)}
                    ) from primary_error
            raise LLMError(
                f"Primary LLM failed: {primary_error}",
                details={"error": str(primary_error)}
            ) from primary_error

    async def generate_stream(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> AsyncIterator[str]:
        """
        Generate streaming with rate limiting and fallback.

        Note: Streaming responses are not cached.

        Args:
            prompt: Input prompt.
            settings: Generation settings.

        Yields:
            String chunks of the response.

        Raises:
            RateLimitError: When rate limit is exceeded.
            LLMError: When all providers fail.
        """
        self._check_rate_limit()

        try:
            async for chunk in self._primary.generate_stream(prompt, settings):
                yield chunk
        except Exception as primary_error:
            if self._fallback:
                try:
                    async for chunk in self._fallback.generate_stream(prompt, settings):
                        yield chunk
                    return
                except Exception:
                    raise LLMError(
                        f"Both primary and fallback LLM failed: {primary_error}",
                    ) from primary_error
            raise LLMError(
                f"Primary LLM failed: {primary_error}",
            ) from primary_error

    def _check_rate_limit(self) -> None:
        """Check if rate limit is exceeded and raise if so."""
        now = datetime.now()

        # Clean old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if now - ts < self._rate_limit_window
        ]

        if len(self._request_timestamps) >= self._rate_limit_rpm:
            raise RateLimitError(
                f"Rate limit of {self._rate_limit_rpm} requests/minute exceeded",
                retry_after=60,
                details={"retry_after_seconds": 60}
            )

        self._request_timestamps.append(now)

    def _make_cache_key(
        self,
        prompt: str,
        settings: GenerationSettings | None
    ) -> str:
        """Create a cache key from prompt and settings."""
        settings_str = str(sorted((settings or {}).items()))
        combined = f"{prompt}:{settings_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _get_cached(self, key: str) -> LLMResponse | None:
        """Get cached response if valid."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.response
        elif entry:
            # Clean up expired entry
            del self._cache[key]
        return None

    def _cache_response(self, key: str, response: LLMResponse) -> None:
        """Cache a response with TTL."""
        self._cache[key] = CacheEntry(response, self._cache_ttl)

    def get_provider(self) -> LLMProvider:
        """Delegate to primary LLM."""
        return self._primary.get_provider()

    def get_langchain_llm(self) -> Optional[BaseLanguageModel]:
        """
        Get the LangChain-compatible LLM if integration is enabled.
        
        Returns:
            LangChain LLM instance or None if integration disabled.
        """
        if self._enable_langchain_integration:
            return self._langchain_llm
        return None

    def get_metrics(self) -> dict[str, Any]:
        """Get wrapper metrics for monitoring."""
        return {
            "cache_size": len(self._cache),
            "cache_expired": sum(
                1 for e in self._cache.values() if e.is_expired()
            ),
            "requests_last_minute": len(self._request_timestamps),
            "primary_provider": self._primary.get_provider().value,
            "fallback_provider": (
                self._fallback.get_provider().value if self._fallback else None
            ),
            "rate_limit_rpm": self._rate_limit_rpm,
            "langchain_integration_enabled": self._enable_langchain_integration,
        }

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()

    def get_cached_response(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> LLMResponse | None:
        """Check if a prompt is cached without side effects."""
        key = self._make_cache_key(prompt, settings)
        return self._get_cached(key)
