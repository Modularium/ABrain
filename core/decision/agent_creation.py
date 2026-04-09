"""Agent creation helpers for low-confidence routing outcomes."""

from __future__ import annotations

import re
from uuid import uuid4

from core.model_context import ModelContext, TaskContext

from .agent_descriptor import (
    AgentAvailability,
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentLatencyProfile,
    AgentSourceType,
    AgentTrustLevel,
)
from .agent_registry import AgentRegistry
from .task_intent import TaskIntent


class AgentCreationEngine:
    """Create and register internal agent descriptors for uncovered tasks."""

    def __init__(self, *, threshold: float = 0.55) -> None:
        self.threshold = threshold

    def should_create_agent(self, score: float | None) -> bool:
        return score is None or score < self.threshold

    def create_agent_from_task(
        self,
        task: TaskContext | ModelContext | dict,
        capabilities: list[str],
        *,
        registry: AgentRegistry | None = None,
    ) -> AgentDescriptor:
        intent = self._infer_intent(task)
        source_type, execution_kind = self._choose_adapter(intent)
        slug = self._slugify(intent.task_type or intent.domain or "task")
        descriptor = AgentDescriptor(
            agent_id=f"generated-{slug}-{uuid4().hex[:8]}",
            display_name=f"Generated {intent.domain.title()} Agent",
            source_type=source_type,
            execution_kind=execution_kind,
            capabilities=capabilities,
            trust_level=self._default_trust_level(source_type),
            cost_profile=self._default_cost_profile(source_type),
            latency_profile=self._default_latency_profile(source_type),
            availability=AgentAvailability.ONLINE,
            editable_in_flowise=source_type == AgentSourceType.FLOWISE,
            metadata={
                "created_by": "agent_creation_v1",
                "created_from_task_type": intent.task_type,
                "created_from_domain": intent.domain,
                "generated": True,
            },
        )
        if registry is not None:
            registry.register(descriptor)
        return descriptor

    def _infer_intent(self, task: TaskContext | ModelContext | dict) -> TaskIntent:
        if isinstance(task, ModelContext) and task.task_context is not None:
            return self._infer_intent(task.task_context)
        if isinstance(task, TaskContext):
            preferences = dict(task.preferences or {})
            return TaskIntent(
                task_type=task.task_type,
                domain=str(preferences.get("domain") or self._infer_domain(task.task_type)),
                required_capabilities=list(preferences.get("required_capabilities") or []),
                execution_hints=dict(preferences.get("execution_hints") or {}),
                description=str(getattr(task.description, "text", task.description) or "") or None,
            )
        if isinstance(task, dict):
            preferences = dict(task.get("preferences") or {})
            task_type = str(task.get("task_type") or task.get("task") or "analysis")
            return TaskIntent(
                task_type=task_type,
                domain=str(preferences.get("domain") or self._infer_domain(task_type)),
                required_capabilities=list(preferences.get("required_capabilities") or []),
                execution_hints=dict(preferences.get("execution_hints") or {}),
                description=str(task.get("description") or "") or None,
            )
        raise TypeError(f"Unsupported task input for agent creation: {type(task)!r}")

    def _choose_adapter(self, intent: TaskIntent) -> tuple[AgentSourceType, AgentExecutionKind]:
        preferred_source = intent.execution_hints.get("preferred_source_type")
        if isinstance(preferred_source, str):
            try:
                source_type = AgentSourceType(preferred_source)
            except ValueError:
                source_type = None
            else:
                if source_type == AgentSourceType.ADMINBOT:
                    return source_type, AgentExecutionKind.SYSTEM_EXECUTOR
                if source_type == AgentSourceType.OPENHANDS:
                    return source_type, AgentExecutionKind.LOCAL_PROCESS
                if source_type in {AgentSourceType.CODEX, AgentSourceType.CLAUDE_CODE}:
                    return source_type, AgentExecutionKind.CLOUD_AGENT
                if source_type in {AgentSourceType.FLOWISE, AgentSourceType.N8N}:
                    return source_type, AgentExecutionKind.WORKFLOW_ENGINE
        if intent.domain == "system":
            return AgentSourceType.ADMINBOT, AgentExecutionKind.SYSTEM_EXECUTOR
        if intent.domain == "workflow":
            return AgentSourceType.FLOWISE, AgentExecutionKind.WORKFLOW_ENGINE
        if intent.domain == "code":
            return AgentSourceType.OPENHANDS, AgentExecutionKind.LOCAL_PROCESS
        return AgentSourceType.OPENHANDS, AgentExecutionKind.LOCAL_PROCESS

    def _default_trust_level(self, source_type: AgentSourceType) -> AgentTrustLevel:
        if source_type == AgentSourceType.ADMINBOT:
            return AgentTrustLevel.TRUSTED
        return AgentTrustLevel.SANDBOXED

    def _default_cost_profile(self, source_type: AgentSourceType) -> AgentCostProfile:
        if source_type in {AgentSourceType.CODEX, AgentSourceType.CLAUDE_CODE}:
            return AgentCostProfile.MEDIUM
        return AgentCostProfile.LOW

    def _default_latency_profile(self, source_type: AgentSourceType) -> AgentLatencyProfile:
        if source_type in {AgentSourceType.CODEX, AgentSourceType.CLAUDE_CODE}:
            return AgentLatencyProfile.BACKGROUND
        return AgentLatencyProfile.INTERACTIVE

    def _infer_domain(self, task_type: str) -> str:
        if task_type.startswith("system") or task_type.startswith("service"):
            return "system"
        if task_type.startswith("workflow"):
            return "workflow"
        if task_type.startswith("code"):
            return "code"
        return "analysis"

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "task"
