# Wrappers

This directory contains wrappers for external services and tools.

## Instructions

1.  **Implement Provider Wrappers**: Each file in this directory must wrap a specific service (LLM, DB, etc.) and expose a standardized interface.
2.  **Interface Compliance**: Every wrapper must implement its corresponding interface from `src/main/agent/interfaces/`.
3.  **Mandatory Methods**:
    *   LLM wrappers must expose `get_llm()`.
    *   DB/Service wrappers must expose `connect()`.
4.  **No Business Logic**: Wrappers should only handle communication, error mapping, and low-level details. Business logic belongs in Nodes.

## Tasks

- [ ] Implement provider wrappers. Each file must expose `get_llm()` or `connect()`.
- [ ] Add unit tests for every wrapper in `tests/unit/wrappers/`.
