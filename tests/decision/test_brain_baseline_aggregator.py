"""Phase 6 – Brain v1 B6-S5: BrainBaselineAggregator tests."""

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
    BrainBaselineAggregator,
    BrainBaselineMetrics,
    BrainBaselineReport,
    BrainShadowEvalSummary,
    _compute_metrics,
    _summary_from_span,
)
from core.decision.brain.shadow_runner import BrainShadowRunner
from core.decision.brain.state import (
    BrainAgentSignal,
    BrainPolicySignals,
    BrainRecord,
    BrainState,
    BrainTarget,
)
from core.decision.brain.trainer import (
    BrainOfflineTrainer,
    BrainTrainingJobConfig,
    save_brain_records,
)
from core.decision.learning.model_registry import ModelRegistry
from core.decision.task_intent import TaskIntent
from core.model_context import TaskContext

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
    agreement: bool = True,
    score_divergence: float = 0.1,
    top_k_overlap: float = 1.0,
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
        production_agent="A",
        brain_agent="A" if agreement else "B",
        agreement=agreement,
        score_divergence=score_divergence,
        top_k_overlap=top_k_overlap,
        k=k,
        num_candidates=num_candidates,
    )


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


def _emit_shadow_eval(
    ts: TraceStore,
    runner: BrainShadowRunner,
    *,
    workflow: str = "wf",
    descriptors: list[AgentDescriptor] | None = None,
) -> str:
    descriptors = descriptors or [_make_descriptor("a1")]
    trace = ts.create_trace(workflow)
    intent = _make_intent()
    production = RoutingEngine().route_intent(intent, descriptors)
    runner.evaluate(intent, descriptors, production, trace_id=trace.trace_id)
    return trace.trace_id


# ---------------------------------------------------------------------------
# _summary_from_span
# ---------------------------------------------------------------------------


class TestSummaryFromSpan:
    def test_extracts_all_attributes(self):
        from datetime import UTC, datetime

        attrs = {
            "brain_shadow.version_id": "v1",
            "brain_shadow.production_agent": "A",
            "brain_shadow.brain_agent": "A",
            "brain_shadow.agreement": True,
            "brain_shadow.score_divergence": 0.1,
            "brain_shadow.top_k_overlap": 1.0,
            "brain_shadow.k": 3,
            "brain_shadow.num_candidates": 2,
        }
        summary = _summary_from_span(
            trace_id="t",
            workflow_name="wf",
            span_attributes=attrs,
            span_id="s",
            started_at=datetime.now(UTC),
        )
        assert summary is not None
        assert summary.version_id == "v1"
        assert summary.agreement is True

    def test_missing_attribute_returns_none(self):
        from datetime import UTC, datetime

        attrs = {"brain_shadow.version_id": "v1"}  # incomplete
        summary = _summary_from_span(
            trace_id="t",
            workflow_name="wf",
            span_attributes=attrs,
            span_id="s",
            started_at=datetime.now(UTC),
        )
        assert summary is None

    def test_invalid_value_returns_none(self):
        from datetime import UTC, datetime

        attrs = {
            "brain_shadow.version_id": "v1",
            "brain_shadow.production_agent": None,
            "brain_shadow.brain_agent": "A",
            "brain_shadow.agreement": True,
            "brain_shadow.score_divergence": "not-a-float",  # type error
            "brain_shadow.top_k_overlap": 1.0,
            "brain_shadow.k": 3,
            "brain_shadow.num_candidates": 2,
        }
        summary = _summary_from_span(
            trace_id="t",
            workflow_name="wf",
            span_attributes=attrs,
            span_id="s",
            started_at=datetime.now(UTC),
        )
        assert summary is None

    def test_none_production_agent_preserved(self):
        from datetime import UTC, datetime

        attrs = {
            "brain_shadow.version_id": "v1",
            "brain_shadow.production_agent": None,
            "brain_shadow.brain_agent": "A",
            "brain_shadow.agreement": False,
            "brain_shadow.score_divergence": 1.0,
            "brain_shadow.top_k_overlap": 0.0,
            "brain_shadow.k": 3,
            "brain_shadow.num_candidates": 1,
        }
        summary = _summary_from_span(
            trace_id="t",
            workflow_name="wf",
            span_attributes=attrs,
            span_id="s",
            started_at=datetime.now(UTC),
        )
        assert summary is not None
        assert summary.production_agent is None


# ---------------------------------------------------------------------------
# _compute_metrics
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_empty_yields_zero_metrics(self):
        m = _compute_metrics([])
        assert m.sample_count == 0
        assert m.agreement_rate == 0.0
        assert m.coverage_workflows == 0
        assert m.coverage_versions == 0

    def test_all_agree_yields_rate_1(self):
        summaries = [_make_summary(trace_id=f"t{i}", agreement=True) for i in range(5)]
        m = _compute_metrics(summaries)
        assert m.sample_count == 5
        assert m.agreement_rate == 1.0

    def test_all_disagree_yields_rate_0(self):
        summaries = [
            _make_summary(trace_id=f"t{i}", agreement=False, score_divergence=0.5)
            for i in range(4)
        ]
        m = _compute_metrics(summaries)
        assert m.agreement_rate == 0.0
        assert m.mean_score_divergence == pytest.approx(0.5)

    def test_mixed_yields_fractional_rate(self):
        summaries = [_make_summary(trace_id="t1", agreement=True)] * 3 + [
            _make_summary(trace_id="t2", agreement=False)
        ]
        m = _compute_metrics(summaries)
        assert m.agreement_rate == pytest.approx(0.75)

    def test_coverage_counts_distinct(self):
        summaries = [
            _make_summary(trace_id="t1", workflow_name="wf-a", version_id="v1"),
            _make_summary(trace_id="t2", workflow_name="wf-b", version_id="v1"),
            _make_summary(trace_id="t3", workflow_name="wf-a", version_id="v2"),
        ]
        m = _compute_metrics(summaries)
        assert m.coverage_workflows == 2
        assert m.coverage_versions == 2

    def test_median_computed(self):
        divs = [0.1, 0.2, 0.3, 0.9]
        summaries = [
            _make_summary(trace_id=f"t{i}", score_divergence=d) for i, d in enumerate(divs)
        ]
        m = _compute_metrics(summaries)
        assert m.median_score_divergence == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Recommendation logic (via aggregator with synthetic spans)
# ---------------------------------------------------------------------------


class TestRecommendation:
    def _agg(self, **overrides):
        return BrainBaselineAggregator(
            trace_store=None,  # type: ignore[arg-type] — _recommend doesn't need it
            **overrides,
        )

    def test_no_samples_observes(self):
        m = BrainBaselineMetrics(
            sample_count=0,
            agreement_rate=0.0,
            mean_score_divergence=0.0,
            median_score_divergence=0.0,
            mean_top_k_overlap=0.0,
            coverage_workflows=0,
            coverage_versions=0,
        )
        rec, reason = self._agg()._recommend(m)
        assert rec == RECOMMENDATION_OBSERVE
        assert "no brain_shadow_eval" in reason

    def test_few_samples_observes_even_at_high_agreement(self):
        m = BrainBaselineMetrics(
            sample_count=5,
            agreement_rate=1.0,
            mean_score_divergence=0.0,
            median_score_divergence=0.0,
            mean_top_k_overlap=1.0,
            coverage_workflows=1,
            coverage_versions=1,
        )
        rec, reason = self._agg(min_samples_for_promote=30)._recommend(m)
        assert rec == RECOMMENDATION_OBSERVE
        assert "min_samples_for_promote" in reason

    def test_strong_agreement_promotes(self):
        m = BrainBaselineMetrics(
            sample_count=100,
            agreement_rate=0.9,
            mean_score_divergence=0.05,
            median_score_divergence=0.04,
            mean_top_k_overlap=0.95,
            coverage_workflows=3,
            coverage_versions=1,
        )
        rec, _ = self._agg()._recommend(m)
        assert rec == RECOMMENDATION_PROMOTE

    def test_high_divergence_blocks_promote(self):
        m = BrainBaselineMetrics(
            sample_count=100,
            agreement_rate=0.9,
            mean_score_divergence=0.5,
            median_score_divergence=0.5,
            mean_top_k_overlap=0.9,
            coverage_workflows=1,
            coverage_versions=1,
        )
        rec, reason = self._agg()._recommend(m)
        assert rec == RECOMMENDATION_OBSERVE
        assert "mean_score_divergence" in reason

    def test_low_agreement_high_samples_rejects(self):
        m = BrainBaselineMetrics(
            sample_count=200,
            agreement_rate=0.1,
            mean_score_divergence=0.7,
            median_score_divergence=0.7,
            mean_top_k_overlap=0.2,
            coverage_workflows=2,
            coverage_versions=1,
        )
        rec, reason = self._agg()._recommend(m)
        assert rec == RECOMMENDATION_REJECT
        assert "agreement_rate" in reason

    def test_low_agreement_few_samples_observes_not_rejects(self):
        m = BrainBaselineMetrics(
            sample_count=5,
            agreement_rate=0.0,
            mean_score_divergence=1.0,
            median_score_divergence=1.0,
            mean_top_k_overlap=0.0,
            coverage_workflows=1,
            coverage_versions=1,
        )
        rec, _ = self._agg(min_samples_for_reject=10)._recommend(m)
        assert rec == RECOMMENDATION_OBSERVE


# ---------------------------------------------------------------------------
# BrainBaselineAggregator.aggregate – TraceStore integration
# ---------------------------------------------------------------------------


class TestAggregateAgainstTraceStore:
    def test_empty_store_yields_zero_samples(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate()
        assert isinstance(report, BrainBaselineReport)
        assert report.samples == 0
        assert report.recommendation == RECOMMENDATION_OBSERVE
        assert report.overall.sample_count == 0

    def test_traces_without_shadow_spans_are_skipped(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        # Create a trace with an unrelated span — should not contribute.
        trace = ts.create_trace("noisy-wf")
        span = ts.start_span(
            trace.trace_id,
            span_type="routing_decision",
            name="noise",
            attributes={"x": 1},
        )
        ts.finish_span(span.span_id, status="ok")

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate()
        assert report.samples == 0
        assert report.traces_scanned == 1

    def test_aggregates_real_shadow_spans(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        version_id = _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        for _ in range(3):
            _emit_shadow_eval(ts, runner)

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate()
        assert report.samples == 3
        assert report.overall.sample_count == 3
        assert version_id in report.per_version
        assert "wf" in report.per_workflow

    def test_workflow_filter_excludes_other_workflows(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        _emit_shadow_eval(ts, runner, workflow="wf-keep")
        _emit_shadow_eval(ts, runner, workflow="wf-keep")
        _emit_shadow_eval(ts, runner, workflow="wf-skip")

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate(workflow_filter="wf-keep")
        assert report.samples == 2
        assert set(report.per_workflow) == {"wf-keep"}

    def test_version_filter_excludes_other_versions(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        version_id = _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        _emit_shadow_eval(ts, runner)

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate(version_filter="nonexistent-version")
        assert report.samples == 0

        report_match = agg.aggregate(version_filter=version_id)
        assert report_match.samples == 1

    def test_per_version_breakdown_isolates_versions(self, tmp_path):
        """Two registered Brain models produce separate per-version metric slots."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        v1 = _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        _emit_shadow_eval(ts, runner)

        v2 = _train_brain_and_register(tmp_path, registry)
        # New active version → next eval uses v2
        runner2 = BrainShadowRunner(registry=registry, trace_store=ts)
        _emit_shadow_eval(ts, runner2)

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate()
        assert v1 in report.per_version
        assert v2 in report.per_version
        assert report.per_version[v1].sample_count == 1
        assert report.per_version[v2].sample_count == 1

    def test_promotion_thresholds_serialised_in_report(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        agg = BrainBaselineAggregator(
            trace_store=ts,
            min_agreement_for_promote=0.8,
            max_divergence_for_promote=0.15,
            min_samples_for_promote=50,
        )
        report = agg.aggregate()
        assert report.promotion_thresholds["min_agreement_for_promote"] == 0.8
        assert report.promotion_thresholds["max_divergence_for_promote"] == 0.15
        assert report.promotion_thresholds["min_samples_for_promote"] == 50.0

    def test_recommendation_observes_when_few_samples(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        for _ in range(3):
            _emit_shadow_eval(ts, runner)

        agg = BrainBaselineAggregator(trace_store=ts, min_samples_for_promote=30)
        report = agg.aggregate()
        assert report.recommendation == RECOMMENDATION_OBSERVE

    def test_recommendation_promotes_with_lowered_thresholds(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        # Single-candidate routes always agree (production = brain = only agent).
        for _ in range(3):
            _emit_shadow_eval(ts, runner)

        agg = BrainBaselineAggregator(
            trace_store=ts,
            min_samples_for_promote=2,
            min_agreement_for_promote=0.5,
            max_divergence_for_promote=1.0,
        )
        report = agg.aggregate()
        assert report.overall.agreement_rate == 1.0
        assert report.recommendation == RECOMMENDATION_PROMOTE

    def test_trace_limit_caps_scan(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        for _ in range(5):
            _emit_shadow_eval(ts, runner)

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate(trace_limit=2)
        assert report.traces_scanned == 2
        assert report.samples <= 2

    def test_corrupt_shadow_span_skipped_not_raised(self, tmp_path):
        """Defensive: malformed brain_shadow_eval span attributes must not raise."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        trace = ts.create_trace("wf")
        span = ts.start_span(
            trace.trace_id,
            span_type=BRAIN_SHADOW_SPAN_TYPE,
            name="brain.shadow_evaluation",
            attributes={"brain_shadow.version_id": "v1"},  # missing required keys
        )
        ts.finish_span(span.span_id, status="ok")

        agg = BrainBaselineAggregator(trace_store=ts)
        report = agg.aggregate()
        assert report.samples == 0
        assert report.traces_scanned == 1


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestReportSchema:
    def test_extra_fields_rejected_on_report(self):
        with pytest.raises(Exception):
            BrainBaselineReport(  # type: ignore[call-arg]
                traces_scanned=0,
                samples=0,
                overall=BrainBaselineMetrics(
                    sample_count=0,
                    agreement_rate=0.0,
                    mean_score_divergence=0.0,
                    median_score_divergence=0.0,
                    mean_top_k_overlap=0.0,
                    coverage_workflows=0,
                    coverage_versions=0,
                ),
                recommendation=RECOMMENDATION_OBSERVE,
                recommendation_reason="x",
                bogus="x",
            )

    def test_extra_fields_rejected_on_metrics(self):
        with pytest.raises(Exception):
            BrainBaselineMetrics(  # type: ignore[call-arg]
                sample_count=0,
                agreement_rate=0.0,
                mean_score_divergence=0.0,
                median_score_divergence=0.0,
                mean_top_k_overlap=0.0,
                coverage_workflows=0,
                coverage_versions=0,
                bogus=1,
            )
