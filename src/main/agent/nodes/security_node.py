"""
Security Node - Performs security analysis on generated code.

Analyzes code for vulnerabilities, insecure patterns, hardcoded secrets,
and OWASP Top 10 issues. Generates commands for scanning tools.
"""

from typing import Any
import re
import logging

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)

# Patterns for common security issues
INSECURE_PATTERNS = {
    "eval_exec": {
        "pattern": r"\b(eval|exec)\s*\(",
        "severity": "critical",
        "message": "Use of eval()/exec() — potential code injection",
    },
    "sql_injection": {
        "pattern": r"(f\".*SELECT|f\".*INSERT|f\".*DELETE|f\".*UPDATE|\.format\(.*SELECT)",
        "severity": "critical",
        "message": "Possible SQL injection — use parameterized queries",
    },
    "hardcoded_password": {
        "pattern": r"(password|secret|api_key|token)\s*=\s*[\"'][^\"']{4,}[\"']",
        "severity": "high",
        "message": "Hardcoded credential — use environment variables",
    },
    "shell_injection": {
        "pattern": r"os\.system\(|subprocess\.(call|run|Popen)\(.*shell\s*=\s*True",
        "severity": "high",
        "message": "Shell injection risk — avoid shell=True",
    },
    "weak_crypto": {
        "pattern": r"\b(md5|sha1)\b",
        "severity": "medium",
        "message": "Weak hash algorithm — use SHA-256 or bcrypt",
    },
    "debug_mode": {
        "pattern": r"(DEBUG\s*=\s*True|debug\s*=\s*True|\.run\(debug=True\))",
        "severity": "medium",
        "message": "Debug mode enabled — disable in production",
    },
    "pickle_unsafe": {
        "pattern": r"pickle\.(loads|load)\(",
        "severity": "high",
        "message": "Unsafe pickle deserialization — use JSON instead",
    },
    "open_cors": {
        "pattern": r"allow_origins\s*=\s*\[\s*[\"']\*[\"']\s*\]",
        "severity": "medium",
        "message": "CORS allows all origins — restrict to specific domains",
    },
}


class SecurityNode(BaseNode):
    """
    Node responsible for security analysis.

    Scans generated code for vulnerabilities using pattern matching
    and generates commands for security scanning tools (bandit, safety).

    Dependencies:
        - model (needs generated code)
    """

    def __init__(
        self,
        llm_wrapper: Any | None = None,
        rules_dir: str | None = None,
        max_retries: int = 2,
    ):
        super().__init__(max_retries=max_retries, timeout_seconds=180)
        self._llm = llm_wrapper
        self._rules_dir = rules_dir

    @property
    def node_name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Performs security analysis and vulnerability scanning"

    def get_required_dependencies(self) -> list[str]:
        return ["model"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Perform security analysis on generated code.

        Steps:
        1. Get generated files from state artifacts
        2. Run pattern-based static analysis
        3. Generate scanner commands (bandit, safety)
        4. Record findings in state
        """
        artifacts = state.get("artifacts", [])
        all_findings = []
        scan_commands = []

        # Scan each code artifact
        for artifact in artifacts:
            if artifact.get("type") != "file":
                continue

            content = artifact.get("content", "")
            file_path = artifact.get("path", "unknown")
            findings = self._scan_code(content, file_path)
            all_findings.extend(findings)

        # Generate scanner commands
        scan_commands.append({
            "tool": "bandit",
            "command": "bandit -r . -f json -o security_report.json",
            "description": "Python security linter (SAST)",
        })
        scan_commands.append({
            "tool": "safety",
            "command": "safety check --json --output safety_report.json",
            "description": "Check dependencies for known vulnerabilities",
        })
        scan_commands.append({
            "tool": "semgrep",
            "command": "semgrep --config=auto . --json > semgrep_report.json",
            "description": "Multi-language static analysis",
        })

        # Determine if any critical findings block the pipeline
        critical_count = sum(1 for f in all_findings if f["severity"] == "critical")
        high_count = sum(1 for f in all_findings if f["severity"] == "high")

        security_report = {
            "findings": all_findings,
            "total_findings": len(all_findings),
            "critical": critical_count,
            "high": high_count,
            "medium": len(all_findings) - critical_count - high_count,
            "scan_commands": scan_commands,
            "blocked": critical_count > 0,
            "recommendation": (
                "BLOCKED: Critical vulnerabilities found. Fix before proceeding."
                if critical_count > 0
                else "PASSED: No critical issues. Review high/medium findings."
            ),
        }

        state["security_report"] = security_report

        if critical_count > 0:
            logger.warning(f"Security scan found {critical_count} critical issues")
        else:
            logger.info(f"Security scan passed ({len(all_findings)} non-critical findings)")

        return state

    def _scan_code(self, code: str, file_path: str) -> list[dict[str, Any]]:
        """Scan code content for insecure patterns."""
        findings = []
        lines = code.split("\n")

        for rule_id, rule in INSECURE_PATTERNS.items():
            for line_num, line in enumerate(lines, 1):
                if re.search(rule["pattern"], line, re.IGNORECASE):
                    findings.append({
                        "rule_id": rule_id,
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "file": file_path,
                        "line": line_num,
                        "line_content": line.strip(),
                    })

        return findings
