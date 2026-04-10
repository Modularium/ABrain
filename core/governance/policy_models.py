"""Canonical runtime governance models for policy evaluation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PolicyEffect = Literal["allow", "deny", "require_approval"]


class PolicyRule(BaseModel):
    """Deterministic governance rule evaluated at runtime."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1024)
    capability: str | None = Field(default=None, max_length=128)
    agent_id: str | None = Field(default=None, max_length=128)
    source_type: str | None = Field(default=None, max_length=128)
    execution_kind: str | None = Field(default=None, max_length=128)
    max_cost: float | None = Field(default=None, ge=0.0)
    max_latency: int | None = Field(default=None, ge=0)
    requires_local: bool | None = None
    risk_level: str | None = Field(default=None, max_length=32)
    external_side_effect: bool | None = None
    effect: PolicyEffect
    priority: int = 0

    @field_validator(
        "id",
        "description",
        "capability",
        "agent_id",
        "source_type",
        "execution_kind",
        "risk_level",
    )
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("string values must not be blank")
        return normalized


class PolicyEvaluationContext(BaseModel):
    """Flattened context used for deterministic runtime policy matching."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1, max_length=128)
    task_summary: str | None = Field(default=None, max_length=2048)
    task_id: str | None = Field(default=None, max_length=128)
    plan_id: str | None = Field(default=None, max_length=128)
    step_id: str | None = Field(default=None, max_length=128)
    required_capabilities: list[str] = Field(default_factory=list)
    agent_id: str | None = Field(default=None, max_length=128)
    source_type: str | None = Field(default=None, max_length=128)
    execution_kind: str | None = Field(default=None, max_length=128)
    estimated_cost: float | None = Field(default=None, ge=0.0)
    estimated_latency: int | None = Field(default=None, ge=0)
    is_local: bool | None = None
    risk_level: str | None = Field(default=None, max_length=32)
    external_side_effect: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "task_type",
        "task_summary",
        "task_id",
        "plan_id",
        "step_id",
        "agent_id",
        "source_type",
        "execution_kind",
        "risk_level",
    )
    @classmethod
    def normalize_context_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("required_capabilities")
    @classmethod
    def normalize_capabilities(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized_values: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                normalized_values.append(normalized)
        return normalized_values


class PolicyDecision(BaseModel):
    """Outcome of deterministic policy evaluation."""

    model_config = ConfigDict(extra="forbid")

    effect: PolicyEffect
    matched_rules: list[str] = Field(default_factory=list)
    winning_rule_id: str | None = None
    winning_priority: int | None = None
    reason: str
