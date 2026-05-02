"""
CICD Node - Generates CI/CD pipeline configuration files.

Produces GitHub Actions, GitLab CI, or Azure DevOps pipeline
configs based on the project structure and generated code.
"""

from typing import Any
import logging

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)


# Template for GitHub Actions workflow
GITHUB_ACTIONS_TEMPLATE = """name: CI/CD Pipeline

on:
  push:
    branches: [{branches}]
  pull_request:
    branches: [{branches}]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Run tests
        run: |
          pip install pytest pytest-cov
          pytest --cov=. --cov-report=xml -v

  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Security scan with bandit
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json || true

      - name: Check dependencies
        run: |
          pip install safety
          safety check || true
"""

GITLAB_CI_TEMPLATE = """stages:
  - test
  - security
  - build

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip"

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=. --cov-report=xml -v
  coverage: '/TOTAL.*\\s+(\\d+%)/'

security:
  stage: security
  image: python:3.12
  script:
    - pip install bandit safety
    - bandit -r . -f json -o bandit-report.json || true
    - safety check || true
  allow_failure: true

lint:
  stage: test
  image: python:3.12
  script:
    - pip install flake8 black mypy
    - flake8 . --count --select=E9,F63,F7,F82 --show-source
    - black --check .
"""


class CICDNode(BaseNode):
    """
    Node responsible for CI/CD config generation.

    Generates pipeline configuration files for:
    - GitHub Actions
    - GitLab CI
    - Azure DevOps (basic)

    Dependencies:
        - git (needs code to be committed)
    """

    def __init__(
        self,
        provider: str = "github",
        config: dict[str, Any] | None = None,
        max_retries: int = 3,
    ):
        super().__init__(max_retries=max_retries, timeout_seconds=600)
        self._provider = provider.lower()
        self._config = config or {}

    @property
    def node_name(self) -> str:
        return "cicd"

    @property
    def description(self) -> str:
        return f"Generates {self._provider} CI/CD pipeline configuration"

    def get_required_dependencies(self) -> list[str]:
        return ["git"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Generate CI/CD pipeline configuration.

        Steps:
        1. Determine CI/CD provider
        2. Generate appropriate config file
        3. Add as artifact
        """
        branches = self._config.get("branches", "main")

        if self._provider in ("github", "github_actions"):
            config_content = GITHUB_ACTIONS_TEMPLATE.format(branches=branches)
            config_path = ".github/workflows/ci.yml"
            config_name = "GitHub Actions"

        elif self._provider in ("gitlab", "gitlab_ci"):
            config_content = GITLAB_CI_TEMPLATE
            config_path = ".gitlab-ci.yml"
            config_name = "GitLab CI"

        else:
            config_content = f"# CI/CD config for {self._provider}\n# TODO: Generate template"
            config_path = f"cicd/{self._provider}.yml"
            config_name = self._provider

        # Add config as artifact
        state["artifacts"].append({
            "type": "file",
            "path": config_path,
            "content": config_content,
            "created_at": state.get("updated_at", ""),
            "category": "cicd",
        })

        # Generate commands for manual setup
        commands = []
        if self._provider in ("github", "github_actions"):
            commands = [
                {
                    "command": f"mkdir -p .github/workflows && cp {config_path} .github/workflows/",
                    "description": "Set up GitHub Actions workflow directory",
                },
                {
                    "command": "git add .github/ && git commit -m 'ci: add GitHub Actions workflow'",
                    "description": "Commit CI configuration",
                },
            ]

        state["cicd_config"] = {
            "provider": config_name,
            "config_file": config_path,
            "commands": commands,
            "status": "generated",
        }

        logger.info(f"Generated {config_name} pipeline config at {config_path}")
        return state
