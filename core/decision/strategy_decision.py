"""Top-level strategy decision model for the ABrain decision layer.

Represents the fused verdict produced by ``StrategyEngine`` before any
execution is attempted: whether the task is allowed, whether it requires a
human approval gate, and which orchestration path should be taken.

This model does **not** replace :class:`RoutingDecision` (agent selection) or
:class:`PolicyDecision` (governance effect).  It composes their inputs into
one auditable verdict.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .capabilities import CapabilityRisk


PolicyEffect = Literal["allow", "deny", "require_approval"]


class StrategyChoice(StrEnum):
    """Orchestration path selected by the strategy engine."""

    DIRECT_EXECUTION = "direct_execution"
    PLAN_AND_EXECUTE = "plan_and_execute"
    REQUEST_APPROVAL = "request_approval"
    REJECT = "reject"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StrategyDecision(BaseModel):
    """Deterministic pre-execution strategy verdict."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(
        default_factory=lambda: f"decision-{uuid4().hex}",
        min_length=1,
        max_length=128,
    )
    trace_id: str | None = Field(default=None, max_length=128)

    task_type: str = Field(min_length=1, max_length=128)
    risk: CapabilityRisk = CapabilityRisk.MEDIUM
    policy_effect: PolicyEffect
    matched_policy_rules: list[str] = Field(default_factory=list)

    requires_approval: bool
    allowed: bool
    selected_strategy: StrategyChoice

    reasoning: str = Field(min_length=1, max_length=2048)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utcnow)

    @field_validator("decision_id", "task_type", "reasoning")
    @classmethod
    def _normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("trace_id")
    @classmethod
    def _normalize_trace_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("matched_policy_rules")
    @classmethod
    def _normalize_rules(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            stripped = value.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                normalized.append(stripped)
        return normalized
