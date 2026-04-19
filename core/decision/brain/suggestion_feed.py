"""Phase 6 – Brain v1 B6-S6: Brain suggestion feed.

Surfaces actionable Brain top-1 suggestions to operators — strictly
suggestion-only, never a decision replacement.  The feed is a read-only
consumer of ``brain_shadow_eval`` spans (written by ``BrainShadowRunner``)
from the canonical ``TraceStore``.

The roadmap exit task for Phase 6 is
*"Brain-v1 nur als Vorschlagsmodell ausrollen, nicht als Policy-Ersatz"*.
This module is that surface:

- no ownership of the production ``RoutingDecision`` (no writes to routing,
  policy, approval, or execution paths);
- no second TraceStore, no model loading (feed is purely observational);
- gated: when a ``BrainBaselineReport`` is supplied, entries are only
  surfaced if its ``recommendation == "promote"`` — suggestions stay
  hidden until the Brain version has been validated against the heuristic
  baseline.  Without a report, the feed surfaces unconditionally (opt-in
  ungated mode for local inspection).

An "actionable suggestion" is defined as a Brain shadow evaluation that
disagrees with production (``brain_agent != production_agent``, both
non-null) with ``score_divergence >= min_score_divergence``.  Agreement
rows are not suggestions — they are covered by the aggregator.

Stdlib only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from core.audit.trace_store import TraceStore

from .baseline_aggregator import (
    BRAIN_SHADOW_SPAN_TYPE,
    RECOMMENDATION_PROMOTE,
    BrainBaselineReport,
    BrainShadowEvalSummary,
    _summary_from_span,
)


class BrainSuggestionEntry(BaseModel):
    """One actionable Brain suggestion derived from a shadow eval span."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str
    workflow_name: str
    version_id: str
    production_agent: str
    brain_suggested_agent: str
    score_divergence: float = Field(ge=0.0, le=1.0)
    top_k_overlap: float = Field(ge=0.0, le=1.0)
    k: int = Field(ge=1)
    num_candidates: int = Field(ge=0)


class BrainSuggestionFeed(BaseModel):
    """Feed of Brain suggestions with gate + filter context."""

    model_config = ConfigDict(extra="forbid")

    traces_scanned: int = Field(ge=0)
    shadow_samples: int = Field(ge=0, description="Total brain_shadow_eval spans read")
    disagreement_samples: int = Field(ge=0, description="Shadow samples with prod != brain agent")
    entries: list[BrainSuggestionEntry] = Field(default_factory=list)
    gated: bool = Field(description="True when a baseline report was supplied as a gate")
    gate_passed: bool = Field(description="True when ungated or baseline report recommends promote")
    gate_reason: str = Field(description="Human-readable explanation of gate state")
    min_score_divergence: float = Field(ge=0.0, le=1.0)


class BrainSuggestionFeedBuilder:
    """Build a suggestion feed from ``brain_shadow_eval`` spans.

    Parameters
    ----------
    trace_store:
        Canonical ``TraceStore``.  Only ``list_recent_traces`` and
        ``get_trace`` are used — strictly read-only.
    min_score_divergence:
        Minimum ``score_divergence`` for a disagreement to be treated as
        actionable.  Disagreements below this are counted in
        ``disagreement_samples`` but do not appear in ``entries``.  Default
        ``0.0`` (all disagreements surfaced).
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        min_score_divergence: float = 0.0,
    ) -> None:
        if not 0.0 <= min_score_divergence <= 1.0:
            raise ValueError("min_score_divergence must be in [0, 1]")
        self.trace_store = trace_store
        self.min_score_divergence = min_score_divergence

    def build(
        self,
        *,
        trace_limit: int = 1000,
        workflow_filter: str | None = None,
        version_filter: str | None = None,
        baseline_report: BrainBaselineReport | None = None,
        max_entries: int | None = None,
    ) -> BrainSuggestionFeed:
        """Scan recent traces and assemble a suggestion feed.

        Parameters
        ----------
        trace_limit:
            Number of most-recent traces to scan.
        workflow_filter / version_filter:
            Optional slice filters applied before gating.
        baseline_report:
            When provided, its ``recommendation`` is the gate — only a
            ``promote`` verdict surfaces entries.  Any other verdict (or no
            report) is described in ``gate_reason``.
        max_entries:
            Optional cap on ``entries`` length after the gate.  Does not
            affect ``shadow_samples`` or ``disagreement_samples`` counts.
        """
        gated = baseline_report is not None
        if gated:
            assert baseline_report is not None
            gate_passed = baseline_report.recommendation == RECOMMENDATION_PROMOTE
            gate_reason = (
                f"baseline verdict '{baseline_report.recommendation}': "
                f"{baseline_report.recommendation_reason}"
            )
        else:
            gate_passed = True
            gate_reason = "ungated — no baseline report supplied"

        traces = self.trace_store.list_recent_traces(limit=trace_limit)
        traces_scanned = len(traces)

        shadow_samples = 0
        disagreement_samples = 0
        candidates: list[BrainSuggestionEntry] = []

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
                shadow_samples += 1
                entry = _entry_from_summary(summary)
                if entry is None:
                    continue
                disagreement_samples += 1
                if entry.score_divergence < self.min_score_divergence:
                    continue
                candidates.append(entry)

        if gate_passed:
            entries = candidates
            if max_entries is not None and max_entries >= 0:
                entries = entries[:max_entries]
        else:
            entries = []

        return BrainSuggestionFeed(
            traces_scanned=traces_scanned,
            shadow_samples=shadow_samples,
            disagreement_samples=disagreement_samples,
            entries=entries,
            gated=gated,
            gate_passed=gate_passed,
            gate_reason=gate_reason,
            min_score_divergence=self.min_score_divergence,
        )


def _entry_from_summary(summary: BrainShadowEvalSummary) -> BrainSuggestionEntry | None:
    """Return an actionable suggestion entry or ``None`` for non-actionable rows.

    A row is actionable iff both agents are known and they disagree.  Agreement
    rows and rows with a missing agent on either side are not suggestions.
    """
    if summary.agreement:
        return None
    if summary.production_agent is None or summary.brain_agent is None:
        return None
    if summary.production_agent == summary.brain_agent:
        return None
    return BrainSuggestionEntry(
        trace_id=summary.trace_id,
        span_id=summary.span_id,
        workflow_name=summary.workflow_name,
        version_id=summary.version_id,
        production_agent=summary.production_agent,
        brain_suggested_agent=summary.brain_agent,
        score_divergence=summary.score_divergence,
        top_k_overlap=summary.top_k_overlap,
        k=summary.k,
        num_candidates=summary.num_candidates,
    )


__all__ = [
    "BrainSuggestionEntry",
    "BrainSuggestionFeed",
    "BrainSuggestionFeedBuilder",
]
