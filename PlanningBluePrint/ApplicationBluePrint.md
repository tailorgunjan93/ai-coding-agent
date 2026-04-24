# Open-Source Coding Agent (VS Code Extension)

## 1. Goals
- Generate complete software applications from prompts.
- Enhance or fix existing codebases.
- Always create/update `planning.md` before coding.
- Manage full code lifecycle: create, update, delete, debug, run.
- Ensure production-grade quality with continuous testing.
- Enforce highest coding standards and design patterns (SOLID, Clean Architecture).
- Integrate CI/CD pipelines if available.
- Automate Git commits with semantic messages and PR descriptions.
- Handle databases (schema, migrations, ORM, queries).
- Every piece of code must include meaningful comments.
- Maintain memory and project context.
- Visualize code graphs and data flow graphs.
- Human-in-the-loop checkpoints for planning and execution.
- Publish on VS Code Extensions Marketplace.

## 2. Architecture
- **Frontend (VS Code Extension API)**
  - Commands:
    - `GenerateApp` → end-to-end app creation.
    - `EnhanceCode` → improve/refactor existing code.
    - `FixCode` → detect and correct bugs.
    - `AddFeature` → extend functionality.
    - `DebugCode` → run diagnostics and suggest fixes.
    - `RunCode` → execute in sandbox/terminal.
    - `DeleteCode` → remove obsolete files.
    - `PlanEnhancement` → create/update `planning.md`.
    - `VisualizeGraph` → show code/data flow graphs.
    - `TestCode` → run auto-generated tests.
    - `CommitCode` → Git commit with semantic message.
    - `DeployPipeline` → CI/CD integration.
    - `DatabaseOps` → schema, migrations, queries.

- **Backend (LangGraph Orchestration)**
  - Nodes:
    - Input Node (user query)
    - Planning Node (`planning.md`)
    - HumanApproval Node (confirm plan before execution)
    - Model Node (API or local SLM)
    - Validation Node (detect hallucination)
    - Web Search Node (fallback)
    - Plugin Node (skill injection)
    - Tester Node (unit/integration/edge tests)
    - Memory Node (persistent context)
    - Code Graph Node (structure visualization)
    - Data Flow Graph Node (runtime visualization)
    - Lifecycle Node (create, update, delete, debug, run)
    - Git Node (commit, PR, semantic messages)
    - CI/CD Node (pipeline generation, deploy)
    - DB Node (schema, migrations, ORM, queries)
    - Output Node (final response)

## 3. Code Lifecycle Management
- **GenerateApp**: Scaffold full-stack apps with design patterns.
- **EnhanceCode**: Refactor existing repo, improve architecture.
- **FixCode**: Detect bugs, auto-correct, retest.
- **AddFeature**: Extend codebase with new modules/features.
- **DebugCode**: Run diagnostics, log errors, suggest fixes.
- **RunCode**: Execute in sandbox or VS Code terminal.
- **DeleteCode**: Remove obsolete files safely.

## 4. Planning System
- `planning.md` auto-generated for every new app or enhancement.
- Contains:
  - Requirements
  - Architecture
  - Tech stack
  - Task breakdown
  - Design patterns applied
  - Links to code graph/data flow graph
- Human approval required before coding starts.

## 5. Tester System
- Auto-generate tests per language:
  - Python → pytest
  - .NET → xUnit
  - JS/TS → Jest
- Run in sandbox, collect results.
- Continuous correction loop until tests pass.

## 6. Visualization System
- **Code Graph**: Classes, functions, modules.
- **Data Flow Graph**: Input/output dependencies, runtime flow.
- Stored in `/agent-graphs`.

## 7. Git Integration
- Auto-generate semantic commit messages (`feat:`, `fix:`, `refactor:`).
- Push commits with linked `planning.md`.
- Optionally open PRs with generated descriptions.

## 8. CI/CD Integration
- Detect if CI/CD is available (GitHub Actions, GitLab CI, Azure DevOps).
- Auto-generate pipeline configs (build, test, deploy).
- Trigger pipelines after enhancements or new features.
- Block deployment if tests fail.

## 9. Database Handling
- **DB Node**:
  - Schema design.
  - Migrations.
  - ORM model generation (SQLAlchemy, Prisma, EF Core).
  - Query optimization.
  - DB-specific tests (data integrity, performance).

## 10. Workflow
1. User prompt → Planning Node creates/updates `planning.md`.
2. HumanApproval Node → user confirms plan.
3. Model Node generates code (cloud LLM or local SLM).
4. Lifecycle Node applies action (create/update/fix/add/debug/run).
5. Tester Node validates with tests.
6. Graph Nodes update visualization.
7. DB Node handles schema/migrations if needed.
8. Git Node commits changes.
9. CI/CD Node triggers pipeline if available.
10. Memory Node stores context for future enhancements.
11. Output Node delivers production-ready code/app.

## 11. Publishing
- License: MIT/Apache 2.0.
- Package with `vsce`.
- Publish on VS Marketplace.
