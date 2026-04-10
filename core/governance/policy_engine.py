"""Deterministic runtime governance engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.decision.agent_descriptor import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)
from core.decision.task_intent import TaskIntent

from .policy_models import PolicyDecision, PolicyEvaluationContext
from .policy_registry import PolicyRegistry


class PolicyEngine:
    """Evaluate runtime governance rules after routing and before execution."""

    def __init__(self, *, policy_registry: PolicyRegistry | None = None) -> None:
        self.policy_registry = policy_registry or PolicyRegistry()

    def evaluate(
        self,
        task_intent: TaskIntent,
        agent_descriptor: AgentDescriptor | None,
        execution_context: PolicyEvaluationContext | Mapping[str, Any],
    ) -> PolicyDecision:
        """Return the winning deterministic policy decision for the selected action."""
        context = (
            execution_context
            if isinstance(execution_context, PolicyEvaluationContext)
            else PolicyEvaluationContext.model_validate(execution_context)
        )
        matched = self.policy_registry.get_applicable_policies(context)
        if not matched:
            return PolicyDecision(
                effect="allow",
                matched_rules=[],
                winning_rule_id=None,
                winning_priority=None,
                reason="no_policy_matched",
            )
        winner = matched[0]
        matched_rules = [rule.id for rule in matched]
        target = agent_descriptor.display_name if agent_descriptor is not None else "unselected-agent"
        return PolicyDecision(
            effect=winner.effect,
            matched_rules=matched_rules,
            winning_rule_id=winner.id,
            winning_priority=winner.priority,
            reason=f"{winner.id}: {winner.description} for {target}",
        )

    @staticmethod
    def build_execution_context(
        task_intent: TaskIntent,
        agent_descriptor: AgentDescriptor | None,
        *,
        task: Mapping[str, Any] | None = None,
        task_id: str | None = None,
        plan_id: str | None = None,
        step_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PolicyEvaluationContext:
        """Create a flattened evaluation context from the selected task and agent."""
        task_mapping = dict(task or {})
        extra = dict(metadata or {})
        hints = dict(task_intent.execution_hints or {})
        estimated_cost = _coerce_float(
            extra.get("estimated_cost")
            or hints.get("estimated_cost")
            or task_mapping.get("estimated_cost")
        )
        estimated_latency = _coerce_int(
            extra.get("estimated_latency")
            or hints.get("estimated_latency")
            or task_mapping.get("estimated_latency")
        )
        external_side_effect = _coerce_bool(
            extra.get("external_side_effect")
            if "external_side_effect" in extra
            else hints.get("external_side_effect", task_mapping.get("external_side_effect"))
        )
        return PolicyEvaluationContext(
            task_type=task_intent.task_type,
            task_summary=task_intent.description,
            task_id=task_id or str(task_mapping.get("task_id") or "") or None,
            plan_id=plan_id,
            step_id=step_id,
            required_capabilities=list(task_intent.required_capabilities),
            agent_id=agent_descriptor.agent_id if agent_descriptor is not None else None,
            source_type=agent_descriptor.source_type.value if agent_descriptor is not None else None,
            execution_kind=agent_descriptor.execution_kind.value if agent_descriptor is not None else None,
            estimated_cost=estimated_cost,
            estimated_latency=estimated_latency,
            is_local=_infer_locality(agent_descriptor, hints=hints, metadata=extra),
            risk_level=task_intent.risk.value,
            external_side_effect=external_side_effect,
            metadata={
                "task_domain": task_intent.domain,
                **task_mapping,
                **extra,
            },
        )


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return None


def _infer_locality(
    agent_descriptor: AgentDescriptor | None,
    *,
    hints: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> bool | None:
    explicit = metadata.get("is_local")
    if explicit is None:
        explicit = hints.get("is_local")
    explicit_bool = _coerce_bool(explicit)
    if explicit_bool is not None:
        return explicit_bool
    if agent_descriptor is None:
        return None
    if agent_descriptor.execution_kind == AgentExecutionKind.CLOUD_AGENT:
        return False
    if agent_descriptor.source_type == AgentSourceType.CODEX:
        return False
    if agent_descriptor.execution_kind in {
        AgentExecutionKind.LOCAL_PROCESS,
        AgentExecutionKind.SYSTEM_EXECUTOR,
    }:
        return True
    if agent_descriptor.source_type in {
        AgentSourceType.OPENHANDS,
        AgentSourceType.ADMINBOT,
        AgentSourceType.N8N,
        AgentSourceType.FLOWISE,
    }:
        return True
    return None
