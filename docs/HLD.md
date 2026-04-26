# AI Coding Agent - High-Level Design (HLD)

## 1. System Overview

The AI Coding Agent is a LangGraph-based autonomous coding assistant that coordinates multiple specialized nodes to transform user requests into complete, tested, and deployable code solutions.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              VS CODE EXTENSION (Frontend)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Generate  │ │Enhance  │ │ FixCode  │ │AddFeature│ │DebugCode │ │PlanApp   │  │
│  │App       │ │Code     │ │          │ │          │ │          │ │          │  │
│  └──────┬───┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
└─────────┼─────────┼────────────┼────────────┼────────────┼────────────┼────────┘
          │         │            │            │            │            │
          ▼         ▼            ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              LangGraph Workflow Engine                              │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           STATE GRAPH                                        │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │   │
│  │  │ INPUT   │───▶│PLANNING │───▶│APPROVAL │───▶│  MODEL  │───▶│DESIGN   │  │   │
│  │  └─────────┘    └────┬────┘    └─────────┘    └────┬────┘    └────┬────┘  │   │
│  │                      │                              │               │       │   │
│  │                      ▼                              ▼               ▼       │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │   │
│  │  │ LIFECYCLE│◀───│ VALIDATE│◀───│ PLUGIN  │    │SECURITY │    │  TESTER │  │   │
│  │  └────┬────┘    └─────────┘    └─────────┘    └─────────┘    └────┬────┘  │   │
│  │       │                                                              │       │   │
│  │       ▼                                                              ▼       │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │   │
│  │  │   GIT   │◀───│   DB    │◀───│CODEGRAPH│◀───│DATAFLOW │◀───│MEMORY   │  │   │
│  │  └────┬────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │   │
│  │       │                                                              │       │   │
│  │       ▼                                                              ▼       │   │
│  │  ┌─────────┐                                                   ┌─────────┐  │   │
│  │  │  CICD   │──────────────────────────────────────────────────▶│ OUTPUT  │  │   │
│  │  └─────────┘                                                   └─────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Core Components

### 2.1 Interface Layer (Abstract Contracts)

The interface layer defines **strict contracts** that all implementations must follow. This ensures interchangeable components and testable architecture.

| Interface | File | Responsibility | Key Methods |
|-----------|------|---------------|-------------|
| `LLMInterface` | `interfaces/llm_interface.py` | Unified LLM access | `get_llm()`, `generate()`, `generate_stream()` |
| `DBInterface` | `interfaces/db_interface.py` | Database operations | `connect()`, `create_table()`, `run_query()` |
| `NodeInterface` | `interfaces/node_interface.py` | Agent node contract | `execute(state)`, `validate(state)` |
| `RepoInterface` | `interfaces/repo_interface.py` | Repository operations | `clone()`, `commit()`, `push()` |

### 2.2 Wrapper Layer (Composition-Based)

Wrappers add orthogonal concerns (caching, rate-limiting, retries) via composition without modifying wrapped components.

| Wrapper | Wraps | Purpose |
|---------|-------|---------|
| `LLMWrapper` | `LLMInterface` | Adds caching, rate limiting, fallback |
| `ToolWrapper` | LangChain tools | RetrievalQA, Memory, Agent creation |
| `PromptWrapper` | Prompt templates | Versioning, interpolation, validation |
| `DBWrapper` | `DBInterface` | Connection pooling, query templating |

### 2.3 Node Layer (LangGraph Nodes)

Nodes are the execution units in the LangGraph state machine.

| Node | Input | Output | Responsibility |
|------|-------|--------|----------------|
| `PlanningNode` | user_request | planning.md | Creates structured plans |
| `HumanApprovalNode` | plan | approved/rejected | Gates human confirmation |
| `ModelNode` | plan | code/draft | LLM code generation |
| `SecurityNode` | code | scan_report | Static analysis, vuln scan |
| `TesterNode` | code | test_results | Test generation & execution |
| `DBNode` | schema_spec | migrations | DB schema/migration ops |
| `GitNode` | changes | commit/PR | Version control operations |
| `CICDNode` | artifacts | pipeline_status | CI/CD integration |
| `OutputNode` | all_outputs | final_response | Result aggregation |

## 3. Data Flow

```
User Input (VS Code)
        │
        ▼
┌───────────────────┐
│   Input Node      │ ──── validates raw prompt
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Planning Node    │ ──── generates planning.md
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ HumanApproval     │ ──── awaits user confirmation
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Model Node      │ ──── calls LLM via LLMInterface
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌───────┐   ┌────────┐
│Design │   │Security│ ──── parallel execution
│Node   │   │Node    │
└───┬───┘   └────┬───┘
    │            │
    └─────┬──────┘
          │
          ▼
┌───────────────────┐
│  Lifecycle Node   │ ──── create/update/fix/delete
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌───────┐   ┌────────┐
│  DB   │   │Tester  │ ──── parallel execution
│ Node  │   │Node    │
└───┬───┘   └────┬───┘
    │            │
    └─────┬──────┘
          │
          ▼
┌───────────────────┐
│   Git Node        │ ──── commits changes
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   CICD Node       │ ──── triggers pipeline
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Output Node      │ ──── aggregates results
└───────────────────┘
```

## 4. Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│  1. INPUT VALIDATION                                        │
│     - Prompt injection prevention                           │
│     - Schema validation (Pydantic)                          │
│     - Rate limiting per user session                        │
├─────────────────────────────────────────────────────────────┤
│  2. LLM INTERACTION                                         │
│     - Content filtering on prompts/responses               │
│     - Hallucination detection via ValidationNode           │
│     - Context window management                             │
├─────────────────────────────────────────────────────────────┤
│  3. CODE EXECUTION                                          │
│     - Sandboxed execution environment                       │
│     - File system access control                            │
│     - Command allowlist (no rm -rf, etc.)                  │
├─────────────────────────────────────────────────────────────┤
│  4. EXTERNAL INTEGRATIONS                                   │
│     - OAuth tokens encrypted at rest                       │
│     - API key vault integration                              │
│     - Git credentials secure storage                       │
├─────────────────────────────────────────────────────────────┤
│  5. AUDIT LOGGING                                           │
│     - All operations logged with timestamps                 │
│     - User actions tracked for compliance                   │
│     - Error patterns analyzed for threats                   │
└─────────────────────────────────────────────────────────────┘
```

## 5. Extensibility Points

| Extension Point | Mechanism | Example |
|-----------------|-----------|---------|
| New Node Type | Implement `NodeInterface` ABC | `CloudNode` for cloud deployment |
| New LLM Provider | Extend `LLMInterface` | `CohereAdapter` |
| New Database | Extend `DBInterface` | `PostgresAdapter` |
| New Tool | LangChain Tool interface | `SearchApiTool` |
| New Visualization | CodeGraph/DataFlow protocols | `SequenceDiagramNode` |

## 6. Technology Stack

| Layer | Technology |
|-------|------------|
| Orchestration | LangGraph |
| LLM Integration | LangChain |
| State Management | TypedDict + LangGraph State |
| Schema Validation | Pydantic v2 |
| Async Operations | asyncio |
| Code Analysis | AST parsing, regex |
| Testing | pytest |

## 7. File Structure

```
src/main/agent/
├── agent.py              # Main entry point
├── graph_builder.py     # LangGraph state machine
├── exceptions.py        # Exception hierarchy
├── interfaces/
│   ├── llm_interface.py
│   ├── db_interface.py
│   ├── node_interface.py
│   └── repo_interface.py
├── models/
│   ├── agent_state.py   # TypedDict state
│   ├── plan_schema.py   # Pydantic models
│   └── test_result.py
├── wrappers/
│   ├── llm_wrapper.py
│   ├── tool_wrapper.py
│   ├── prompt_wrapper.py
│   └── db_wrapper.py
├── nodes/
│   ├── base_node.py     # Abstract base
│   ├── planning_node.py
│   ├── model_node.py
│   ├── security_node.py
│   ├── tester_node.py
│   ├── db_node.py
│   ├── git_node.py
│   ├── cicd_node.py
│   └── output_node.py
└── utils/
    ├── code_commenter.py
    ├── design_pattern_enforcer.py
    └── ...
```
