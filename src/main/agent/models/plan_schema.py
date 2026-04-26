"""
Plan Schema - Pydantic models for planning output.

These models define the structure of planning documents produced
by the PlanningNode and consumed by other nodes.
"""

from typing import NotRequired
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class Priority(Enum):
    """Task priority levels."""
    LOW = 0
    MEDIUM = 5
    HIGH = 7
    CRITICAL = 10


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class PlanTask(BaseModel):
    """A task within the execution plan."""
    id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Human-readable task description")
    priority: int = Field(default=5, ge=0, le=10, description="Priority 0-10")
    estimated_hours: NotRequired[float] = Field(default=None, ge=0)
    actual_hours: NotRequired[float] = Field(default=None, ge=0)
    depends_on: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    skills_required: list[str] = Field(default_factory=list)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    assignee: NotRequired[str]
    created_at: NotRequired[datetime]
    completed_at: NotRequired[datetime]
    error: NotRequired[str]

    @field_validator("id")
    @classmethod
    def id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty")
        return v


class RiskLikelihood(Enum):
    """Risk likelihood levels."""
    RARE = "rare"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    CERTAIN = "certain"


class RiskImpact(Enum):
    """Risk impact levels."""
    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"


class PlanRisk(BaseModel):
    """A risk identified in the plan."""
    id: str = Field(..., description="Unique risk identifier")
    description: str = Field(..., description="Risk description")
    likelihood: RiskLikelihood
    impact: RiskImpact
    mitigation: str = Field(..., description="Mitigation strategy")
    contingency: NotRequired[str] = Field(default=None, description="Contingency plan")
    owner: NotRequired[str]


class Technology(BaseModel):
    """A technology in the tech stack."""
    name: str = Field(..., description="Technology name")
    version: NotRequired[str] = Field(default=None, description="Version constraint")
    purpose: str = Field(..., description="Why this technology is chosen")


class Dependency(BaseModel):
    """A dependency between tasks."""
    source_id: str = Field(..., description="Source task ID")
    target_id: str = Field(..., description="Target task ID")
    dependency_type: str = Field(default="finish_to_start", description="Type of dependency")


class ApprovalInfo(BaseModel):
    """Human approval information."""
    required: bool = Field(default=True, description="Whether approval is required")
    status: str = Field(default="pending", description="pending, approved, rejected")
    approved_by: NotRequired[str]
    approved_at: NotRequired[datetime]
    comments: NotRequired[str]


class PlanSchema(BaseModel):
    """
    Complete plan schema produced by the PlanningNode.

    This defines the structure of planning.md documents and serves as
    the contract between planning and downstream nodes.
    """
    project_name: str = Field(..., description="Name of the project")
    version: str = Field(default="1.0.0", description="Plan version")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Requirements & Architecture
    requirements: list[str] = Field(..., description="User requirements")
    architecture_overview: str = Field(..., description="High-level architecture description")
    tech_stack: list[Technology] = Field(default_factory=list)
    design_patterns: list[str] = Field(default_factory=list)

    # Task breakdown
    tasks: list[PlanTask] = Field(..., description="Execution tasks")
    dependencies: list[Dependency] = Field(default_factory=list, description="Task dependencies")

    # Risk management
    risks: list[PlanRisk] = Field(default_factory=list)

    # Human approval gate
    human_approval: ApprovalInfo = Field(default_factory=ApprovalInfo)

    # Output paths
    planning_md_path: NotRequired[str] = Field(default=None, description="Path to planning.md")
    code_graph_path: NotRequired[str] = Field(default=None, description="Path to code_graph.json")
    data_flow_path: NotRequired[str] = Field(default=None, description="Path to data_flow.json")

    # Metadata
    metadata: dict[str, str] = Field(default_factory=dict)

    def get_task_by_id(self, task_id: str) -> PlanTask | None:
        """Find a task by its ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_root_tasks(self) -> list[PlanTask]:
        """Get tasks with no dependencies (entry points)."""
        task_ids = {t.id for t in self.tasks}
        for t in self.tasks:
            if t.depends_on:
                # Filter to only valid depends_on that exist in task list
                pass
        # Root tasks are those that no other task depends on
        dependent_ids = {dep.target_id for dep in self.dependencies}
        return [t for t in self.tasks if t.id not in dependent_ids]

    def topological_sort(self) -> list[PlanTask]:
        """Return tasks in dependency order."""
        sorted_tasks: list[PlanTask] = []
        remaining = {t.id for t in self.tasks}
        completed = set()

        while remaining:
            # Find tasks whose dependencies are all completed
            ready = [
                t for t in self.tasks
                if t.id in remaining
                and all(dep in completed for dep in t.depends_on)
            ]

            if not ready:
                # Circular dependency or missing task
                remaining_task = next((t for t in self.tasks if t.id in remaining), None)
                raise ValueError(f"Circular or missing dependency detected for task: {remaining_task}")

            sorted_tasks.extend(ready)
            completed.update(t.id for t in ready)
            remaining.difference_update(completed)

        return sorted_tasks
