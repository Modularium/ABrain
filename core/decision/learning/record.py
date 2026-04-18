"""Canonical LearningRecord schema for Phase 5 – LearningOps.

A LearningRecord is a denormalised, flat snapshot of one routing decision
and its downstream outcomes (approval + execution).  It is the canonical
data unit for offline training dataset construction.

It is intentionally separate from TrainingSample (online neural-policy) to
keep concerns clean: LearningRecord captures *what happened and why*;
TrainingSample captures *what features were used and what reward resulted*.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LearningRecord(BaseModel):
    """One training example derived from a completed trace + approval + outcome.

    All fields are optional where the source data may be absent (e.g. a trace
    without a routing decision, or a routing decision without an approval).
    Data-quality flags make the availability of each signal explicit so that
    downstream training jobs can filter precisely.
    """

    model_config = ConfigDict(extra="forbid")

    # --- Trace provenance ---
    trace_id: str
    workflow_name: str
    task_type: str | None = None
    task_id: str | None = None
    started_at: str | None = None   # ISO 8601
    ended_at: str | None = None     # ISO 8601
    trace_status: str = "unknown"   # e.g. "ok", "error"

    # --- Routing decision ---
    selected_agent_id: str | None = None
    candidate_agent_ids: list[str] = Field(default_factory=list)
    selected_score: float | None = None
    routing_confidence: float | None = None
    score_gap: float | None = None
    confidence_band: str | None = None    # "high" | "medium" | "low"
    policy_effect: str | None = None      # "allow" | "deny" | "approval_required"
    matched_policy_ids: list[str] = Field(default_factory=list)
    approval_required: bool = False

    # --- Approval outcome ---
    approval_id: str | None = None
    approval_decision: str | None = None  # "approved" | "rejected" | "pending"

    # --- Execution outcome ---
    success: bool | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None

    # --- Arbitrary metadata preserved from the trace ---
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- Data-quality flags (set by DatasetBuilder, not by callers) ---
    has_routing_decision: bool = False   # at least one explainability record exists
    has_outcome: bool = False            # success field is set
    has_approval_outcome: bool = False   # approval_decision is resolved (not pending/missing)

    def quality_score(self) -> float:
        """Rough quality score in [0, 1] — higher means more signals available."""
        flags = [self.has_routing_decision, self.has_outcome, self.has_approval_outcome]
        return sum(1 for f in flags if f) / len(flags)
