"""
Test Result Models - Pydantic schemas for test execution results.

These models capture test suite execution results including
individual test cases, coverage metrics, and summary statistics.
"""

from typing import Any
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class TestStatus(Enum):
    """Status of an individual test case."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestCase(BaseModel):
    """A single test case result."""
    id: str = Field(description="Unique test case identifier")
    name: str = Field(description="Test case name")
    status: TestStatus = Field(description="Test execution status")
    duration_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    error_message: str | None = Field(default=None, description="Error message if failed")
    file_path: str | None = Field(default=None, description="Test file path")
    line_number: int | None = Field(default=None, description="Line number in test file")


class TestSuite(BaseModel):
    """A collection of test cases (one test file)."""
    name: str = Field(description="Test suite name")
    total_tests: int = Field(default=0, description="Total number of tests")
    passed: int = Field(default=0, description="Number of passed tests")
    failed: int = Field(default=0, description="Number of failed tests")
    skipped: int = Field(default=0, description="Number of skipped tests")
    errors: int = Field(default=0, description="Number of errored tests")
    duration_ms: float = Field(default=0.0, description="Total suite execution time")
    test_cases: list[TestCase] = Field(default_factory=list, description="Individual test results")
    coverage_percent: float | None = Field(default=None, description="Code coverage percentage")


class TestSummary(BaseModel):
    """Aggregated test summary across all suites."""
    total_suites: int = Field(default=0)
    total_tests: int = Field(default=0)
    total_passed: int = Field(default=0)
    total_failed: int = Field(default=0)
    total_skipped: int = Field(default=0)
    total_errors: int = Field(default=0)
    total_duration_ms: float = Field(default=0.0)
    overall_coverage_percent: float | None = Field(default=None)
    success: bool = Field(default=False, description="True if all tests passed")

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100


class TestResult(BaseModel):
    """
    Complete test execution result.

    Captures all test suites, individual cases, and summary
    metrics for a single test run.
    """
    session_id: str = Field(description="Agent session ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    language: str = Field(default="python", description="Programming language")
    framework: str = Field(default="pytest", description="Test framework used")
    suites: list[TestSuite] = Field(default_factory=list, description="Test suite results")
    summary: TestSummary = Field(default_factory=TestSummary, description="Aggregated summary")
    command: str = Field(default="", description="Command used to run tests")
    raw_output: str = Field(default="", description="Raw test runner output")

    def compute_summary(self) -> None:
        """Recompute summary from suite data."""
        self.summary = TestSummary(
            total_suites=len(self.suites),
            total_tests=sum(s.total_tests for s in self.suites),
            total_passed=sum(s.passed for s in self.suites),
            total_failed=sum(s.failed for s in self.suites),
            total_skipped=sum(s.skipped for s in self.suites),
            total_errors=sum(s.errors for s in self.suites),
            total_duration_ms=sum(s.duration_ms for s in self.suites),
            success=all(s.failed == 0 and s.errors == 0 for s in self.suites),
        )
