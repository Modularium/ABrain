"""Phase 6 – Brain v1 B6-S6: BrainSuggestionFeedBuilder tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.audit.trace_store import TraceStore
from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
    RoutingEngine,
)
from core.decision.brain.baseline_aggregator import (
    BRAIN_SHADOW_SPAN_TYPE,
    RECOMMENDATION_OBSERVE,
    RECOMMENDATION_PROMOTE,
    RECOMMENDATION_REJECT,
    BrainBaselineMetrics,
    BrainBaselineReport,
    BrainShadowEvalSummary,
)
from core.decision.brain.shadow_runner import BrainShadowRunner
from core.decision.brain.state import (
    BrainAgentSignal,
    BrainPolicySignals,
    BrainRecord,
    BrainState,
    BrainTarget,
)
from core.decision.brain.suggestion_feed import (
    BrainSuggestionEntry,
    BrainSuggestionFeed,
    BrainSuggestionFeedBuilder,
    _entry_from_summary,
)
from core.decision.brain.trainer import (
    BrainOfflineTrainer,
    BrainTrainingJobConfig,
    save_brain_records,
)
from core.decision.learning.model_registry import ModelRegistry
from core.decision.task_intent import TaskIntent

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(
    *,
    trace_id: str = "t1",
    span_id: str = "s1",
    workflow_name: str = "wf",
    version_id: str = "v1",
    agreement: bool = False,
    production_agent: str | None = "A",
    brain_agent: str | None = "B",
    score_divergence: float = 0.4,
    top_k_overlap: float = 0.5,
    k: int = 3,
    num_candidates: int = 2,
) -> BrainShadowEvalSummary:
    from datetime import UTC, datetime

    return BrainShadowEvalSummary(
        trace_id=trace_id,
        span_id=span_id,
        workflow_name=workflow_name,
        started_at=datetime.now(UTC),
        version_id=version_id,
        production_agent=production_agent,
        brain_agent=brain_agent,
        agreement=agreement,
        score_divergence=score_divergence,
        top_k_overlap=top_k_overlap,
        k=k,
        num_candidates=num_candidates,
    )


def _make_report(
    *,
    recommendation: str = RECOMMENDATION_PROMOTE,
    reason: str = "looks good",
) -> BrainBaselineReport:
    zero = BrainBaselineMetrics(
        sample_count=0,
        agreement_rate=0.0,
        mean_score_divergence=0.0,
        median_score_divergence=0.0,
        mean_top_k_overlap=0.0,
        coverage_workflows=0,
        coverage_versions=0,
    )
    return BrainBaselineReport(
        traces_scanned=0,
        samples=0,
        overall=zero,
        recommendation=recommendation,
        recommendation_reason=reason,
    )


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
    """Create a trace with one brain_shadow_eval span and return its trace_id."""
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


def _make_descriptor(agent_id: str) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["analysis.code"],
        trust_level=AgentTrustLevel.TRUSTED,
        availability=AgentAvailability.ONLINE,
        metadata={"success_rate": 0.9, "estimated_cost_per_token": 0.001, "avg_response_time": 1.0},
    )


def _make_intent() -> TaskIntent:
    return TaskIntent(
        task_type="code_review",
        domain="engineering",
        required_capabilities=["analysis.code"],
        execution_hints={},
        description="Review module",
    )


def _make_brain_record(trace_id: str, success: bool = True) -> BrainRecord:
    return BrainRecord(
        trace_id=trace_id,
        workflow_name="wf",
        state=BrainState(
            task_type="code_review",
            domain="engineering",
            num_required_capabilities=1,
            num_candidates=1,
            routing_confidence=0.8,
            score_gap=0.1,
            confidence_band="high",
            policy=BrainPolicySignals(),
            candidates=[
                BrainAgentSignal(
                    agent_id="agent-0",
                    capability_match_score=1.0,
                    success_rate=0.9,
                    avg_latency_s=1.0,
                    avg_cost_usd=0.001,
                    recent_failures=0,
                    execution_count=10,
                    load_factor=0.1,
                    trust_level_ord=0.67,
                    availability_ord=1.0,
                )
            ],
        ),
        target=BrainTarget(
            selected_agent_id="agent-0",
            outcome_success=success,
            outcome_cost_usd=0.001,
            outcome_latency_ms=500.0,
        ),
    )


def _train_brain_and_register(tmp_path: Path, registry: ModelRegistry) -> str:
    records_path = tmp_path / "brain_records.jsonl"
    save_brain_records(
        [_make_brain_record(f"t{i}", success=(i % 2 == 0)) for i in range(4)],
        records_path,
    )
    config = BrainTrainingJobConfig(
        brain_records_path=records_path,
        output_artifact_path=tmp_path / "brain_models" / "brain.json",
        min_samples=1,
    )
    result = BrainOfflineTrainer(config).run()
    entry = registry.register_brain(result, config)
    return entry.version_id


# ---------------------------------------------------------------------------
# _entry_from_summary
# ---------------------------------------------------------------------------


class TestEntryFromSummary:
    def test_disagreement_yields_entry(self):
        summary = _make_summary(agreement=False, production_agent="A", brain_agent="B")
        entry = _entry_from_summary(summary)
        assert entry is not None
        assert entry.production_agent == "A"
        assert entry.brain_suggested_agent == "B"

    def test_agreement_yields_none(self):
        summary = _make_summary(
            agreement=True, production_agent="A", brain_agent="A", score_divergence=0.0
        )
        assert _entry_from_summary(summary) is None

    def test_none_production_agent_yields_none(self):
        summary = _make_summary(agreement=False, production_agent=None, brain_agent="B")
        assert _entry_from_summary(summary) is None

    def test_none_brain_agent_yields_none(self):
        summary = _make_summary(agreement=False, production_agent="A", brain_agent=None)
        assert _entry_from_summary(summary) is None

    def test_same_agent_but_flagged_disagree_yields_none(self):
        # Defensive: if flags drift, agent identity must still gate actionability.
        summary = _make_summary(agreement=False, production_agent="A", brain_agent="A")
        assert _entry_from_summary(summary) is None


# ---------------------------------------------------------------------------
# BrainSuggestionFeedBuilder.build — TraceStore integration (synthetic spans)
# ---------------------------------------------------------------------------


class TestBuildAgainstTraceStore:
    def test_empty_store_yields_empty_feed(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert isinstance(feed, BrainSuggestionFeed)
        assert feed.entries == []
        assert feed.shadow_samples == 0
        assert feed.disagreement_samples == 0
        assert feed.gated is False
        assert feed.gate_passed is True

    def test_non_shadow_spans_skipped(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        trace = ts.create_trace("noisy-wf")
        span = ts.start_span(
            trace.trace_id,
            span_type="routing_decision",
            name="noise",
            attributes={"x": 1},
        )
        ts.finish_span(span.span_id, status="ok")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert feed.traces_scanned == 1
        assert feed.shadow_samples == 0
        assert feed.entries == []

    def test_agreement_spans_not_in_entries(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, production_agent="A", brain_agent="A")
        _write_shadow_span(ts, production_agent="B", brain_agent="B")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert feed.shadow_samples == 2
        assert feed.disagreement_samples == 0
        assert feed.entries == []

    def test_disagreement_yields_entry(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(
            ts, production_agent="A", brain_agent="B", score_divergence=0.3
        )

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert feed.shadow_samples == 1
        assert feed.disagreement_samples == 1
        assert len(feed.entries) == 1
        entry = feed.entries[0]
        assert entry.production_agent == "A"
        assert entry.brain_suggested_agent == "B"
        assert entry.score_divergence == pytest.approx(0.3)

    def test_min_score_divergence_filter(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, production_agent="A", brain_agent="B", score_divergence=0.05)
        _write_shadow_span(ts, production_agent="A", brain_agent="C", score_divergence=0.6)

        builder = BrainSuggestionFeedBuilder(
            trace_store=ts, min_score_divergence=0.2
        )
        feed = builder.build()
        assert feed.disagreement_samples == 2
        assert len(feed.entries) == 1
        assert feed.entries[0].brain_suggested_agent == "C"
        assert feed.min_score_divergence == pytest.approx(0.2)

    def test_workflow_filter(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, workflow="wf-keep", production_agent="A", brain_agent="B")
        _write_shadow_span(ts, workflow="wf-keep", production_agent="A", brain_agent="C")
        _write_shadow_span(ts, workflow="wf-skip", production_agent="A", brain_agent="D")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(workflow_filter="wf-keep")
        assert feed.shadow_samples == 2
        assert {e.workflow_name for e in feed.entries} == {"wf-keep"}

    def test_version_filter(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, version_id="v1", production_agent="A", brain_agent="B")
        _write_shadow_span(ts, version_id="v2", production_agent="A", brain_agent="C")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(version_filter="v2")
        assert feed.shadow_samples == 1
        assert len(feed.entries) == 1
        assert feed.entries[0].version_id == "v2"

    def test_max_entries_caps_list_not_counts(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        for idx in range(5):
            _write_shadow_span(
                ts, production_agent="A", brain_agent=f"B{idx}", score_divergence=0.3
            )

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(max_entries=2)
        assert feed.shadow_samples == 5
        assert feed.disagreement_samples == 5
        assert len(feed.entries) == 2

    def test_trace_limit_caps_scan(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        for _ in range(5):
            _write_shadow_span(ts, production_agent="A", brain_agent="B")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(trace_limit=2)
        assert feed.traces_scanned == 2
        assert feed.shadow_samples <= 2

    def test_corrupt_shadow_span_skipped(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        trace = ts.create_trace("wf")
        span = ts.start_span(
            trace.trace_id,
            span_type=BRAIN_SHADOW_SPAN_TYPE,
            name="brain.shadow_evaluation",
            attributes={"brain_shadow.version_id": "v1"},  # incomplete
        )
        ts.finish_span(span.span_id, status="ok")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert feed.shadow_samples == 0
        assert feed.entries == []

    def test_real_runner_produces_agreement_not_suggestion(self, tmp_path):
        """Integration: single-candidate routes always agree → no suggestions surface."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)

        descriptors = [_make_descriptor("a1")]
        intent = _make_intent()
        for _ in range(3):
            trace = ts.create_trace("wf")
            production = RoutingEngine().route_intent(intent, descriptors)
            runner.evaluate(intent, descriptors, production, trace_id=trace.trace_id)

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert feed.shadow_samples == 3
        assert feed.disagreement_samples == 0
        assert feed.entries == []


# ---------------------------------------------------------------------------
# Baseline-report gating
# ---------------------------------------------------------------------------


class TestBaselineGate:
    def test_ungated_surfaces_entries(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, production_agent="A", brain_agent="B")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build()
        assert feed.gated is False
        assert feed.gate_passed is True
        assert len(feed.entries) == 1
        assert "ungated" in feed.gate_reason

    def test_gated_promote_surfaces_entries(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, production_agent="A", brain_agent="B")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(baseline_report=_make_report(recommendation=RECOMMENDATION_PROMOTE))
        assert feed.gated is True
        assert feed.gate_passed is True
        assert len(feed.entries) == 1
        assert RECOMMENDATION_PROMOTE in feed.gate_reason

    def test_gated_observe_hides_entries(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, production_agent="A", brain_agent="B")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(baseline_report=_make_report(recommendation=RECOMMENDATION_OBSERVE))
        assert feed.gated is True
        assert feed.gate_passed is False
        assert feed.entries == []
        # Counts reflect underlying data — only the surface is suppressed.
        assert feed.disagreement_samples == 1

    def test_gated_reject_hides_entries(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        _write_shadow_span(ts, production_agent="A", brain_agent="B")

        builder = BrainSuggestionFeedBuilder(trace_store=ts)
        feed = builder.build(baseline_report=_make_report(recommendation=RECOMMENDATION_REJECT))
        assert feed.gated is True
        assert feed.gate_passed is False
        assert feed.entries == []
        assert RECOMMENDATION_REJECT in feed.gate_reason


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestBuilderConstruction:
    def test_invalid_min_score_divergence_rejected(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        with pytest.raises(ValueError):
            BrainSuggestionFeedBuilder(trace_store=ts, min_score_divergence=-0.1)
        with pytest.raises(ValueError):
            BrainSuggestionFeedBuilder(trace_store=ts, min_score_divergence=1.1)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchema:
    def test_entry_rejects_extra_fields(self):
        with pytest.raises(Exception):
            BrainSuggestionEntry(  # type: ignore[call-arg]
                trace_id="t",
                span_id="s",
                workflow_name="wf",
                version_id="v1",
                production_agent="A",
                brain_suggested_agent="B",
                score_divergence=0.1,
                top_k_overlap=1.0,
                k=3,
                num_candidates=2,
                bogus="x",
            )

    def test_feed_rejects_extra_fields(self):
        with pytest.raises(Exception):
            BrainSuggestionFeed(  # type: ignore[call-arg]
                traces_scanned=0,
                shadow_samples=0,
                disagreement_samples=0,
                entries=[],
                gated=False,
                gate_passed=True,
                gate_reason="x",
                min_score_divergence=0.0,
                bogus="x",
            )
