"""
Graph Builder - Constructs the LangGraph state machine.

This module defines how nodes are connected in the workflow,
including conditional edges and parallel execution paths.
"""

from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

from src.main.agent.models.agent_state import AgentState
from src.main.agent.nodes import (
    PlanningNode,
    HumanApprovalNode,
    ModelNode,
    SecurityNode,
    TesterNode,
    DBNode,
    GitNode,
    CICDNode,
    OutputNode,
    DesignPatternNode,
    LifecycleNode,
)


class GraphBuilder:
    """
    Builds the LangGraph state graph for the AI Coding Agent.

    This class:
    - Defines all nodes and their connections
    - Sets up conditional routing
    - Configures parallel execution paths
    - Compiles the graph with checkpointer

    Usage:
        builder = GraphBuilder()
        graph = builder.build()
        result = await graph.ainvoke(initial_state)
    """

    def __init__(
        self,
        checkpointer: Any | None = None,
        debug: bool = False,
    ):
        """
        Initialize the graph builder.

        Args:
            checkpointer: LangGraph checkpointer for state persistence.
            debug: Enable debug mode for graph visualization.
        """
        self._checkpointer = checkpointer or MemorySaver()
        self._debug = debug
        self._nodes: dict[str, Any] = {}
        self._graph: StateGraph | None = None

    def build(self) -> Any:
        """
        Build and compile the LangGraph state graph.

        Returns:
            Compiled LangGraph application.
        """
        self._graph = StateGraph(AgentState)

        # Register all nodes
        self._add_nodes()

        # Define edges
        self._add_edges()

        # Define conditional routing
        self._add_conditional_edges()

        # Set entry point
        self._graph.set_entry_point("planning")

        # Compile with checkpointer
        compiled = self._graph.compile(checkpointer=self._checkpointer)

        if self._debug:
            # Print graph structure for debugging
            print("Graph compiled successfully")
            print(f"Nodes: {list(self._nodes.keys())}")

        return compiled

    def _add_nodes(self) -> None:
        """Register all nodes in the graph."""
        # Note: In production, these would be initialized with actual dependencies
        # For now, using placeholder initialization

        self._nodes["planning"] = PlanningNode(
            llm_wrapper=None,  # Would be injected
            prompt_wrapper=None,
        )

        self._nodes["human_approval"] = HumanApprovalNode()

        self._nodes["model"] = ModelNode(
            llm_wrapper=None,
            prompt_wrapper=None,
        )

        self._nodes["security"] = SecurityNode()

        self._nodes["tester"] = TesterNode(
            llm_wrapper=None,
            prompt_wrapper=None,
        )

        self._nodes["db"] = DBNode()

        self._nodes["design_pattern"] = DesignPatternNode()

        self._nodes["lifecycle"] = LifecycleNode()

        self._nodes["git"] = GitNode()

        self._nodes["cicd"] = CICDNode()

        self._nodes["output"] = OutputNode()

        # Add all nodes to graph
        for name, node in self._nodes.items():
            self._graph.add_node(name, node.execute)

    def _add_edges(self) -> None:
        """Define sequential edges between nodes."""
        # Primary workflow path
        self._graph.add_edge("planning", "human_approval")
        self._graph.add_edge("human_approval", "model")

        # Parallel paths after model
        self._graph.add_edge("model", "security")
        self._graph.add_edge("model", "tester")
        self._graph.add_edge("model", "db")

        # Design pattern checks after security
        self._graph.add_edge("security", "design_pattern")

        # Lifecycle orchestration
        self._graph.add_edge("design_pattern", "lifecycle")
        self._graph.add_edge("tester", "lifecycle")
        self._graph.add_edge("db", "lifecycle")

        # Git operations after lifecycle
        self._graph.add_edge("lifecycle", "git")

        # CI/CD after git
        self._graph.add_edge("git", "cicd")

        # Final output
        self._graph.add_edge("cicd", "output")

        # Terminal node
        self._graph.add_edge("output", END)

    def _add_conditional_edges(self) -> None:
        """Define conditional routing logic."""

        def route_after_approval(state: AgentState) -> str:
            """Route after human approval based on decision."""
            approval_status = state.get("approval_status", "pending")

            if approval_status == "approved":
                return "model"
            elif approval_status == "rejected":
                return "planning"  # Go back to planning
            else:
                return "human_approval"  # Stay in approval

        # Conditional routing after human approval
        self._graph.add_conditional_edges(
            "human_approval",
            route_after_approval,
            {
                "model": "model",
                "planning": "planning",
                "human_approval": "human_approval",
            }
        )

        def route_after_security(state: AgentState) -> str:
            """Route after security based on findings."""
            security_output = state.get("security_output", {})
            findings = security_output.get("findings", [])

            # If critical vulnerabilities, block and go back to model
            critical = [f for f in findings if f.get("severity") == "critical"]
            if critical:
                return "model"  # Requires fixing

            return "design_pattern"

        # Conditional routing after security
        self._graph.add_conditional_edges(
            "security",
            route_after_security,
            {
                "model": "model",
                "design_pattern": "design_pattern",
            }
        )

        def route_after_tester(state: AgentState) -> str:
            """Route after testing based on results."""
            tester_output = state.get("tester_output", {})
            summary = tester_output.get("summary", {})

            # If tests failed, could route back to model
            if not summary.get("success", True):
                return "lifecycle"  # Continue but flag issues

            return "lifecycle"

        # Note: Tester runs in parallel with security and db
        # Results are collected at lifecycle node

    def get_node(self, name: str) -> Any:
        """Get a registered node by name."""
        return self._nodes.get(name)

    def get_graph(self) -> StateGraph:
        """Get the uncompiled graph (for visualization)."""
        return self._graph


def build_agent_graph() -> Any:
    """
    Convenience function to build the default agent graph.

    Returns:
        Compiled LangGraph application.
    """
    builder = GraphBuilder()
    return builder.build()
