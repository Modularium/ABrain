"""Phase 6 – Brain v1 B6-S5: Brain-vs-heuristic baseline aggregator.

Reads ``brain_shadow_eval`` spans (written by ``BrainShadowRunner``) from the
canonical ``TraceStore`` and aggregates them into a structured comparison
report with overall, per-version, and per-workflow metrics, plus a
threshold-based promotion recommendation.

Read-only: no writes to ``TraceStore``, no second store, no model loading.
The aggregator is the canonical answer to the roadmap task
*"Brain-v1 gegen heuristische Baseline evaluieren"* — operators run it
against a representative trace window to decide go/no-go on Brain v1
promotion.

Pipeline::

    list_recent_traces(trace_limit)
      → for each trace: get_trace(trace_id)
      → filter spans by span_type == "brain_shadow_eval"
      → flatten into BrainShadowEvalSummary
      → apply optional workflow / version filters
      → compute BrainBaselineMetrics overall + per-axis
      → apply promotion thresholds
      → BrainBaselineReport

Stdlib only.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from statistics import mean, median
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.audit.trace_store import TraceStore

# Span type written by BrainShadowRunner — single source of truth.
BRAIN_SHADOW_SPAN_TYPE = "brain_shadow_eval"

# Recommendation labels.
RECOMMENDATION_PROMOTE = "promote"
RECOMMENDATION_OBSERVE = "observe"
RECOMMENDATION_REJECT = "reject"


class BrainShadowEvalSummary(BaseModel):
    """Flattened view of one ``brain_shadow_eval`` span for aggregation."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str
    workflow_name: str
    started_at: datetime
    version_id: str
    production_agent: str | None
    brain_agent: str | None
    agreement: bool
    score_divergence: float = Field(ge=0.0, le=1.0)
    top_k_overlap: float = Field(ge=0.0, le=1.0)
    k: int = Field(ge=1)
    num_candidates: int = Field(ge=0)


class BrainBaselineMetrics(BaseModel):
    """Aggregated metrics across one slice of shadow evaluations."""

    model_config = ConfigDict(extra="forbid")

    sample_count: int = Field(ge=0)
    agreement_rate: float = Field(ge=0.0, le=1.0)
    mean_score_divergence: float = Field(ge=0.0, le=1.0)
    median_score_divergence: float = Field(ge=0.0, le=1.0)
    mean_top_k_overlap: float = Field(ge=0.0, le=1.0)
    coverage_workflows: int = Field(ge=0)
    coverage_versions: int = Field(ge=0)


class BrainBaselineReport(BaseModel):
    """Structured Brain-vs-heuristic baseline report."""

    model_config = ConfigDict(extra="forbid")

    traces_scanned: int = Field(ge=0)
    samples: int = Field(ge=0)
    overall: BrainBaselineMetrics
    per_version: dict[str, BrainBaselineMetrics] = Field(default_factory=dict)
    per_workflow: dict[str, BrainBaselineMetrics] = Field(default_factory=dict)
    recommendation: str = Field(
        description="'promote' | 'observe' | 'reject' — see promotion_thresholds for criteria"
    )
    recommendation_reason: str
    promotion_thresholds: dict[str, float] = Field(default_factory=dict)


class BrainBaselineAggregator:
    """Aggregate ``brain_shadow_eval`` spans into a baseline comparison report.

    Parameters
    ----------
    trace_store:
        Canonical ``TraceStore``.  Only ``list_recent_traces`` and
        ``get_trace`` are used — strictly read-only.
    min_agreement_for_promote:
        Minimum overall agreement_rate (Brain top-1 == production top-1) for
        the report to recommend promotion.  Default 0.7.
    max_divergence_for_promote:
        Maximum mean score_divergence permitted for promotion.  Default 0.2.
    min_samples_for_promote:
        Minimum sample_count required before any promotion can be recommended.
        Below this the report falls back to ``observe``.  Default 30.
    reject_agreement_below:
        Hard reject threshold — agreement_rate strictly below this triggers
        ``reject`` regardless of sample count (assuming the count is at least
        ``min_samples_for_reject``).  Default 0.3.
    min_samples_for_reject:
        Minimum samples required to issue a ``reject`` recommendation.  Below
        this the verdict stays ``observe``.  Default 10.
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        min_agreement_for_promote: float = 0.7,
        max_divergence_for_promote: float = 0.2,
        min_samples_for_promote: int = 30,
        reject_agreement_below: float = 0.3,
        min_samples_for_reject: int = 10,
    ) -> None:
        self.trace_store = trace_store
        self.min_agreement_for_promote = min_agreement_for_promote
        self.max_divergence_for_promote = max_divergence_for_promote
        self.min_samples_for_promote = min_samples_for_promote
        self.reject_agreement_below = reject_agreement_below
        self.min_samples_for_reject = min_samples_for_reject

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate(
        self,
        *,
        trace_limit: int = 1000,
        workflow_filter: str | None = None,
        version_filter: str | None = None,
    ) -> BrainBaselineReport:
        """Scan recent traces and produce a baseline comparison report.

        Parameters
        ----------
        trace_limit:
            Number of most-recent traces to scan.  Each trace is fetched once.
        workflow_filter:
            When set, only spans whose trace's ``workflow_name`` matches are
            included.
        version_filter:
            When set, only spans whose ``brain_shadow.version_id`` matches are
            included.
        """
        traces = self.trace_store.list_recent_traces(limit=trace_limit)
        traces_scanned = len(traces)

        summaries: list[BrainShadowEvalSummary] = []
        for trace in traces:
            if workflow_filter is not None and trace.workflow_name != workflow_filter:
                continue
            snapshot = self.trace_store.get_trace(trace.trace_id)
            if snapshot is None:
                continue
            for span in snapshot.spans:
                if span.span_type != BRAIN_SHADOW_SPAN_TYPE:
                    continue
                summary = _summary_from_span(
                    trace_id=trace.trace_id,
                    workflow_name=trace.workflow_name,
                    span_attributes=span.attributes,
                    span_id=span.span_id,
                    started_at=span.started_at,
                )
                if summary is None:
                    continue
                if version_filter is not None and summary.version_id != version_filter:
                    continue
                summaries.append(summary)

        overall = _compute_metrics(summaries)
        per_version = _group_metrics(summaries, key=lambda s: s.version_id)
        per_workflow = _group_metrics(summaries, key=lambda s: s.workflow_name)

        recommendation, reason = self._recommend(overall)

        return BrainBaselineReport(
            traces_scanned=traces_scanned,
            samples=overall.sample_count,
            overall=overall,
            per_version=per_version,
            per_workflow=per_workflow,
            recommendation=recommendation,
            recommendation_reason=reason,
            promotion_thresholds={
                "min_agreement_for_promote": self.min_agreement_for_promote,
                "max_divergence_for_promote": self.max_divergence_for_promote,
                "min_samples_for_promote": float(self.min_samples_for_promote),
                "reject_agreement_below": self.reject_agreement_below,
                "min_samples_for_reject": float(self.min_samples_for_reject),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recommend(self, metrics: BrainBaselineMetrics) -> tuple[str, str]:
        if metrics.sample_count == 0:
            return (
                RECOMMENDATION_OBSERVE,
                "no brain_shadow_eval spans found in the scanned trace window",
            )
        if (
            metrics.sample_count >= self.min_samples_for_reject
            and metrics.agreement_rate < self.reject_agreement_below
        ):
            return (
                RECOMMENDATION_REJECT,
                (
                    f"agreement_rate {metrics.agreement_rate:.3f} < "
                    f"reject threshold {self.reject_agreement_below:.3f}"
                ),
            )
        if metrics.sample_count < self.min_samples_for_promote:
            return (
                RECOMMENDATION_OBSERVE,
                (
                    f"sample_count {metrics.sample_count} < "
                    f"min_samples_for_promote {self.min_samples_for_promote}"
                ),
            )
        if metrics.agreement_rate < self.min_agreement_for_promote:
            return (
                RECOMMENDATION_OBSERVE,
                (
                    f"agreement_rate {metrics.agreement_rate:.3f} < "
                    f"min_agreement_for_promote {self.min_agreement_for_promote:.3f}"
                ),
            )
        if metrics.mean_score_divergence > self.max_divergence_for_promote:
            return (
                RECOMMENDATION_OBSERVE,
                (
                    f"mean_score_divergence {metrics.mean_score_divergence:.3f} > "
                    f"max_divergence_for_promote {self.max_divergence_for_promote:.3f}"
                ),
            )
        return (
            RECOMMENDATION_PROMOTE,
            (
                f"agreement_rate {metrics.agreement_rate:.3f} ≥ "
                f"{self.min_agreement_for_promote:.3f} and divergence "
                f"{metrics.mean_score_divergence:.3f} ≤ "
                f"{self.max_divergence_for_promote:.3f} "
                f"on {metrics.sample_count} samples"
            ),
        )


# ---------------------------------------------------------------------------
# Internal helpers (module-level — easy to unit-test)
# ---------------------------------------------------------------------------


def _summary_from_span(
    *,
    trace_id: str,
    workflow_name: str,
    span_attributes: dict[str, Any],
    span_id: str,
    started_at: datetime,
) -> BrainShadowEvalSummary | None:
    """Flatten one ``brain_shadow_eval`` span into a summary.

    Returns ``None`` when required attributes are missing (defensive against
    span schema drift — the aggregator should never raise on a malformed
    span, just skip it).
    """
    try:
        return BrainShadowEvalSummary(
            trace_id=trace_id,
            span_id=span_id,
            workflow_name=workflow_name,
            started_at=started_at,
            version_id=str(span_attributes["brain_shadow.version_id"]),
            production_agent=_optional_str(span_attributes.get("brain_shadow.production_agent")),
            brain_agent=_optional_str(span_attributes.get("brain_shadow.brain_agent")),
            agreement=bool(span_attributes["brain_shadow.agreement"]),
            score_divergence=float(span_attributes["brain_shadow.score_divergence"]),
            top_k_overlap=float(span_attributes["brain_shadow.top_k_overlap"]),
            k=int(span_attributes["brain_shadow.k"]),
            num_candidates=int(span_attributes["brain_shadow.num_candidates"]),
        )
    except (KeyError, ValueError, TypeError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _compute_metrics(summaries: list[BrainShadowEvalSummary]) -> BrainBaselineMetrics:
    if not summaries:
        return BrainBaselineMetrics(
            sample_count=0,
            agreement_rate=0.0,
            mean_score_divergence=0.0,
            median_score_divergence=0.0,
            mean_top_k_overlap=0.0,
            coverage_workflows=0,
            coverage_versions=0,
        )
    agreements = [1.0 if s.agreement else 0.0 for s in summaries]
    divergences = [s.score_divergence for s in summaries]
    overlaps = [s.top_k_overlap for s in summaries]
    workflows = {s.workflow_name for s in summaries}
    versions = {s.version_id for s in summaries}
    return BrainBaselineMetrics(
        sample_count=len(summaries),
        agreement_rate=mean(agreements),
        mean_score_divergence=mean(divergences),
        median_score_divergence=median(divergences),
        mean_top_k_overlap=mean(overlaps),
        coverage_workflows=len(workflows),
        coverage_versions=len(versions),
    )


def _group_metrics(
    summaries: Iterable[BrainShadowEvalSummary],
    *,
    key,
) -> dict[str, BrainBaselineMetrics]:
    grouped: dict[str, list[BrainShadowEvalSummary]] = defaultdict(list)
    for summary in summaries:
        grouped[key(summary)].append(summary)
    return {group: _compute_metrics(items) for group, items in grouped.items()}


__all__ = [
    "BRAIN_SHADOW_SPAN_TYPE",
    "RECOMMENDATION_OBSERVE",
    "RECOMMENDATION_PROMOTE",
    "RECOMMENDATION_REJECT",
    "BrainBaselineAggregator",
    "BrainBaselineMetrics",
    "BrainBaselineReport",
    "BrainShadowEvalSummary",
]
