# Nodes

This directory contains the execution nodes for the LangGraph agent.

## Instructions

1.  **Single Responsibility**: Each node should update exactly one field (or a small set of related fields) in the `AgentState`.
2.  **No Extra Logic**: Don't add complex logic or external API calls directly in the node. Use wrappers.
3.  **Interface Compliance**: Every node must implement `NodeInterface` and the `run()` method.
4.  **State Management**: Always return the updated `AgentState`.

## Tasks

- [ ] Implement nodes that update specific fields in `AgentState`.
- [ ] Ensure `run()` is the only method implemented for logic.
- [ ] Add unit tests for every node in `tests/unit/nodes/`.
