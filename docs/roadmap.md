# Project Roadmap

## Overview
This roadmap outlines the evolution of the AI-powered coding agent.  
It provides short-term, mid-term, and long-term goals to guide contributors and ensure alignment with the vision.

---

## Short-Term Goals (0–3 months)
- ✅ Establish repository structure (`/src`, `/tests`, `/ci`, `/docs`, `/agent-graphs`, `/db`).
- ✅ Create starter templates (`README.md`, `planning.md`).
- ✅ Implement core LangGraph nodes:
  - Planning, HumanApproval, Model, Lifecycle, Tester, DB, Git, CI/CD, DesignPattern, Security, Output.
- ✅ Integrate CI/CD pipelines (GitHub Actions, GitLab CI, Azure DevOps).
- ✅ Enforce SOLID principles and design patterns.
- ✅ Continuous testing loop (unit, integration, edge-case).
- ✅ Security enforcement (linting, static analysis, vulnerability scans).

---

## Mid-Term Goals (3–9 months)
- 🔄 Expand visualization:
  - CodeGraph and DataFlowGraph with interactive diagrams.
- 🔄 Enhance DB Node:
  - Support multiple databases (PostgreSQL, MySQL, MongoDB).
  - Automated migrations and rollback strategies.
- 🔄 Add plugin system:
  - External skills (e.g., API integrations, cloud services).
- 🔄 Improve human-in-the-loop UX:
  - VS Code extension UI for approvals and workflow visualization.
- 🔄 Strengthen Git integration:
  - Automated PR creation, branch management, semantic commit enforcement.
- 🔄 Expand testing:
  - Performance tests, load tests, fuzzing.

---

## Long-Term Goals (9–18 months)
- 🚀 Multi-agent orchestration:
  - Specialized agents for planning, testing, security, and deployment.
- 🚀 Hybrid model strategy:
  - Combine local SLMs with cloud LLMs for efficiency.
- 🚀 Marketplace integration:
  - Share workflows, plugins, and templates with the community.
- 🚀 Enterprise adoption:
  - Role-based access control, audit logs, compliance checks.
- 🚀 Open-source release:
  - Public repo with contributor guidelines, issue templates, and community governance.
- 🚀 Advanced visualization:
  - Real-time code/data flow dashboards with monitoring hooks.

---

## Vision
The agent will evolve from a **coding assistant** into a **production-grade developer platform**.  
It will combine **planning, human approval, CI/CD, Git, DB handling, security, testing, and visualization** into a trusted workflow for teams and enterprises.

---

## Recommendations
- Keep roadmap updated quarterly.
- Align contributions with roadmap milestones.
- Treat short-term goals as **non-negotiable foundations** before expanding.
