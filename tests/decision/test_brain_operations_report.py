"""Phase 6 – §6.3 Observability: BrainOperationsReporter tests."""

from __future__ import annotations

import pytest

from core.audit.trace_store import TraceStore
from core.decision.brain.baseline_aggregator import (
    BRAIN_SHADOW_SPAN_TYPE,
    RECOMMENDATION_OBSERVE,
    RECOMMENDATION_PROMOTE,
    BrainBaselineAggregator,
    BrainBaselineReport,
)
from core.decision.brain.operations_report import (
    BrainOperationsReport,
    BrainOperationsReporter,
)
from core.decision.brain.suggestion_feed import (
    BrainSuggestionFeed,
    BrainSuggestionFeedBuilder,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_shadow_span(
    ts: TraceStore,
    *,
    workflow: str = "wf",
    version_id: str = "v1",
    production_agent: str | None = "A",
    brain_agent: str | None = "B",
    agreement: bool | None = None,
    score_divergence: float = 0.4,
    top_k_overlap: float = 0.5,
    k: int = 3,
    num_candidates: int = 2,
) -> str:
    if agreement is None:
        agreement = production_agent == brain_agent and production_agent is not None
    trace = ts.create_trace(workflow)
    span = ts.start_span(
        trace.trace_id,
        span_type=BRAIN_SHADOW_SPAN_TYPE,
        name="brain.shadow_evaluation",
        attributes={
            "brain_shadow.version_id": version_id,
            "brain_shadow.production_agent": production_agent,
            "brain_shadow.brain_agent": brain_agent,
            "brain_shadow.agreement": agreement,
            "brain_shadow.score_divergence": score_divergence,
            "brain_shadow.top_k_overlap": top_k_overlap,
            "brain_shadow.k": k,
            "brain_shadow.num_candidates": num_candidates,
        },
    )
    ts.finish_span(span.span_id, status="ok")
    return trace.trace_id


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestReporterConstruction:
    def test_defaults_wire_aggregator_and_feed_builder(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        reporter = BrainOperationsReporter(trace_store=ts)
        assert reporter.trace_store is ts
        assert isinstance(reporter.aggregator, BrainBaselineAggregator)
        assert isinstance(reporter.feed_builder, BrainSuggestionFeedBuilder)

    def test_accepts_injected_components(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        agg = BrainBaselineAggregator(trace_store=ts, min_samples_for_promote=1)
        feed = BrainSuggestionFeedBuilder(trace_store=ts, min_score_divergence=0.25)
        reporter = BrainOperationsReporter(
            trace_store=ts, aggregator=agg, feed_builder=feed
        )
        assert reporter.aggregator is agg
        assert reporter.feed_builder is feed


# ---------------------------------------------------------------------------
# generate() — empty / composed behaviour
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_empty_store_returns_observe_verdict_and_empty_feed(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        reporter = BrainOperationsReporter(trace_store=ts)
        report = reporter.generate()

        assert isinstance(report, BrainOperationsReport)
        assert isinstance(report.baseline, BrainBaselineReport)
        assert isinstance(report.suggestion_feed, BrainSuggestionFeed)
        assert report.baseline.samples == 0
        assert report.baseline.recommendation == RECOMMENDATION_OBSERVE
        assert report.suggestion_feed.entries == []
        # Feed is gated by baseline report — even if not promote.
        assert report.suggestion_feed.gated is True
        assert report.suggestion_feed.gate_passed is False

    def test_promote_verdict_surfaces_disagreement_entries(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        # 10 high-agreement samples with 3 actionable disagreements.
        for _ in range(7):
            _write_shadow_span(ts, production_agent="A", brain_agent="A",
                               score_divergence=0.05, top_k_overlap=0.95)
        for brain in ("B", "C", "D"):
            _write_shadow_span(ts, production_agent="A", brain_agent=brain,
                               score_divergence=0.15, top_k_overlap=0.5)

        agg = BrainBaselineAggregator(
            trace_store=ts,
            min_samples_for_promote=5,
            min_agreement_for_promote=0.5,
            max_divergence_for_promote=0.5,
        )
        reporter = BrainOperationsReporter(trace_store=ts, aggregator=agg)
        report = reporter.generate()

        assert report.baseline.recommendation == RECOMMENDATION_PROMOTE
        assert report.suggestion_feed.gated is True
        assert report.suggestion_feed.gate_passed is True
        assert len(report.suggestion_feed.entries) == 3
        agents = {e.brain_suggested_agent for e in report.suggestion_feed.entries}
        assert agents == {"B", "C", "D"}

    def test_observe_verdict_suppresses_entries_but_preserves_counts(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        # Only 2 disagreement samples — below default min_samples_for_promote=30.
        _write_shadow_span(ts, production_agent="A", brain_agent="B",
                           score_divergence=0.4)
        _write_shadow_span(ts, production_agent="A", brain_agent="C",
                           score_divergence=0.5)

        reporter = BrainOperationsReporter(trace_store=ts)
        report = reporter.generate()

        assert report.baseline.recommendation == RECOMMENDATION_OBSERVE
        assert report.suggestion_feed.gate_passed is False
        assert report.suggestion_feed.entries == []
        # Disagreement counts are still populated so operators can see what
        # would have surfaced.
        assert report.suggestion_feed.shadow_samples == 2
        assert report.suggestion_feed.disagreement_samples == 2

    def test_shared_filters_applied_to_both_primitives(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, workflow="wf-a", version_id="v1",
                           production_agent="A", brain_agent="B")
        _write_shadow_span(ts, workflow="wf-b", version_id="v1",
                           production_agent="A", brain_agent="C")
        _write_shadow_span(ts, workflow="wf-a", version_id="v2",
                           production_agent="A", brain_agent="D")

        reporter = BrainOperationsReporter(trace_store=ts)
        report = reporter.generate(workflow_filter="wf-a", version_filter="v1")

        assert report.workflow_filter == "wf-a"
        assert report.version_filter == "v1"
        assert report.baseline.samples == 1
        assert report.suggestion_feed.shadow_samples == 1
        assert report.suggestion_feed.disagreement_samples == 1

    def test_trace_limit_propagates_to_scan(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        for _ in range(5):
            _write_shadow_span(ts, production_agent="A", brain_agent="B")

        reporter = BrainOperationsReporter(trace_store=ts)
        report = reporter.generate(trace_limit=2)

        assert report.trace_limit == 2
        assert report.baseline.traces_scanned <= 2
        assert report.suggestion_feed.traces_scanned <= 2

    def test_max_feed_entries_caps_feed_only(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        for _ in range(7):
            _write_shadow_span(ts, production_agent="A", brain_agent="A",
                               score_divergence=0.05, top_k_overlap=0.95)
        for brain in ("B", "C", "D"):
            _write_shadow_span(ts, production_agent="A", brain_agent=brain,
                               score_divergence=0.2)

        agg = BrainBaselineAggregator(
            trace_store=ts,
            min_samples_for_promote=5,
            min_agreement_for_promote=0.5,
            max_divergence_for_promote=0.5,
        )
        reporter = BrainOperationsReporter(trace_store=ts, aggregator=agg)
        report = reporter.generate(max_feed_entries=2)

        assert report.baseline.recommendation == RECOMMENDATION_PROMOTE
        assert len(report.suggestion_feed.entries) == 2
        # Baseline counts are unaffected by the feed cap.
        assert report.baseline.samples == 10
        assert report.suggestion_feed.disagreement_samples == 3


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_extra_fields_forbidden(self):
        from datetime import UTC, datetime

        from core.decision.brain.baseline_aggregator import BrainBaselineMetrics

        zero = BrainBaselineMetrics(
            sample_count=0, agreement_rate=0.0, mean_score_divergence=0.0,
            median_score_divergence=0.0, mean_top_k_overlap=0.0,
            coverage_workflows=0, coverage_versions=0,
        )
        baseline = BrainBaselineReport(
            traces_scanned=0, samples=0, overall=zero,
            recommendation=RECOMMENDATION_OBSERVE, recommendation_reason="x",
        )
        feed = BrainSuggestionFeed(
            traces_scanned=0, shadow_samples=0, disagreement_samples=0,
            entries=[], gated=True, gate_passed=False,
            gate_reason="x", min_score_divergence=0.0,
        )
        with pytest.raises(ValueError):
            BrainOperationsReport(
                generated_at=datetime.now(UTC),
                trace_limit=100,
                baseline=baseline,
                suggestion_feed=feed,
                extra_field="nope",  # type: ignore[call-arg]
            )

    def test_required_fields(self):
        from datetime import UTC, datetime

        with pytest.raises(ValueError):
            BrainOperationsReport(
                generated_at=datetime.now(UTC),
                trace_limit=100,
                # missing baseline + suggestion_feed
            )  # type: ignore[call-arg]
