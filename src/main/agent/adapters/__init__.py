"""Adapters package - Concrete implementations of interfaces."""

from src.main.agent.adapters.openai_adapter import OpenAIAdapter
from src.main.agent.adapters.anthropic_adapter import AnthropicAdapter
from src.main.agent.adapters.ollama_adapter import OllamaAdapter
from src.main.agent.adapters.groq_adapter import GroqAdapter
from src.main.agent.adapters.google_adapter import GoogleAdapter
from src.main.agent.adapters.bedrock_adapter import BedrockAdapter
from src.main.agent.adapters.sqlite_adapter import SQLiteAdapter
from src.main.agent.adapters.git_adapter import GitAdapter
from src.main.agent.adapters.llm_factory import (
    create_llm_adapter,
    detect_available_providers,
    get_provider_status,
)

__all__ = [
    # LLM Adapters
    "OpenAIAdapter",
    "AnthropicAdapter",
    "OllamaAdapter",
    "GroqAdapter",
    "GoogleAdapter",
    "BedrockAdapter",
    # Non-LLM Adapters
    "SQLiteAdapter",
    "GitAdapter",
    # Factory
    "create_llm_adapter",
    "detect_available_providers",
    "get_provider_status",
]
