"""AI Coding Agent framework."""

__version__ = "0.1.0"

# Lazy loading or just exposing exceptions which have no dependencies
from src.main.agent.exceptions import (
    AgentException,
    ConfigurationError,
    ConnectionError,
    LLMError,
    RateLimitError,
    ContextLengthError,
    ValidationError,
    NodeExecutionError,
    RetryableError,
    SecurityError,
    PermissionError,
    QueryError,
    PromptError,
)

__all__ = [
    # Exceptions
    "AgentException",
    "ConfigurationError",
    "ConnectionError",
    "LLMError",
    "RateLimitError",
    "ContextLengthError",
    "ValidationError",
    "NodeExecutionError",
    "RetryableError",
    "SecurityError",
    "PermissionError",
    "QueryError",
    "PromptError",
]

