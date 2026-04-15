"""Pydantic result models for the ABrain evaluation layer.

All models are read-only value objects produced by :class:`TraceEvaluator`.
None of them trigger execution, create approvals, or write to any store.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Routing replay
# ---------------------------------------------------------------------------


class RoutingReplayVerdict(StrEnum):
    """Classification of a per-step routing dry-run result."""

    EXACT_MATCH = "exact_match"
    """Same agent selected today as historically."""

    ACCEPTABLE_VARIATION = "acceptable_variation"
    """Different agent selected, but same confidence band — not a regression."""

    REGRESSION = "regression"
    """Different agent selected with a meaningful confidence or band change."""

    NON_REPLAYABLE = "non_replayable"
    """Insufficient context in stored trace to run a meaningful comparison."""


class RoutingReplayResult(BaseModel):
    """Per-step comparison of stored routing decision vs current routing logic."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    verdict: RoutingReplayVerdict

    stored_agent_id: str | None = None
    """Agent selected at original execution time."""

    current_agent_id: str | None = None
    """Agent that would be selected by the current routing engine."""

    stored_confidence: float | None = None
    stored_confidence_band: str | None = None
    stored_score_gap: float | None = None

    current_confidence: float | None = None
    current_confidence_band: str | None = None
    current_score_gap: float | None = None

    current_top_candidates: list[str] = Field(default_factory=list)
    """Agent IDs of the top-ranked candidates in the current run."""

    reason: str = ""
    """Human-readable explanation of the verdict."""

    non_replayable_reason: str | None = None
    """Why the step could not be replayed (only set when NON_REPLAYABLE)."""


# ---------------------------------------------------------------------------
# Policy compliance
# ---------------------------------------------------------------------------


class PolicyReplayVerdict(StrEnum):
    """Classification of a per-step policy compliance comparison."""

    COMPLIANT = "compliant"
    """Same policy effect today as historically."""

    TIGHTENED = "tightened"
    """Policy is stricter today (allow → require_approval, * → deny).  Safe."""

    REGRESSION = "regression"
    """Policy is more permissive today (deny/require_approval → allow).  Risky."""

    NON_EVALUABLE = "non_evaluable"
    """Insufficient context to run a meaningful comparison."""


# Effect ordering: higher = more restrictive.
_EFFECT_STRICTNESS: dict[str, int] = {
    "allow": 0,
    "require_approval": 1,
    "deny": 2,
}


def classify_policy_delta(stored: str | None, current: str | None) -> PolicyReplayVerdict:
    """Return the compliance verdict for a stored→current policy effect pair.

    Pure function — no side effects.
    """
    if stored is None or current is None:
        return PolicyReplayVerdict.NON_EVALUABLE
    stored_rank = _EFFECT_STRICTNESS.get(stored, -1)
    current_rank = _EFFECT_STRICTNESS.get(current, -1)
    if stored_rank == -1 or current_rank == -1:
        return PolicyReplayVerdict.NON_EVALUABLE
    if current_rank == stored_rank:
        return PolicyReplayVerdict.COMPLIANT
    if current_rank > stored_rank:
        return PolicyReplayVerdict.TIGHTENED
    return PolicyReplayVerdict.REGRESSION


class PolicyReplayResult(BaseModel):
    """Per-step comparison of stored policy decision vs current governance logic."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    verdict: PolicyReplayVerdict

    stored_effect: str | None = None
    """Policy effect recorded at original execution time."""

    current_effect: str | None = None
    """Policy effect returned by current PolicyEngine for reconstructed context."""

    stored_matched_policy_ids: list[str] = Field(default_factory=list)
    current_matched_policy_ids: list[str] = Field(default_factory=list)

    stored_approval_required: bool = False
    current_approval_required: bool = False

    approval_consistency: bool = True
    """True when approval_required matches between stored and current."""

    reason: str = ""
    """Human-readable explanation."""


# ---------------------------------------------------------------------------
# Per-step combined result
# ---------------------------------------------------------------------------


class StepEvaluationResult(BaseModel):
    """Combined routing + policy evaluation for one stored explainability step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    routing: RoutingReplayResult
    policy: PolicyReplayResult | None = None
    has_regression: bool = False
    """True when either routing or policy has a REGRESSION verdict."""


# ---------------------------------------------------------------------------
# Per-trace evaluation
# ---------------------------------------------------------------------------


class TraceEvaluationResult(BaseModel):
    """Full evaluation of one stored trace against current logic.

    Produced by :meth:`TraceEvaluator.evaluate_trace`.
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    workflow_name: str
    can_replay: bool
    """Mirrors ReplayDescriptor.can_replay — False means most steps are NON_REPLAYABLE."""

    step_results: list[StepEvaluationResult] = Field(default_factory=list)

    has_routing_regression: bool = False
    """True when any step has a routing REGRESSION verdict."""

    has_policy_regression: bool = False
    """True when any step has a policy REGRESSION verdict."""

    has_any_regression: bool = False
    """True when has_routing_regression OR has_policy_regression."""

    routing_match_count: int = 0
    routing_regression_count: int = 0
    policy_compliant_count: int = 0
    policy_regression_count: int = 0
    non_replayable_count: int = 0

    summary: dict[str, Any] = Field(default_factory=dict)
    """Free-form summary fields for CLI / API rendering."""


# ---------------------------------------------------------------------------
# Batch baseline report
# ---------------------------------------------------------------------------


class BatchEvaluationReport(BaseModel):
    """Baseline metrics computed across a batch of recently stored traces.

    Produced by :meth:`TraceEvaluator.compute_baselines`.
    """

    model_config = ConfigDict(extra="forbid")

    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_count: int = 0
    """Total traces examined."""

    replayable_count: int = 0
    """Traces with can_replay=True."""

    evaluated_step_count: int = 0
    """Total steps evaluated across all traces."""

    non_replayable_step_count: int = 0

    routing_exact_match_count: int = 0
    routing_acceptable_variation_count: int = 0
    routing_regression_count: int = 0

    routing_match_rate: float | None = None
    """exact_match / (exact_match + acceptable_variation + regression); None if 0 replayable steps."""

    policy_compliant_count: int = 0
    policy_tightened_count: int = 0
    policy_regression_count: int = 0

    policy_compliance_rate: float | None = None
    """compliant / (compliant + tightened + regression); None if no policy data."""

    approval_consistent_count: int = 0
    approval_inconsistent_count: int = 0
    approval_consistency_rate: float | None = None
    """consistent / total with approval data."""

    avg_routing_confidence: float | None = None
    """Mean routing_confidence across all steps with recorded confidence."""

    confidence_band_distribution: dict[str, int] = Field(default_factory=dict)
    """Counts per confidence_band ("high"/"medium"/"low")."""

    traces_with_regression: int = 0
    """Traces where has_any_regression=True."""

    # ── Routing KPIs ──────────────────────────────────────────────────────────

    trace_success_count: int = 0
    """Traces with status='completed'."""

    trace_failed_count: int = 0
    """Traces with status='failed'."""

    trace_success_rate: float | None = None
    """success_count / (success_count + failed_count); None if no terminal traces."""

    avg_duration_ms: float | None = None
    """Mean trace duration in milliseconds across completed traces."""

    p95_duration_ms: float | None = None
    """95th-percentile trace duration in milliseconds across completed traces."""

    # ── Safety metrics ────────────────────────────────────────────────────────

    approval_bypass_count: int = 0
    """Steps where approval_required=True but no approval_id was recorded.
    Indicates an approval gate that was not followed up — a safety signal."""

    baseline_metadata: dict[str, Any] = Field(default_factory=dict)
