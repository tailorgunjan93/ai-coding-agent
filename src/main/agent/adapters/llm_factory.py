"""
LLM Factory - Smart provider auto-detection and adapter creation.

This factory detects available LLM providers (API keys, local servers)
and creates the appropriate adapter. Priority order:
  1. OpenAI (OPENAI_API_KEY)
  2. Anthropic (ANTHROPIC_API_KEY)
  3. Groq (GROQ_API_KEY) — free tier
  4. Google (GOOGLE_API_KEY) — free tier
  5. AWS Bedrock (AWS credentials)
  6. Ollama (localhost:11434) — fully free
"""

from typing import Any
import os
import logging

from src.main.agent.interfaces.llm_interface import LLMInterface, LLMProvider
from src.main.agent.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# Map of provider names to their env var requirements
_PROVIDER_ENV_KEYS = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GROQ: "GROQ_API_KEY",
    LLMProvider.GOOGLE: "GOOGLE_API_KEY",
    LLMProvider.AWS_BEDROCK: "AWS_ACCESS_KEY_ID",  # Also needs AWS_SECRET_ACCESS_KEY
}


def detect_available_providers() -> list[LLMProvider]:
    """
    Detect which LLM providers are available based on environment
    variables and running services.

    Returns:
        List of available LLMProvider values, in priority order.
    """
    available = []

    # Check cloud providers via env vars
    for provider, env_key in _PROVIDER_ENV_KEYS.items():
        if os.getenv(env_key):
            if provider == LLMProvider.AWS_BEDROCK:
                # AWS needs both access key and secret
                if os.getenv("AWS_SECRET_ACCESS_KEY"):
                    available.append(provider)
            else:
                available.append(provider)

    # Check local Ollama server
    try:
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter
        if OllamaAdapter.is_server_running():
            available.append(LLMProvider.LOCAL)
    except ImportError:
        pass

    return available


def get_provider_status() -> dict[str, dict[str, Any]]:
    """
    Get detailed status for all supported providers.

    Returns:
        Dict mapping provider name to status info.
    """
    status = {}

    for provider, env_key in _PROVIDER_ENV_KEYS.items():
        has_key = bool(os.getenv(env_key))
        if provider == LLMProvider.AWS_BEDROCK:
            has_key = has_key and bool(os.getenv("AWS_SECRET_ACCESS_KEY"))

        status[provider.value] = {
            "available": has_key,
            "env_var": env_key,
            "type": "cloud",
        }

    # Ollama status
    ollama_running = False
    ollama_models = []
    try:
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter
        ollama_running = OllamaAdapter.is_server_running()
        if ollama_running:
            temp = OllamaAdapter.__new__(OllamaAdapter)
            temp._base_url = OllamaAdapter.BASE_URL
            ollama_models = temp.list_local_models()
    except ImportError:
        pass

    status["local"] = {
        "available": ollama_running,
        "server_running": ollama_running,
        "models": ollama_models,
        "type": "local",
        "setup": "Install Ollama: https://ollama.ai/download",
    }

    return status


def create_llm_adapter(
    provider: str | None = None,
    model: str | None = None,
    auto_detect: bool = True,
    prefer_local: bool = False,
    **kwargs,
) -> LLMInterface:
    """
    Create an LLM adapter based on available providers.

    Args:
        provider: Force a specific provider ("openai", "anthropic",
                  "groq", "google", "bedrock", "ollama").
        model: Override the default model for the chosen provider.
        auto_detect: Auto-detect the best available provider.
        prefer_local: Prefer Ollama even if cloud keys are available.
        **kwargs: Additional arguments passed to the adapter constructor.

    Returns:
        LLMInterface adapter instance.

    Raises:
        ConfigurationError: If no provider is available.
    """
    # Force specific provider
    if provider:
        return _create_specific_adapter(provider, model, **kwargs)

    # Prefer local if requested
    if prefer_local:
        try:
            return _create_specific_adapter("ollama", model, **kwargs)
        except (ConfigurationError, Exception) as e:
            logger.warning(f"Local LLM not available: {e}. Trying cloud providers...")

    # Auto-detect best available
    if auto_detect:
        available = detect_available_providers()
        if available:
            chosen = available[0]
            logger.info(f"Auto-detected LLM provider: {chosen.value}")
            return _create_specific_adapter(chosen.value, model, **kwargs)

    # Nothing available
    raise ConfigurationError(
        "No LLM provider available. Set up one of the following:\n\n"
        "FREE OPTIONS:\n"
        "  1. Ollama (local, fully free):\n"
        "     - Install: https://ollama.ai/download\n"
        "     - Run: ollama pull deepseek-coder-v2:16b && ollama serve\n\n"
        "  2. Groq (cloud, free tier - 30 req/min):\n"
        "     - Get key: https://console.groq.com/keys\n"
        "     - Set: GROQ_API_KEY=your-key\n\n"
        "  3. Google Gemini (cloud, free tier - 15 req/min):\n"
        "     - Get key: https://aistudio.google.com/apikey\n"
        "     - Set: GOOGLE_API_KEY=your-key\n\n"
        "PAID OPTIONS:\n"
        "  4. OpenAI: Set OPENAI_API_KEY\n"
        "  5. Anthropic: Set ANTHROPIC_API_KEY\n"
        "  6. AWS Bedrock: Set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY"
    )


def _create_specific_adapter(
    provider: str,
    model: str | None = None,
    **kwargs,
) -> LLMInterface:
    """
    Create an adapter for a specific provider.

    Args:
        provider: Provider name string.
        model: Optional model override.
        **kwargs: Additional adapter arguments.

    Returns:
        LLMInterface adapter instance.

    Raises:
        ConfigurationError: If provider is unknown or unavailable.
    """
    provider_lower = provider.lower().strip()

    if provider_lower == "openai":
        from src.main.agent.adapters.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(model=model or OpenAIAdapter.DEFAULT_MODEL, **kwargs)

    elif provider_lower == "anthropic":
        from src.main.agent.adapters.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(model=model or AnthropicAdapter.DEFAULT_MODEL, **kwargs)

    elif provider_lower == "groq":
        from src.main.agent.adapters.groq_adapter import GroqAdapter
        return GroqAdapter(model=model or GroqAdapter.DEFAULT_MODEL, **kwargs)

    elif provider_lower == "google":
        from src.main.agent.adapters.google_adapter import GoogleAdapter
        return GoogleAdapter(model=model or GoogleAdapter.DEFAULT_MODEL, **kwargs)

    elif provider_lower in ("bedrock", "aws_bedrock", "aws"):
        from src.main.agent.adapters.bedrock_adapter import BedrockAdapter
        return BedrockAdapter(model=model or BedrockAdapter.DEFAULT_MODEL, **kwargs)

    elif provider_lower in ("ollama", "local"):
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter
        if not OllamaAdapter.is_server_running():
            raise ConfigurationError(
                "Ollama server is not running.\n"
                "Start it with: ollama serve\n"
                "Install from: https://ollama.ai/download"
            )
        return OllamaAdapter(model=model, **kwargs)

    else:
        raise ConfigurationError(
            f"Unknown provider: '{provider}'. "
            f"Supported: openai, anthropic, groq, google, bedrock, ollama"
        )
