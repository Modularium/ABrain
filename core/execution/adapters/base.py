"""Base types for execution adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.decision.agent_descriptor import AgentDescriptor
from core.models.errors import StructuredError
from core.model_context import ModelContext, TaskContext


class ExecutionResult(BaseModel):
    """Structured execution result produced by adapters and the engine."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    success: bool
    output: Any | None = None
    raw_output: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: StructuredError | None = None
    duration_ms: int | None = None
    cost: float | None = None


class BaseExecutionAdapter:
    """Base adapter contract for executing a task via an external agent."""

    adapter_name = "base"

    def validate(self, task: TaskContext | ModelContext | Mapping[str, Any], agent_descriptor: AgentDescriptor) -> None:
        """Validate that the adapter can execute the given task for the descriptor."""
        del task
        del agent_descriptor

    def execute(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        agent_descriptor: AgentDescriptor,
    ) -> ExecutionResult:
        raise NotImplementedError

    def task_text(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> str:
        """Extract a plain-text task description for external adapters."""
        if isinstance(task, ModelContext):
            if task.task_context is not None:
                text = self.task_text(task.task_context)
                return text or str(task.task or "")
            return str(task.task or "")
        if isinstance(task, TaskContext):
            return str(getattr(task.description, "text", task.description) or task.task_type or "")
        if isinstance(task, Mapping):
            return str(task.get("description") or task.get("task") or task.get("task_type") or "")
        raise TypeError(f"Unsupported task input: {type(task)!r}")

    def task_type(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> str:
        """Extract task type from supported task inputs."""
        if isinstance(task, ModelContext):
            return task.task_context.task_type if task.task_context else str(task.task or "analysis")
        if isinstance(task, TaskContext):
            return task.task_type
        if isinstance(task, Mapping):
            return str(task.get("task_type") or task.get("task") or "analysis")
        raise TypeError(f"Unsupported task input: {type(task)!r}")

    def task_preferences(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> dict[str, Any]:
        """Extract preference-like metadata from the task."""
        if isinstance(task, ModelContext):
            if task.task_context and isinstance(task.task_context.preferences, dict):
                return dict(task.task_context.preferences)
            return {}
        if isinstance(task, TaskContext):
            return dict(task.preferences or {})
        if isinstance(task, Mapping):
            preferences = task.get("preferences")
            return dict(preferences) if isinstance(preferences, Mapping) else {}
        raise TypeError(f"Unsupported task input: {type(task)!r}")
