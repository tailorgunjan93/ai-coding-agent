# Contributor Guide

Welcome to the `ai-coding-agent` project! To maintain high code quality and architectural integrity, all contributors must follow these rules.

## Core Rules

1.  **Interfaces Everywhere**: Every node, wrapper, and utility MUST implement an interface (e.g., `NodeInterface`, `LLMInterface`, `DBInterface`, `GitInterface`, `CICDInterface`). This ensures consistency and interchangeability.
2.  **Never Import Libraries Directly in Nodes**: Nodes must remain high-level logic controllers. Always use wrappers for external calls (LLM, DB, Git, CI/CD).
    *   *Bad*: `import openai` inside a node.
    *   *Good*: Inject `LLMInterface` and use `llm.generate()`.
3.  **Always Update AgentState**: Nodes must be pure transformations of the `AgentState`. They receive the current state and must return an updated `AgentState` object.
4.  **Tests are Mandatory**: Every new function, node, or wrapper must have a corresponding unit test in the `/tests/` directory. Use `pytest`.
5.  **Follow SOLID Principles**: Avoid hard-coded dependencies. Use dependency injection to provide implementations of interfaces to your components.
6.  **Use Stub Templates**: When starting a new node or wrapper, use the provided `.stub` templates to ensure you follow the required structure.

## Architectural Enforcement

We use automated tools to enforce these patterns:
- **Linting**: `flake8`, `black`, and `mypy` run on every commit.
- **Design Pattern Enforcer**: A custom script scans for direct API calls or other architectural violations.

## Workflow

1.  **Pick a Task**: Tasks are defined in the `README.md` files of each directory.
2.  **Implement**: Follow the one-line instructions and TODOs in the stub templates.
3.  **Test**: Run `pytest` locally.
4.  **Lint**: Ensure `pre-commit` hooks pass.
5.  **Commit**: Your commit will only be accepted if all checks pass.

---

### Node Implementation Rules

- Implement only the `run()` method.
- Input: `AgentState` object.
- Output: Updated `AgentState`.
- Use wrappers for all external calls.
- Add a unit test in `/tests/unit/` for every node.
