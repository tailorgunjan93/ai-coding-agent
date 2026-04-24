# Release Strategy

## Overview
This document defines how releases are managed for the AI-powered coding agent.  
It ensures consistency, traceability, and reliability across all versions.

---

## Versioning
- The project follows **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`
  - **MAJOR** → Breaking changes (e.g., architecture overhaul).
  - **MINOR** → New features added in a backward-compatible way.
  - **PATCH** → Bug fixes, security updates, or minor improvements.

---

## Release Types
1. **Stable Releases**
   - Tagged as `vX.Y.Z`.
   - Published after all CI/CD pipelines pass (build, lint, test, security).
   - Require Maintainer approval.

2. **Pre-Releases**
   - Tagged as `vX.Y.Z-alpha`, `vX.Y.Z-beta`, or `vX.Y.Z-rc`.
   - Used for testing new features before stable release.
   - May be published to a separate branch or registry.

3. **Hotfixes**
   - Tagged as `vX.Y.Z+hotfix`.
   - Applied directly to stable releases for urgent bug/security fixes.
   - Must include clear documentation in `CHANGELOG.md`.

---

## Release Workflow
1. **Planning**
   - Update `planning.md` with release scope.
   - Link commits to approved plan.

2. **Development**
   - Work on feature branches (`feat/`, `fix/`, `docs/`, `ci/`).
   - Ensure commits follow semantic rules.

3. **Testing**
   - Run unit, integration, and edge-case tests.
   - Generate coverage reports in `/tests/coverage`.

4. **Security**
   - Run linting, static analysis, and vulnerability scans.
   - Block release if critical issues remain.

5. **Approval**
   - Maintainers review PRs and approve release candidate.

6. **Tagging**
   - Tag release in Git:
     ```bash
     git tag vX.Y.Z
     git push origin vX.Y.Z
     ```

7. **Publishing**
   - CI/CD pipelines publish extension via `vsce`.
   - Artifacts stored for traceability.

---

## Documentation
- Update `CHANGELOG.md` with release notes.
- Update `roadmap.md` to reflect completed milestones.
- Document architectural changes in `architecture.md`.

---

## Recommendations
- Cut releases at the end of each sprint or milestone.
- Use pre-releases for experimental features.
- Treat hotfixes as urgent exceptions, not routine practice.
