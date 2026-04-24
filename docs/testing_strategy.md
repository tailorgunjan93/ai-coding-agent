# Testing Strategy

## Overview
The Tester Node ensures all generated code is **validated continuously** before deployment.  
It auto-generates tests, runs them in a sandbox, and corrects code until all tests pass.

---

## Responsibilities
1. **Unit Tests**
   - Validate individual functions and classes.
   - Frameworks:
     - Python → pytest
     - .NET → xUnit
     - JS/TS → Jest

2. **Integration Tests**
   - Validate workflows across multiple modules.
   - Ensure DB, API, and service layers interact correctly.

3. **Edge-Case Tests**
   - Validate behavior under invalid inputs, stress conditions, and boundary values.
   - Examples: empty strings, null values, large datasets, concurrent requests.

4. **Continuous Correction Loop**
   - Run tests in sandbox.
   - Collect results.
   - Feed failures back into Lifecycle Node.
   - Regenerate/fix code until all tests pass.

---

## Workflow Integration
- **Planning Stage**: `planning.md` specifies testing requirements.
- **Code Generation Stage**: Agent auto-generates tests alongside code.
- **Execution Stage**: Tester Node runs tests in sandbox.
- **Correction Stage**: Failures trigger code fixes automatically.
- **Approval Stage**: Human reviewer confirms test coverage and results.

---

## Tools Used
- **pytest** (Python)
- **xUnit** (.NET)
- **Jest** (JavaScript/TypeScript)
- **Sandbox Runner** for isolated execution
- **Coverage Reports** stored in `/tests/coverage`

---

## Fail-Safe Rules
- Deployment blocked if:
  - Unit tests fail.
  - Integration tests fail.
  - Edge-case tests fail.
- Override requires explicit human approval documented in `planning.md`.

---

## Recommendations
- Always link test results to commits in Git.
- Store coverage reports in `/tests/coverage`.
- Treat testing as a **non-negotiable quality gate**.
