"""
Exception hierarchy for the AI Coding Agent framework.

All framework exceptions inherit from AgentException.
This hierarchy enables granular error handling and debugging.
"""

from abc import ABC


class AgentException(ABC, Exception):
    """Base exception for all agent errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AgentException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, details)


class ConnectionError(AgentException):
    """Raised when connection to external service fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, details)


class LLMError(AgentException):
    """Raised when LLM generation or interaction fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, details)


class RateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.retry_after = retry_after


class ContextLengthError(LLMError):
    """Raised when prompt exceeds model's context window."""

    def __init__(self, message: str, context_window: int | None = None, prompt_length: int | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.context_window = context_window
        self.prompt_length = prompt_length


class ValidationError(AgentException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, value: any = None, details: dict | None = None):
        super().__init__(message, details)
        self.field = field
        self.value = value


class NodeExecutionError(AgentException):
    """Raised when a node fails during execution."""

    def __init__(self, message: str, node_name: str | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.node_name = node_name


class RetryableError(NodeExecutionError):
    """Raised when a node fails but should be retried."""

    def __init__(self, message: str, node_name: str | None = None, retry_count: int = 0, details: dict | None = None):
        super().__init__(message, node_name, details)
        self.retry_count = retry_count


class SecurityError(AgentException):
    """Raised when a security violation is detected."""

    def __init__(self, message: str, violation_type: str | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.violation_type = violation_type


class PermissionError(SecurityError):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str, required_permission: str | None = None, details: dict | None = None):
        super().__init__(message, "permission_denied", details)
        self.required_permission = required_permission


class QueryError(AgentException):
    """Raised when database query execution fails."""

    def __init__(self, message: str, query: str | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.query = query


class PromptError(AgentException):
    """Raised when prompt rendering or validation fails."""

    def __init__(self, message: str, template_name: str | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.template_name = template_name
