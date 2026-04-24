# CI/CD Integration Strategy

## Overview
This project supports **three major CI/CD platforms**:
- GitHub Actions
- GitLab CI/CD
- Azure DevOps Pipelines

Each pipeline enforces **quality gates** before deployment:
- Build → compile extension
- Lint → enforce coding standards
- Test → run unit, integration, and edge-case tests
- Security → run vulnerability scans
- Deploy → publish to VS Code Marketplace (only if all jobs succeed)

---

## GitHub Actions
- File: `.github/workflows/github-actions.yml`
- Best for: Open-source projects hosted on GitHub.
- Key Features:
  - Triggered on `push` and `pull_request`.
  - Jobs: build, lint, test, security, deploy.
  - Deploys via `vsce publish`.

---

## GitLab CI/CD
- File: `/ci/gitlab-ci.yml`
- Best for: Teams using GitLab for private or enterprise repos.
- Key Features:
  - Stages: build, lint, test, security, deploy.
  - Uses Node.js Docker images.
  - Artifacts stored for build and coverage.
  - Deploy stage runs only on `main`.

---

## Azure DevOps Pipelines
- File: `/ci/azure-pipelines.yml`
- Best for: Enterprise teams already on Azure DevOps.
- Key Features:
  - Stages: Build, Lint, Test, Security, Deploy.
  - Uses `NodeTool` task for Node.js setup.
  - Condition: deploy only if all prior stages succeed.
  - Publishes via `vsce publish`.

---

## Unified Strategy
- **Consistency**: All pipelines follow the same stages and quality gates.
- **Fail-safe Deployment**: Deploy stage runs only if build, lint, test, and security succeed.
- **Extensibility**: Add DB migrations, container builds, or cloud deploy steps as needed.
- **Human-in-the-loop**: Deployment can be gated by manual approval in each platform.
- **Traceability**: Commits linked to `planning.md` ensure CI/CD runs are tied to approved plans.

---

## Recommendations
- Use **GitHub Actions** for open-source/public repos.
- Use **GitLab CI/CD** for private repos or enterprise GitLab setups.
- Use **Azure DevOps** for enterprise teams already invested in Azure ecosystem.
- Keep all three configs in `/ci/` for maximum portability.
