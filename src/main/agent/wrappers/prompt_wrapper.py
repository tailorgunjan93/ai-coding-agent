"""
Prompt Wrapper - Prompt templating and validation.

This module provides utilities for managing, rendering, and validating
prompt templates used across the agent framework.
"""

from typing import Any, TypedDict
from abc import ABC, abstractmethod
from enum import Enum

from src.main.agent.exceptions import PromptError


class PromptRole(Enum):
    """Roles in a prompt conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class PromptMessage(TypedDict):
    """A single prompt message."""
    role: PromptRole
    content: str


class PromptTemplate:
    """
    A prompt template with variables and rendering.

    Templates use {variable} syntax for interpolation.
    """

    def __init__(
        self,
        name: str,
        template: str,
        description: str = "",
        required_variables: list[str] | None = None,
    ):
        """
        Initialize a prompt template.

        Args:
            name: Unique name for this template.
            template: Template string with {variable} placeholders.
            description: Human-readable description.
            required_variables: List of required variable names.
        """
        self.name = name
        self.template = template
        self.description = description
        self.required_variables = required_variables or []

    def render(
        self,
        context: dict[str, Any],
        strict: bool = True,
    ) -> str:
        """
        Render the template with context values.

        Args:
            context: Dict of variable name -> value.
            strict: If True, raise on missing required variables.

        Returns:
            Rendered template string.

        Raises:
            PromptError: If required variables are missing.
        """
        if strict:
            missing = [v for v in self.required_variables if v not in context]
            if missing:
                raise PromptError(
                    f"Missing required variables: {missing}",
                    template_name=self.name,
                    details={"missing": missing}
                )

        try:
            return self.template.format(**context)
        except KeyError as e:
            raise PromptError(
                f"Missing variable in template: {e}",
                template_name=self.name,
                details={"error": str(e)}
            )

    def get_variables(self) -> list[str]:
        """Extract variable names from template."""
        import re
        matches = re.findall(r'\{(\w+)\}', self.template)
        return list(set(matches))


class PromptWrapper:
    """
    Manages prompt templates for the agent framework.

    This wrapper provides:
    - Template registration and retrieval
    - Prompt validation
    - Multi-message conversation building
    - Version tracking

    Usage:
        pw = PromptWrapper()
        pw.register("planning", "Plan for {project}...", ["project"])
        rendered = pw.render("planning", {"project": "MyApp"})
    """

    def __init__(self):
        """Initialize the prompt wrapper."""
        self._templates: dict[str, PromptTemplate] = {}
        self._versions: dict[str, int] = {}

    def register(
        self,
        name: str,
        template: str,
        description: str = "",
        required_variables: list[str] | None = None,
        version: int | None = None,
    ) -> PromptTemplate:
        """
        Register a prompt template.

        Args:
            name: Unique name for this template.
            template: Template string with {variable} placeholders.
            description: Human-readable description.
            required_variables: List of required variable names.
            version: Optional version number (auto-increments if not provided).

        Returns:
            The created PromptTemplate.
        """
        if name in self._templates:
            current_version = self._versions.get(name, 1)
            new_version = version or current_version + 1
            self._versions[name] = new_version
            name = f"{name}_v{new_version}"

        tmpl = PromptTemplate(
            name=name,
            template=template,
            description=description,
            required_variables=required_variables,
        )
        self._templates[name] = tmpl
        return tmpl

    def get(self, name: str) -> PromptTemplate | None:
        """
        Get a template by name.

        Args:
            name: Template name.

        Returns:
            PromptTemplate if found, None otherwise.
        """
        return self._templates.get(name)

    def render(
        self,
        name: str,
        context: dict[str, Any],
        strict: bool = True,
    ) -> str:
        """
        Render a template by name.

        Args:
            name: Template name.
            context: Variable values for rendering.
            strict: If True, raise on missing required variables.

        Returns:
            Rendered template string.

        Raises:
            PromptError: If template not found or variables missing.
        """
        tmpl = self.get(name)
        if not tmpl:
            raise PromptError(
                f"Template not found: {name}",
                template_name=name,
            )
        return tmpl.render(context, strict=strict)

    def build_conversation(
        self,
        messages: list[PromptMessage],
        system_template: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """
        Build a conversation dict for LLM consumption.

        Args:
            messages: List of prompt messages.
            system_template: Optional system prompt template.
            context: Context for rendering templates.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        context = context or {}
        result: list[dict[str, str]] = []

        # Add system message if provided
        if system_template:
            tmpl = PromptTemplate(name="_system", template=system_template)
            content = tmpl.render(context, strict=False)
            result.append({"role": "system", "content": content})

        # Add conversation messages
        for msg in messages:
            role = msg["role"].value if isinstance(msg["role"], PromptRole) else msg["role"]
            content = msg["content"]

            # Render if contains variables
            if "{" in content and context:
                try:
                    tmpl = PromptTemplate(name="_temp", template=content)
                    content = tmpl.render(context, strict=False)
                except PromptError:
                    pass  # Keep original content if rendering fails

            result.append({"role": role, "content": content})

        return result

    def list_templates(self) -> list[str]:
        """List all registered template names."""
        return list(self._templates.keys())

    def validate(self, name: str, context: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate that a template can be rendered with context.

        Args:
            name: Template name.
            context: Variable values.

        Returns:
            Tuple of (is_valid, error_message).
        """
        tmpl = self.get(name)
        if not tmpl:
            return False, f"Template not found: {name}"

        try:
            tmpl.render(context, strict=True)
            return True, None
        except PromptError as e:
            return False, str(e)

    def get_metrics(self) -> dict[str, Any]:
        """Get wrapper metrics."""
        return {
            "template_count": len(self._templates),
            "templates": [
                {
                    "name": t.name,
                    "variables": t.get_variables(),
                    "required": t.required_variables,
                }
                for t in self._templates.values()
            ],
            "versions": dict(self._versions),
        }
