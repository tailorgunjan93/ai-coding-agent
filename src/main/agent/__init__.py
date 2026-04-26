"""AI Coding Agent framework."""

from src.main.agent.agent import Agent, run_agent, get_default_agent
from src.main.agent.graph_builder import GraphBuilder, build_agent_graph
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

__version__ = "0.1.0"

__all__ = [
    # Core
    "Agent",
    "run_agent",
    "get_default_agent",
    "GraphBuilder",
    "build_agent_graph",
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
