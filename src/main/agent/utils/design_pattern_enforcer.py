"""
Design Pattern Enforcer - AST-based linting for SOLID, DRY, KISS principles.

This module provides utilities to analyze Python code and detect violations
of design principles using AST (Abstract Syntax Tree) analysis.
"""

from typing import TypedDict
import ast
from dataclasses import dataclass
from enum import Enum
import re


class ViolationSeverity(Enum):
    """Severity levels for design pattern violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ViolationRule(Enum):
    """Design pattern rules."""
    SINGLE_RESPONSIBILITY = "single_responsibility"
    OPEN_CLOSED = "open_closed"
    LISKOV_SUBSTITUTION = "liskov_substitution"
    INTERFACE_SEGREGATION = "interface_segregation"
    DEPENDENCY_INVERSION = "dependency_inversion"
    DRY = "dry"
    KISS = "kiss"
    YAGNI = "yagni"
    GOD_CLASS = "god_class"
    LONG_METHOD = "long_method"
    DEAD_CODE = "dead_code"
    CYCLE_IMPORT = "cycle_import"


@dataclass
class Violation:
    """A design pattern violation."""
    rule: ViolationRule
    severity: ViolationSeverity
    message: str
    file_path: str
    line_number: int
    column: int
    suggestion: str | None = None
    code_snippet: str | None = None


class DesignPatternEnforcer:
    """
    Analyzes Python code for design pattern violations.

    Uses AST parsing to detect violations of SOLID, DRY, KISS principles.
    """

    def __init__(
        self,
        rules: list[ViolationRule] | None = None,
        max_method_lines: int = 50,
        max_cyclomatic_complexity: int = 10,
    ):
        self._rules = rules or list(ViolationRule)
        self._max_method_lines = max_method_lines
        self._max_complexity = max_cyclomatic_complexity

    def analyze_file(self, file_path: str) -> list[Violation]:
        """Analyze a Python file for violations."""
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        return self.analyze_source(source, file_path)

    def analyze_source(self, source: str, file_path: str = "<unknown>") -> list[Violation]:
        """Analyze Python source code for violations."""
        violations = []
        try:
            tree = ast.parse(source)
            violations.extend(self._check_single_responsibility(tree, source, file_path))
            violations.extend(self._check_long_methods(tree, source, file_path))
            violations.extend(self._check_god_class(tree, source, file_path))
            violations.extend(self._check_dead_code(tree, source, file_path))
        except SyntaxError as e:
            violations.append(Violation(
                rule=ViolationRule.DRY,
                severity=ViolationSeverity.HIGH,
                message=f"Syntax error: {e}",
                file_path=file_path,
                line_number=e.lineno or 0,
                column=e.offset or 0,
                suggestion="Fix syntax errors before analysis",
            ))
        return violations

    def _get_source_line(self, source: str, line_number: int) -> str:
        """Get source line by line number."""
        lines = source.split("\n")
        if 0 < line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""

    def _check_single_responsibility(self, tree: ast.AST, source: str, file_path: str) -> list[Violation]:
        """Check for Single Responsibility Principle violations."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                public_methods = [
                    m for m in node.body
                    if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")
                ]
                if len(public_methods) > 20:
                    prefixes = set()
                    for method in public_methods:
                        match = re.match(r'^([a-z]+)([A-Z])', method.name)
                        if match:
                            prefixes.add(match.group(1))
                    if len(prefixes) >= 3:
                        violations.append(Violation(
                            rule=ViolationRule.SINGLE_RESPONSIBILITY,
                            severity=ViolationSeverity.MEDIUM,
                            message=f"Class '{node.name}' may have too many responsibilities ({len(prefixes)} different action groups)",
                            file_path=file_path,
                            line_number=node.lineno or 0,
                            column=node.col_offset or 0,
                            suggestion=f"Consider splitting into {len(prefixes)} separate classes",
                            code_snippet=self._get_source_line(source, node.lineno or 0),
                        ))
        return violations

    def _check_long_methods(self, tree: ast.AST, source: str, file_path: str) -> list[Violation]:
        """Check for Long Method anti-pattern."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, "body") and len(node.body) > self._max_method_lines:
                    violations.append(Violation(
                        rule=ViolationRule.LONG_METHOD,
                        severity=ViolationSeverity.MEDIUM,
                        message=f"Method '{node.name}' is too long ({len(node.body)} statements, max recommended: {self._max_method_lines})",
                        file_path=file_path,
                        line_number=node.lineno or 0,
                        column=node.col_offset or 0,
                        suggestion="Consider breaking this method into smaller, focused methods",
                        code_snippet=self._get_source_line(source, node.lineno or 0),
                    ))
        return violations

    def _check_god_class(self, tree: ast.AST, source: str, file_path: str) -> list[Violation]:
        """Check for God Class anti-pattern."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                all_methods = [
                    m for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                init_method = None
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        init_method = item
                        break
                instance_vars = 0
                if init_method:
                    for stmt in ast.walk(init_method):
                        if isinstance(stmt, ast.Assign):
                            if any(isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self"
                                   for target in stmt.targets):
                                instance_vars += 1
                score = len(all_methods) * 2 + instance_vars * 3
                if score > 100:
                    violations.append(Violation(
                        rule=ViolationRule.GOD_CLASS,
                        severity=ViolationSeverity.HIGH,
                        message=f"Class '{node.name}' appears to be a God Class (score: {score})",
                        file_path=file_path,
                        line_number=node.lineno or 0,
                        column=node.col_offset or 0,
                        suggestion="Consider splitting into smaller, focused classes",
                        code_snippet=self._get_source_line(source, node.lineno or 0),
                    ))
        return violations

    def _check_dead_code(self, tree: ast.AST, source: str, file_path: str) -> list[Violation]:
        """Check for dead/unreachable code."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") or node.name.startswith("__"):
                    continue
                if len(node.body) == 1:
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Raise):
                        if stmt.exc and isinstance(stmt.exc, ast.Call):
                            if isinstance(stmt.exc.func, ast.Name) and stmt.exc.func.id == "NotImplementedError":
                                violations.append(Violation(
                                    rule=ViolationRule.DEAD_CODE,
                                    severity=ViolationSeverity.LOW,
                                    message=f"Method '{node.name}' raises NotImplementedError",
                                    file_path=file_path,
                                    line_number=node.lineno or 0,
                                    column=node.col_offset or 0,
                                    suggestion="Either implement the method or remove it",
                                    code_snippet=self._get_source_line(source, node.lineno or 0),
                                ))
        return violations


class LintResult(TypedDict):
    """Result from running lint checks."""
    file_path: str
    violations: list[dict]
    total_violations: int
    error_count: int
    warning_count: int
    info_count: int


def lint_file(file_path: str) -> LintResult:
    """Convenience function to lint a single file."""
    enforcer = DesignPatternEnforcer()
    violations = enforcer.analyze_file(file_path)
    return format_lint_result(file_path, violations)


def format_lint_result(file_path: str, violations: list[Violation]) -> LintResult:
    """Format violations into a LintResult."""
    violation_dicts = []
    for v in violations:
        violation_dicts.append({
            "rule": v.rule.value,
            "severity": v.severity.value,
            "message": v.message,
            "line": v.line_number,
            "column": v.column,
            "suggestion": v.suggestion,
            "code": v.code_snippet,
        })
    return LintResult(
        file_path=file_path,
        violations=violation_dicts,
        total_violations=len(violations),
        error_count=sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL),
        warning_count=sum(1 for v in violations if v.severity in (ViolationSeverity.HIGH, ViolationSeverity.MEDIUM)),
        info_count=sum(1 for v in violations if v.severity == ViolationSeverity.LOW),
    )
