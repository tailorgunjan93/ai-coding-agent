# Architecture Overview

## Purpose
This document describes the architecture of the AI-powered coding agent.  
It explains the LangGraph schema, node orchestration, and how each component interacts to deliver production-grade code.

---

## High-Level Design
The agent is built on **LangGraph orchestration** with modular nodes.  
Each node has a single responsibility, ensuring maintainability and scalability.

---

## Node Definitions
- **UserInput Node** → Captures user prompts.
- **Planning Node** → Generates/updates `planning.md`.
- **HumanApproval Node** → Requires explicit approval before execution.
- **Model Node** → Generates code using LLM/SLM providers.
- **Validation Node** → Detects hallucinations and unsafe outputs.
- **WebSearch Node** → Provides fallback knowledge.
- **Plugin Node** → Injects external skills.
- **Tester Node** → Auto-generates and runs unit, integration, and edge-case tests.
- **Memory Node** → Stores context for future enhancements.
- **CodeGraph Node** → Generates structural diagrams.
- **DataFlowGraph Node** → Generates runtime flow diagrams.
- **Lifecycle Node** → Manages create, enhance, fix, add, debug, run, delete actions.
- **DB Node** → Handles schema, migrations, ORM, queries.
- **Git Node** → Commits changes with semantic messages, opens PRs.
- **CI/CD Node** → Generates pipelines (GitHub, GitLab, Azure).
- **DesignPattern Node** → Enforces SOLID principles and design patterns.
- **Security Node** → Runs linting, static analysis, vulnerability scans.
- **Output Node** → Delivers production-ready code/app.

---

## Workflow Diagram
```mermaid
flowchart LR
  A[User Input] --> B[Planning Node]
  B --> C[Human Approval]
  C --> D[Model Node]
  D --> E[Validation Node]
  E --> F[WebSearch Node]
  D --> G[Plugin Node]
  D --> H[DesignPattern Node]
  D --> I[Lifecycle Node]
  I --> J[Tester Node]
  I --> K[DB Node]
  I --> L[CodeGraph Node]
  I --> M[DataFlowGraph Node]
  J --> I
  K --> J
  I --> N[Git Node]
  N --> O[CI/CD Node]
  J --> O
  P[Security Node] --> O
  O --> Q[Output Node]
  R[Memory Node] --> Q
  L --> B
  M --> B
