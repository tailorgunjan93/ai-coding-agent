"""
LLM Wrapper - Adds caching, rate limiting, and fallback to LLMInterface.

This wrapper composes over any LLMInterface adapter to add:
  - Response caching with TTL
  - Rate limiting (requests per minute)
  - Automatic fallback to secondary provider on failure
"""

from typing import Any, AsyncIterator
from datetime import datetime, timedelta
import hashlib
import logging

from src.main.agent.interfaces.llm_interface import (
    LLMInterface,
    LLMResponse,
)

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

    Features:
        - Response caching with configurable TTL
        - Rate limiting (RPM-based)
        - Automatic fallback to secondary provider on failure
        - Provider switch logging for observability

    Usage:
        primary = OpenAIAdapter(model="gpt-4")
        fallback = OllamaAdapter(model="deepseek-coder-v2:16b")
        wrapper = LLMWrapper(primary=primary, fallback=fallback)
        response = await wrapper.generate("Write a Python class")
    """

    def __init__(
        self,
        primary: LLMInterface,
        fallback: LLMInterface | None = None,
        cache_ttl_seconds: int = 300,
        rate_limit_rpm: int = 60,
    ):
        """
        Initialize the LLM wrapper.

        Args:
            primary: Primary LLM adapter.
            fallback: Optional fallback adapter (e.g., local Ollama
                      when cloud provider fails).
            cache_ttl_seconds: Cache time-to-live in seconds.
            rate_limit_rpm: Max requests per minute.
        """
        self._primary = primary
        self._fallback = fallback
        self._cache: dict[str, CacheEntry] = {}
        self._cache_ttl = cache_ttl_seconds
        self._rate_limit_rpm = rate_limit_rpm
        self._request_timestamps: list[datetime] = []
        self._active_provider: str = "primary"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate with caching, rate limiting, and fallback."""
        self._check_rate_limit()

        cache_key = self._make_cache_key(prompt, **kwargs)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Try primary provider
        try:
            response = await self._primary.generate(prompt, **kwargs)
            self._active_provider = "primary"
            self._cache_response(cache_key, response)
            return response

        except Exception as primary_error:
            if self._fallback is None:
                raise

            # Fallback to secondary provider
            logger.warning(
                f"Primary LLM failed ({primary_error}), "
                f"falling back to secondary provider..."
            )
            try:
                response = await self._fallback.generate(prompt, **kwargs)
                self._active_provider = "fallback"
                self._cache_response(cache_key, response)
                logger.info("Fallback provider succeeded")
                return response

            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                # Raise the original primary error
                raise primary_error from fallback_error

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Generate with streaming, using fallback on failure."""
        self._check_rate_limit()

        try:
            async for chunk in self._primary.generate_stream(prompt, **kwargs):
                yield chunk
            self._active_provider = "primary"

        except Exception as primary_error:
            if self._fallback is None:
                raise

            logger.warning(
                f"Primary stream failed ({primary_error}), "
                f"falling back to secondary provider..."
            )
            try:
                async for chunk in self._fallback.generate_stream(prompt, **kwargs):
                    yield chunk
                self._active_provider = "fallback"
            except Exception:
                raise primary_error

    async def generate_with_messages(
        self,
        messages: list[dict[str, Any]],
        **kwargs,
    ) -> LLMResponse:
        """Generate from message history with fallback."""
        self._check_rate_limit()

        try:
            response = await self._primary.generate_with_messages(messages, **kwargs)
            self._active_provider = "primary"
            return response

        except Exception as primary_error:
            if self._fallback is None:
                raise

            logger.warning(
                f"Primary message generation failed ({primary_error}), "
                f"falling back..."
            )
            try:
                response = await self._fallback.generate_with_messages(messages, **kwargs)
                self._active_provider = "fallback"
                return response
            except Exception:
                raise primary_error

    def get_active_provider(self) -> str:
        """Return which provider is currently active ('primary' or 'fallback')."""
        return self._active_provider

    def _check_rate_limit(self) -> None:
        """Check if rate limit is exceeded."""
        now = datetime.now()
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if now - ts < timedelta(minutes=1)
        ]

        if len(self._request_timestamps) >= self._rate_limit_rpm:
            raise Exception(f"Rate limit of {self._rate_limit_rpm} rpm exceeded")

        self._request_timestamps.append(now)

    def _make_cache_key(self, prompt: str, **kwargs) -> str:
        """Create a cache key."""
        combined = f"{prompt}:{str(sorted(kwargs.items()))}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _get_cached(self, key: str) -> LLMResponse | None:
        """Get cached response."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.response
        return None

    def _cache_response(self, key: str, response: LLMResponse) -> None:
        """Cache a response."""
        self._cache[key] = CacheEntry(response, self._cache_ttl)

    def get_llm(self) -> Any:
        """Expose the underlying LLM."""
        return self._primary.get_llm()
