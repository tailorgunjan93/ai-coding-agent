# AI Coding Agent - Low-Level Design (LLD)

## 1. Interface Contracts

All interfaces use Abstract Base Classes (ABC) with `@abstractmethod` decorators. Return types and exceptions are explicitly defined using TypedDict and enum types.

### 1.1 LLMInterface

**File:** `src/main/agent/interfaces/llm_interface.py`

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, TypedDict
from enum import Enum

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    COHERE = "cohere"

class GenerationSettings(TypedDict, total=False):
    temperature: float
    max_tokens: int
    top_p: float
    stop_sequences: list[str]
    cache_prefix: str | None

class LLMResponse(TypedDict):
    content: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens
    model: str
    finish_reason: str

class LLMInterface(ABC):
    """Abstract base for all LLM interactions in the agent framework."""

    @abstractmethod
    def get_llm(self) -> Any:
        """Return the underlying LangChain LLM/tool object."""

    @abstractmethod
    def get_provider(self) -> LLMProvider:
        """Return the LLM provider type."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> LLMResponse:
        """Generate text/code from prompt."""

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        settings: GenerationSettings | None = None
    ) -> AsyncIterator[str]:
        """Generate text/code from prompt with streaming."""

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Check if provider supports function/tool calling."""

    @abstractmethod
    def get_context_window(self) -> int:
        """Return max context window size in tokens."""
```

### 1.2 DBInterface

**File:** `src/main/agent/interfaces/db_interface.py`

```python
from abc import ABC, abstractmethod
from typing import Any, TypedDict
from enum import Enum

class DBType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"

class QueryResult(TypedDict):
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    execution_time_ms: float

class DBConnectionConfig(TypedDict):
    host: str
    port: int
    database: str
    user: str
    password: str

class DBInterface(ABC):
    """Abstract base for database operations."""

    @abstractmethod
    def connect(self, config: DBConnectionConfig | None = None) -> None:
        """Establish database connection."""

    @abstractmethod
    def create_table(self, schema: str, table_name: str) -> bool:
        """Create a table from schema definition."""

    @abstractmethod
    def run_query(self, query: str, params: dict[str, Any] | None = None) -> QueryResult:
        """Execute a query and return results."""

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""

    @abstractmethod
    def get_db_type(self) -> DBType:
        """Return the database type."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Check database health."""
```

### 1.3 NodeInterface

**File:** `src/main/agent/interfaces/node_interface.py`

```python
from abc import ABC, abstractmethod
from typing import TypedDict, NotRequired, Any
from enum import Enum

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class NodeExecutionContext(TypedDict):
    node_id: str
    attempt: int
    max_attempts: int
    timeout_seconds: int
    callbacks: NotRequired[list[Any]]

class NodeResult(TypedDict):
    status: NodeStatus
    output: NotRequired[Any]
    error: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]
    execution_time_ms: float

class NodeInterface(ABC):
    """Abstract base for all agent nodes in the LangGraph workflow."""

    @property
    @abstractmethod
    def node_name(self) -> str:
        """Unique identifier for this node type."""

    @property
    @abstractmethod
    def input_schema(self) -> type:
        """Pydantic model/class for required input state fields."""

    @property
    @abstractmethod
    def output_schema(self) -> type:
        """Pydantic model/class for output state fields."""

    @abstractmethod
    def validate_input(self, state: dict) -> tuple[bool, str | None]:
        """Validate that state has required fields."""

    @abstractmethod
    async def execute(
        self,
        state: dict,
        context: NodeExecutionContext
    ) -> NodeResult:
        """Execute the node's main logic."""

    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if node should retry after an error."""

    @abstractmethod
    def get_required_dependencies(self) -> list[str]:
        """Return list of node names that must execute before this node."""
```

### 1.4 RepoInterface

**File:** `src/main/agent/interfaces/repo_interface.py`

```python
from abc import ABC, abstractmethod
from typing import TypedDict, NotRequired

class CommitInfo(TypedDict):
    message: str
    author: str
    timestamp: str
    files_changed: list[str]
    sha: NotRequired[str]

class PRInfo(TypedDict):
    title: str
    description: str
    source_branch: str
    target_branch: str
    url: NotRequired[str]
    status: NotRequired[str]

class RepoInterface(ABC):
    """Abstract base for repository operations."""

    @abstractmethod
    def clone(self, url: str, path: str) -> bool:
        """Clone repository to local path."""

    @abstractmethod
    def commit(self, message: str, files: list[str]) -> CommitInfo:
        """Commit changes with semantic message."""

    @abstractmethod
    def push(self, branch: str | None = None) -> bool:
        """Push commits to remote."""

    @abstractmethod
    def create_pr(self, title: str, body: str, source: str, target: str) -> PRInfo:
        """Create pull request."""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get repository status."""
```

## 2. Exception Hierarchy

**File:** `src/main/agent/exceptions.py`

```
AgentException (base)
├── ConfigurationError      - Invalid or missing configuration
├── ConnectionError         - Failed to connect to external service
├── LLMError                - LLM generation or interaction failure
│   ├── RateLimitError      - Rate limit exceeded
│   └── ContextLengthError  - Prompt exceeds model context window
├── ValidationError         - Input validation failed
├── NodeExecutionError      - Node failed during execution
│   └── RetryableError      - Error that should trigger retry
└── SecurityError           - Security violation detected
    └── PermissionError     - Insufficient permissions
```

## 3. Model Definitions

### 3.1 AgentState (TypedDict)

**File:** `src/main/agent/models/agent_state.py`

Central state schema shared across all nodes.

```python
class AgentState(TypedDict, total=False):
    # Session info
    session_id: str
    user_id: str
    created_at: str
    original_request: str
    request_type: str  # generate, enhance, fix, debug

    # Planning
    plan: str
    tasks: list[Task]
    current_task_index: int

    # Messages & Artifacts
    messages: list[dict[str, Any]]
    artifacts: list[Artifact]

    # Node outputs
    planning_output: dict[str, Any]
    model_output: dict[str, Any]
    tester_output: dict[str, Any]
    security_output: dict[str, Any]
    db_output: dict[str, Any]
    git_output: dict[str, Any]
    cicd_output: dict[str, Any]

    # Status
    errors: list[dict[str, Any]]
    warnings: list[str]
    success: bool
    metadata: dict[str, Any]
```

### 3.2 PlanSchema (Pydantic)

**File:** `src/main/agent/models/plan_schema.py`

```python
class PlanTask(BaseModel):
    id: str
    description: str
    priority: int = Field(default=0, ge=0, le=10)
    estimated_hours: float | None
    depends_on: list[str] = []
    skills_required: list[str] = []

class PlanRisk(BaseModel):
    id: str
    description: str
    likelihood: str
    impact: str
    mitigation: str

class PlanSchema(BaseModel):
    project_name: str
    version: str = "1.0.0"
    created_at: datetime
    updated_at: datetime
    requirements: list[str]
    architecture_overview: str
    tech_stack: list[str]
    tasks: list[PlanTask]
    dependencies: list[tuple[str, str]]
    risks: list[PlanRisk] = []
    design_patterns: list[str] = []
    human_approval_required: bool = True
    approval_status: str = "pending"
```

### 3.3 TestResult (Pydantic)

**File:** `src/main/agent/models/test_result.py`

```python
class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class TestCase(BaseModel):
    id: str
    name: str
    status: TestStatus
    duration_ms: float
    error_message: str | None

class TestSuite(BaseModel):
    name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    test_cases: list[TestCase]
    coverage_percent: float | None

class TestResult(BaseModel):
    session_id: str
    timestamp: datetime
    language: str
    framework: str
    suites: list[TestSuite]
    summary: TestSummary
```

## 4. Wrapper Implementation Patterns

### 4.1 LLMWrapper (Composition)

Adds caching, rate limiting, and fallback to any LLMInterface.

```python
class LLMWrapper:
    def __init__(
        self,
        primary: LLMInterface,
        fallback: LLMInterface | None = None,
        cache_ttl_seconds: int = 300,
        rate_limit_rpm: int = 60
    ):
        self._primary = primary
        self._fallback = fallback
        self._cache: dict[str, LLMResponse] = {}
        self._request_timestamps: list[datetime] = []

    async def generate(self, prompt: str, settings: GenerationSettings | None = None) -> LLMResponse:
        # 1. Check rate limit
        # 2. Check cache
        # 3. Call primary, on failure call fallback
        # 4. Cache and return response

    async def generate_stream(self, prompt: str, settings: GenerationSettings | None = None) -> AsyncIterator[str]:
        # Similar pattern with streaming
```

### 4.2 ToolWrapper (LangChain Enhancement)

Composes LangChain tools with retrieval and memory capabilities.

```python
class ToolWrapper:
    def attach_retrieval(self, llm, vectorstore, chain_type="stuff"):
        return RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())

    def attach_memory(self, llm):
        memory = ConversationBufferMemory()
        return llm, memory

    def create_agent_with_tools(self, llm, tools, memory=None):
        return AgentExecutor.from_agent_and_tools(agent, tools=tools)
```

## 5. Node Implementation Pattern

### 5.1 BaseNode

Abstract base implementing NodeInterface with common functionality.

```python
class BaseNode(NodeInterface, ABC):
    def __init__(self, max_retries: int = 3, timeout_seconds: int = 300):
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds

    async def execute(self, state: dict, context: NodeExecutionContext) -> NodeResult:
        # Template method:
        # 1. Validate input
        # 2. Call _execute
        # 3. Handle errors/retry
        # 4. Return structured result

    @abstractmethod
    async def _execute(self, state: dict, context: NodeExecutionContext) -> Any:
        """Override in subclass."""
```

### 5.2 Node Skeleton Pattern

```python
class PlanningNode(BaseNode):
    @property
    def node_name(self) -> str:
        return "planning"

    @property
    def input_schema(self) -> type:
        return AgentState

    @property
    def output_schema(self) -> type:
        return PlanSchema

    def get_required_dependencies(self) -> list[str]:
        return ["input"]

    async def _execute(self, state: dict, context: NodeExecutionContext) -> dict[str, Any]:
        # Implementation here
        pass
```

## 6. State Management (LangGraph)

### 6.1 Graph Builder Pattern

```python
def build_agent_graph() -> StateGraph:
    class AgentState(TypedDict):
        session_id: str
        # ... all shared fields

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("input", input_node)
    graph.add_node("planning", PlanningNode(...))
    # ... more nodes

    # Define edges
    graph.add_edge("input", "planning")
    graph.add_edge("planning", "human_approval")

    # Conditional routing
    graph.add_conditional_edges(
        "human_approval",
        lambda state: "model" if state.get("approval_status") == "approved" else END
    )

    # Parallel execution
    graph.add_parallel_edges("model", ["security", "tester"])

    graph.set_entry_point("input")
    return graph.compile(checkpointer=MemorySaver())
```

## 7. Error Propagation Pattern

```python
async def _execute(self, state: dict, context: NodeExecutionContext) -> Any:
    try:
        result = await self._perform_operation(state)
        return result
    except RateLimitError:
        # Don't retry rate limits
        raise
    except (ConnectionError, TimeoutError):
        # Retry network errors
        raise RetryableError(f"Network error: {e}") from e
    except ValidationError:
        # Don't retry validation errors
        return {"error": str(e), "recoverable": False}
    except Exception:
        raise NodeExecutionError(f"Unexpected error: {e}") from e
```

## 8. Critical Design Principles

1. **Composition over inheritance** - Wrappers wrap interfaces, not inherit
2. **TypedDict for state** - LangGraph compatibility, explicit field names
3. **Pydantic for schemas** - PlanSchema, TestResult - well-defined, stable
4. **Async everywhere** - All I/O operations are async
5. **Explicit exceptions** - No silent failures, clear error propagation
6. **Template method** - BaseNode handles common logic, subclasses implement _execute
7. **Validation at boundaries** - validate_input() at start of every node execution
