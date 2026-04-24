# Changelog

All notable changes to this project will be documented in this file.  
This project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]
- Planned features and improvements not yet released.

---

## [0.1.0] - 2026-04-24
### Added
- Initial repository structure (`/src`, `/tests`, `/ci`, `/docs`, `/agent-graphs`, `/db`).
- Core LangGraph nodes: Planning, HumanApproval, Model, Lifecycle, Tester, DB, Git, CI/CD, DesignPattern, Security, Output.
- CI/CD pipeline templates for GitHub Actions, GitLab CI, and Azure DevOps.
- Documentation:
  - `architecture.md` → LangGraph schema (visual + textual).
  - `workflow.md` → End-to-end lifecycle description.
  - `design_patterns.md` → SOLID principles and enforced patterns.
  - `testing_strategy.md` → Continuous testing and correction loop.
  - `security_node.md` → Linting, static analysis, vulnerability scans.
  - `ci_cd_integration.md` → Unified CI/CD strategy.
  - `repository_structure.md` → Contributor directory guide.
  - `contributing.md` → Contributor workflow.
  - `roadmap.md` → Short, mid, and long-term goals.
  - `governance.md` → Roles, review processes, decision-making rules.
  - `CODE_OF_CONDUCT.md` → Community standards.

### Changed
- Standardized commit messages to semantic format (`feat:`, `fix:`, `docs:`).
- Linked commits to `planning.md` for traceability.

### Security
- Enforced linting, static analysis, and vulnerability scans in CI/CD.
- Deployment blocked unless all quality gates pass.

---

## [0.0.1] - 2026-04-20
### Added
- Drafted `README.md` and `planning.md` templates.
- Established initial vision for agent workflow.
