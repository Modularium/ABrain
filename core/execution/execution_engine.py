"""Execution engine for routing decisions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.decision import AgentDescriptor, AgentRegistry, RoutingDecision
from core.models.errors import StructuredError
from core.model_context import ModelContext, TaskContext

from .adapters import ExecutionAdapterRegistry
from .adapters.base import ExecutionResult


class ExecutionEngine:
    """Execute a selected agent without re-running routing logic."""

    def __init__(self, *, adapter_registry: ExecutionAdapterRegistry | None = None) -> None:
        self.adapter_registry = adapter_registry or ExecutionAdapterRegistry()

    def execute(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        decision: RoutingDecision,
        descriptors: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
    ) -> ExecutionResult:
        if not decision.selected_agent_id:
            return ExecutionResult(
                agent_id="",
                success=False,
                error=StructuredError(
                    error_code="missing_selected_agent",
                    message="RoutingDecision did not select an agent",
                    details={"task_type": decision.task_type},
                ),
                metadata={"execution_engine": "v1"},
            )
        descriptor = self._resolve_descriptor(decision.selected_agent_id, descriptors)
        adapter = self.adapter_registry.resolve(descriptor)
        adapter.validate(task, descriptor)
        result = adapter.execute(task, descriptor)
        result.metadata.setdefault("execution_engine", "v1")
        result.metadata.setdefault("selected_agent_id", decision.selected_agent_id)
        result.metadata.setdefault("source_type", descriptor.source_type.value)
        result.metadata.setdefault("execution_kind", descriptor.execution_kind.value)
        result.metadata.setdefault("adapter_name", getattr(adapter, "adapter_name", adapter.__class__.__name__))
        return result

    def _resolve_descriptor(
        self,
        agent_id: str,
        descriptors: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
    ) -> AgentDescriptor:
        if isinstance(descriptors, AgentRegistry):
            descriptor = descriptors.get(agent_id)
            if descriptor is None:
                raise KeyError(f"Unknown agent_id in registry: {agent_id}")
            return descriptor
        if isinstance(descriptors, Mapping):
            descriptor = descriptors.get(agent_id)
            if descriptor is None:
                raise KeyError(f"Unknown agent_id in mapping: {agent_id}")
            return descriptor
        for descriptor in descriptors:
            if descriptor.agent_id == agent_id:
                return descriptor
        raise KeyError(f"Unknown agent_id in sequence: {agent_id}")
