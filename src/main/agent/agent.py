"""
Agent - Main entry point for the AI Coding Agent.

This module provides the Agent class that orchestrates the entire
workflow using LangGraph.
"""

from typing import Any, TypedDict
import uuid
import logging

from src.main.agent.graph_builder import GraphBuilder, build_agent_graph
from src.main.agent.models.agent_state import AgentState, create_initial_state
from src.main.agent.wrappers import LLMWrapper, PromptWrapper
from src.main.agent.interfaces.node_interface import NodeExecutionContext

logger = logging.getLogger(__name__)


class AgentConfig(TypedDict):
    """Configuration for the agent."""
    session_id: str | None
    user_id: str | None
    debug: bool


class Agent:
    """
    Main AI Coding Agent orchestrator.

    This class:
    - Initializes and manages the LangGraph workflow
    - Handles session state
    - Provides a simple interface for invoking the agent
    - Manages node dependencies and execution

    Usage:
        agent = Agent()
        result = await agent.run(
            request="Create a REST API for a todo app",
            request_type="generate"
        )
    """

    def __init__(
        self,
        llm_wrapper: LLMWrapper | None = None,
        prompt_wrapper: PromptWrapper | None = None,
        config: AgentConfig | None = None,
    ):
        """
        Initialize the agent.

        Args:
            llm_wrapper: Optional LLMWrapper for LLM access.
            prompt_wrapper: Optional PromptWrapper for prompts.
            config: Optional agent configuration.
        """
        self._llm = llm_wrapper
        self._prompts = prompt_wrapper or PromptWrapper()
        self._config = config or AgentConfig(
            session_id=None,
            user_id=None,
            debug=False,
        )
        self._graph = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the agent and build the graph."""
        if self._initialized:
            return

        builder = GraphBuilder(debug=self._config.get("debug", False))
        self._graph = builder.build()
        self._initialized = True

        logger.info("Agent initialized successfully")

    async def run(
        self,
        request: str,
        request_type: str = "generate",
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run the agent with a user request.

        Args:
            request: The user's request string.
            request_type: Type of request (generate, enhance, fix, debug).
            session_id: Optional session ID (generated if not provided).
            user_id: Optional user ID.

        Returns:
            Dict with execution results and state.
        """
        self.initialize()

        # Generate or use provided session ID
        session_id = session_id or str(uuid.uuid4())
        user_id = user_id or self._config.get("user_id", "anonymous")

        # Create initial state
        state = create_initial_state(
            session_id=session_id,
            user_id=user_id,
            original_request=request,
            request_type=request_type,
        )

        # Create execution context
        context = NodeExecutionContext(
            node_id="root",
            attempt=1,
            max_attempts=1,
            timeout_seconds=3600,
            session_id=session_id,
        )

        try:
            # Run the graph
            logger.info(f"Starting agent run for session {session_id}")
            result = await self._graph.ainvoke(state, config={"configurable": {"thread_id": session_id}})

            logger.info(f"Agent run completed for session {session_id}")
            return {
                "success": result.get("success", False),
                "session_id": session_id,
                "state": result,
                "output": result.get("output_node_output"),
            }

        except Exception as e:
            logger.error(f"Agent run failed for session {session_id}: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
            }

    async def run_stream(
        self,
        request: str,
        request_type: str = "generate",
        session_id: str | None = None,
        user_id: str | None = None,
    ):
        """
        Run the agent with streaming output.

        Args:
            request: The user's request string.
            request_type: Type of request.
            session_id: Optional session ID.
            user_id: Optional user ID.

        Yields:
            Streaming updates from the graph.
        """
        self.initialize()

        session_id = session_id or str(uuid.uuid4())
        user_id = user_id or self._config.get("user_id", "anonymous")

        state = create_initial_state(
            session_id=session_id,
            user_id=user_id,
            original_request=request,
            request_type=request_type,
        )

        try:
            async for event in self._graph.astream(state, config={"configurable": {"thread_id": session_id}}):
                yield event

        except Exception as e:
            logger.error(f"Agent stream failed for session {session_id}: {e}")
            yield {"error": str(e)}

    def get_graph(self) -> Any:
        """Get the compiled graph for inspection."""
        self.initialize()
        return self._graph

    def get_node_metrics(self) -> dict[str, Any]:
        """Get metrics from all nodes."""
        if not self._initialized:
            return {}

        metrics = {}
        builder = GraphBuilder()
        # Note: In production, would track actual node instances

        return metrics


# Convenience function for simple usage
_default_agent: Agent | None = None


def get_default_agent() -> Agent:
    """Get or create the default agent instance."""
    global _default_agent
    if _default_agent is None:
        _default_agent = Agent()
    return _default_agent


async def run_agent(
    request: str,
    request_type: str = "generate",
    **kwargs,
) -> dict[str, Any]:
    """
    Convenience function to run the default agent.

    Args:
        request: User request.
        request_type: Type of request.
        **kwargs: Additional arguments passed to Agent.run.

    Returns:
        Agent execution results.
    """
    agent = get_default_agent()
    return await agent.run(request, request_type=request_type, **kwargs)
