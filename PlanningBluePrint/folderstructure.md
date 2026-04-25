📦 ai-coding-agent/
│
├── 📄 README.md
│   └─ Overview, setup instructions, architecture diagram, usage examples.
│
├── 📄 planning.md
│   └─ Auto-generated plan for each new app or enhancement (human-approved).
│
├── 📁 src/
│   ├── main/
│   │   ├── agent/
│   │   │   ├── nodes/                  → Atomic node implementations
│   │   │   │   ├── planning_node.py
│   │   │   │   ├── human_approval_node.py
│   │   │   │   ├── model_node.py
│   │   │   │   ├── lifecycle_node.py
│   │   │   │   ├── tester_node.py
│   │   │   │   ├── db_node.py
│   │   │   │   ├── git_node.py
│   │   │   │   ├── cicd_node.py
│   │   │   │   ├── design_pattern_node.py
│   │   │   │   ├── security_node.py
│   │   │   │   └── output_node.py
│   │   │   ├── interfaces/             → Abstract contracts
│   │   │   │   ├── node_interface.py
│   │   │   │   ├── repo_interface.py
│   │   │   │   └── db_interface.py
│   │   │   ├── models/                 → Pydantic schemas
│   │   │   │   ├── agent_state.py
│   │   │   │   ├── test_result.py
│   │   │   │   └── plan_schema.py
│   │   │   ├── wrappers/               → Library abstraction
│   │   │   │   ├── prompt_wrapper.py
│   │   │   │   ├── llm_wrapper.py
│   │   │   │   ├── db_wrapper.py
│   │   │   │   ├── git_wrapper.py
│   │   │   │   └── cicd_wrapper.py
│   │   │   ├── agent.py                → LangGraph workflow definition
│   │   │   └── graph_builder.py        → Builds graph dynamically
│   │   ├── utils/                      → Helper utilities
│   │   │   ├── code_commenter.py
│   │   │   ├── design_pattern_enforcer.py
│   │   │   ├── db_handler.py
│   │   │   ├── git_helper.py
│   │   │   ├── cicd_generator.py
│   │   │   └── test_runner.py
│   │   └── langgraph_schema.json
│   │
│   └── extension/                      → VS Code extension layer
│       ├── commands/
│       ├── ui/
│       └── manifest.json
│
├── 📁 tests/
│   ├── unit/
│   ├── integration/
│   ├── edge_cases/
│   └── db_tests/
│
├── 📁 agent-graphs/
│   ├── code_graph.json
│   ├── data_flow_graph.json
│   └── visualizations/
│
├── 📁 ci/
│   ├── github-actions.yml
│   ├── azure-pipelines.yml
│   └── gitlab-ci.yml
│
├── 📁 docs/
│   ├── architecture.md
│   ├── workflow.md
│   ├── design_patterns.md
│   ├── testing_strategy.md
│   └── ci_cd_integration.md
│
├── 📁 db/
│   ├── schema.sql
│   ├── migrations/
│   └── orm_models/
│
├── 📁 .vscode/
│   ├── settings.json
│   ├── launch.json
│   └── tasks.json
│
├── 📁 .github/
│   ├── ISSUE_TEMPLATE.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│
└── 📄 LICENSE
