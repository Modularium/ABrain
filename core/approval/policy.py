"""Deterministic approval policy for sensitive plan steps."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.decision.capabilities import CapabilityRisk
from core.decision.plan_models import PlanStep


_MUTATING_CAPABILITIES = {
    "code.generate",
    "code.refactor",
    "repo.modify",
    "workflow.execute",
    "workflow.automation",
}
_HIGH_RISK_CAPABILITIES = {
    "system.write",
    "system.execute",
    "repo.modify",
    "workflow.execute",
    "workflow.automation",
}
_READ_ONLY_SYSTEM_CAPABILITIES = {
    "system.read",
    "system.status",
    "system.health",
}


class ApprovalCheck(BaseModel):
    """Structured result of approval policy evaluation."""

    model_config = ConfigDict(extra="forbid")

    required: bool
    reason: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    proposed_action_summary: str


class ApprovalPolicy:
    """Deterministically decide whether a step requires human approval."""

    def evaluate(
        self,
        step: PlanStep,
        agent_descriptor: AgentDescriptor | None,
        *,
        task: dict[str, Any] | None = None,
    ) -> ApprovalCheck:
        del task
        matched_rules: list[str] = []
        capabilities = set(step.required_capabilities)
        metadata = step.metadata

        if bool(metadata.get("requires_human_approval")):
            matched_rules.append("step_metadata_requires_human_approval")
        if step.risk in {CapabilityRisk.HIGH, CapabilityRisk.CRITICAL}:
            matched_rules.append(f"step_risk_{step.risk.value}")
        if bool(metadata.get("risky_operation")):
            matched_rules.append("step_metadata_risky_operation")
        if bool(metadata.get("external_side_effect")):
            matched_rules.append("step_metadata_external_side_effect")
        if capabilities & _HIGH_RISK_CAPABILITIES:
            matched_rules.append("high_risk_capability")

        if agent_descriptor is not None:
            if (
                agent_descriptor.execution_kind == AgentExecutionKind.SYSTEM_EXECUTOR
                and capabilities - _READ_ONLY_SYSTEM_CAPABILITIES
            ):
                matched_rules.append("system_executor_non_read_only")
            if (
                agent_descriptor.execution_kind == AgentExecutionKind.WORKFLOW_ENGINE
                and (bool(metadata.get("external_side_effect")) or "workflow.execute" in capabilities or "workflow.automation" in capabilities)
            ):
                matched_rules.append("workflow_engine_external_side_effect")
            if (
                agent_descriptor.execution_kind == AgentExecutionKind.CLOUD_AGENT
                and capabilities & _MUTATING_CAPABILITIES
            ):
                matched_rules.append("cloud_agent_mutating_action")
            if (
                agent_descriptor.source_type in {AgentSourceType.CODEX, AgentSourceType.CLAUDE_CODE}
                and agent_descriptor.execution_kind == AgentExecutionKind.CLOUD_AGENT
                and capabilities & _MUTATING_CAPABILITIES
            ):
                matched_rules.append("cloud_dev_agent_repo_mutation")

        summary_target = agent_descriptor.display_name if agent_descriptor is not None else "unselected-agent"
        return ApprovalCheck(
            required=bool(matched_rules),
            reason=", ".join(matched_rules) if matched_rules else None,
            matched_rules=matched_rules,
            proposed_action_summary=(
                f"Step {step.step_id} ({step.title}) via {summary_target} with capabilities: "
                f"{', '.join(step.required_capabilities) or 'none'}"
            ),
        )
