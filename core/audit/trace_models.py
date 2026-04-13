"""Structured trace and explainability models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class TraceEvent(BaseModel):
    """A timestamped event attached to a span."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=128)
    timestamp: datetime = Field(default_factory=utcnow)
    message: str = Field(min_length=1, max_length=2048)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type", "message")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class TraceRecord(BaseModel):
    """Top-level trace for a request or plan execution."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(default_factory=lambda: f"trace-{uuid4().hex}", min_length=1, max_length=128)
    workflow_name: str = Field(min_length=1, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    status: str = Field(default="running", min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("trace_id", "workflow_name", "task_id", "status")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class SpanRecord(BaseModel):
    """A nested timed operation within a trace."""

    model_config = ConfigDict(extra="forbid")

    span_id: str = Field(default_factory=lambda: f"span-{uuid4().hex}", min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=128)
    parent_span_id: str | None = Field(default=None, max_length=128)
    span_type: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    status: str = Field(default="running", min_length=1, max_length=64)
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[TraceEvent] = Field(default_factory=list)
    error: dict[str, Any] | None = None

    @field_validator("span_id", "trace_id", "parent_span_id", "span_type", "name", "status")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class ExplainabilityRecord(BaseModel):
    """Compact explainability snapshot for a routed step or task.

    S10 additions (backwards-compatible, all nullable/defaulted):
    - ``routing_confidence`` — top candidate score at decision time
    - ``score_gap`` — score difference between #1 and #2 candidate
    - ``confidence_band`` — "high"/"medium"/"low" routing certainty
    - ``policy_effect`` — governance outcome for this step
    - ``scored_candidates`` — ranked candidate list with per-agent scores
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    step_id: str | None = Field(default=None, max_length=128)
    selected_agent_id: str | None = Field(default=None, max_length=128)
    candidate_agent_ids: list[str] = Field(default_factory=list)
    selected_score: float | None = None
    routing_reason_summary: str = Field(min_length=1, max_length=2048)
    matched_policy_ids: list[str] = Field(default_factory=list)
    approval_required: bool = False
    approval_id: str | None = Field(default=None, max_length=128)
    # S10 — first-class forensics signals (all optional for backwards compat)
    routing_confidence: float | None = None
    score_gap: float | None = None
    confidence_band: str | None = Field(default=None, max_length=32)
    policy_effect: str | None = Field(default=None, max_length=64)
    scored_candidates: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "trace_id", "step_id", "selected_agent_id", "routing_reason_summary",
        "approval_id", "confidence_band", "policy_effect",
    )
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("candidate_agent_ids", "matched_policy_ids")
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        normalized_values: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                normalized_values.append(normalized)
        return normalized_values


class ReplayStepInput(BaseModel):
    """Per-step inputs captured for replay-readiness assessment.

    Describes the minimal context needed to reproduce one routing decision
    step.  Not an execution request — a descriptive summary only.
    """

    model_config = ConfigDict(extra="forbid")

    step_id: str
    task_type: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    selected_agent_id: str | None = None
    candidate_agent_ids: list[str] = Field(default_factory=list)
    routing_confidence: float | None = None
    confidence_band: str | None = None
    policy_effect: str | None = None


class ReplayDescriptor(BaseModel):
    """Canonical replay-readiness descriptor derived from a stored trace.

    Answers: "what would be needed to reproduce this trace's decisions?"
    Not an execution request — a structured forensics summary.

    ``can_replay`` is True when enough context was captured at record time to
    meaningfully reproduce the routing inputs (task_type + candidates present).
    ``missing_inputs`` lists what gaps prevent full reproducibility.
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    workflow_name: str
    task_type: str | None = None
    task_id: str | None = None
    started_at: str | None = None
    step_inputs: list[ReplayStepInput] = Field(default_factory=list)
    can_replay: bool = False
    missing_inputs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSnapshot(BaseModel):
    """Full trace payload returned for internal inspection.

    S10: includes ``replay_descriptor`` — derived from stored explainability
    records.  Always present when the trace has explainability data; None for
    traces with no routing decisions (e.g. bare system-status calls).
    """

    model_config = ConfigDict(extra="forbid")

    trace: TraceRecord
    spans: list[SpanRecord] = Field(default_factory=list)
    explainability: list[ExplainabilityRecord] = Field(default_factory=list)
    replay_descriptor: ReplayDescriptor | None = None
