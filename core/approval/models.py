"""Structured approval models for human-in-the-loop execution control."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.decision.agent_descriptor import AgentExecutionKind, AgentSourceType
from core.decision.capabilities import CapabilityRisk


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class ApprovalStatus(StrEnum):
    """Lifecycle state of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalDecision(BaseModel):
    """Structured human decision for a pending approval request."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1, max_length=128)
    decision: ApprovalStatus
    decided_by: str = Field(min_length=1, max_length=128)
    decided_at: datetime = Field(default_factory=utcnow)
    comment: str | None = Field(default=None, max_length=2048)
    rating: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: ApprovalStatus) -> ApprovalStatus:
        if value not in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        }:
            raise ValueError("approval decisions must be terminal states")
        return value

    @field_validator("approval_id", "decided_by")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class ApprovalRequest(BaseModel):
    """Serializable request emitted when a plan step requires human approval."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(default_factory=lambda: f"approval-{uuid4().hex}", min_length=1, max_length=128)
    plan_id: str = Field(min_length=1, max_length=128)
    step_id: str = Field(min_length=1, max_length=128)
    task_summary: str = Field(min_length=1, max_length=2048)
    agent_id: str | None = Field(default=None, max_length=128)
    source_type: AgentSourceType | None = None
    execution_kind: AgentExecutionKind | None = None
    reason: str = Field(min_length=1, max_length=1024)
    risk: CapabilityRisk
    requested_at: datetime = Field(default_factory=utcnow)
    status: ApprovalStatus = ApprovalStatus.PENDING
    preview: dict[str, Any] = Field(default_factory=dict)
    proposed_action_summary: str = Field(min_length=1, max_length=2048)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("approval_id", "plan_id", "step_id", "task_summary", "reason", "proposed_action_summary")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized
