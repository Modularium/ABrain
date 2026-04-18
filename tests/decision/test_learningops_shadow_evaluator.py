"""Phase 5 – LearningOps L5: ShadowEvaluator tests."""

from __future__ import annotations

import tempfile
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
from core.decision.learning.exporter import DatasetExporter
from core.decision.learning.model_registry import ModelRegistry
from core.decision.learning.offline_trainer import OfflineTrainer, TrainingJobConfig
from core.decision.learning.record import LearningRecord
from core.decision.learning.shadow_evaluator import ShadowComparison, ShadowEvaluator
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _make_descriptor(
    agent_id: str,
    *,
    capabilities: list[str] | None = None,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=capabilities or ["analysis.code"],
        trust_level=AgentTrustLevel.TRUSTED,
        availability=AgentAvailability.ONLINE,
        metadata={
            "success_rate": 0.9,
            "estimated_cost_per_token": 0.001,
            "avg_response_time": 1.0,
        },
    )


def _make_task() -> TaskContext:
    return TaskContext(task_type="code_review", description="Review a module")


def _make_rec(**kw) -> LearningRecord:
    defaults = dict(
        trace_id="t1",
        workflow_name="w1",
        selected_agent_id="agent-A",
        selected_score=0.8,
        routing_confidence=0.9,
        score_gap=0.1,
        candidate_agent_ids=["agent-A"],
        success=True,
        cost_usd=0.002,
        latency_ms=800.0,
        has_routing_decision=True,
        has_outcome=True,
        has_approval_outcome=False,
    )
    defaults.update(kw)
    return LearningRecord(**defaults)


def _train_and_register(tmp_path: Path, registry: ModelRegistry) -> None:
    """Run a minimal training job and register the artefact."""
    records = [_make_rec(trace_id=f"t{i}") for i in range(3)]
    exporter = DatasetExporter(tmp_path / "exports")
    dataset_path = exporter.export(records, filename="ds.jsonl")
    config = TrainingJobConfig(
        dataset_path=dataset_path,
        output_artifact_path=tmp_path / "artifacts" / "model.json",
        min_samples=1,
    )
    result = OfflineTrainer(config).run()
    registry.register(result, config)


def _make_trace(ts: TraceStore) -> str:
    trace = ts.create_trace("shadow-test-workflow")
    return trace.trace_id


# ---------------------------------------------------------------------------
# ShadowComparison schema
# ---------------------------------------------------------------------------


class TestShadowComparison:
    def test_agreement_true_same_agent(self):
        c = ShadowComparison(
            trace_id="t1",
            version_id="abc",
            production_agent_id="A",
            production_score=0.8,
            shadow_agent_id="A",
            shadow_score=0.75,
            agreement=True,
            score_divergence=0.05,
            top_k_overlap=1.0,
            k=3,
        )
        assert c.agreement is True

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            ShadowComparison(  # type: ignore[call-arg]
                trace_id="t1",
                version_id="v",
                agreement=True,
                score_divergence=0.0,
                top_k_overlap=1.0,
                k=1,
                unknown="x",
            )

    def test_score_divergence_clamped(self):
        # pydantic enforces ge=0.0, le=1.0
        with pytest.raises(Exception):
            ShadowComparison(
                trace_id="t",
                version_id="v",
                agreement=False,
                score_divergence=1.5,  # > 1.0
                top_k_overlap=0.5,
                k=1,
            )


# ---------------------------------------------------------------------------
# ShadowEvaluator – no active model
# ---------------------------------------------------------------------------


class TestShadowEvaluatorNoModel:
    def test_returns_none_when_registry_empty(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        engine = RoutingEngine()
        descriptors = [_make_descriptor("a1")]
        production = engine.route(task, descriptors)
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        assert result is None

    def test_no_span_written_when_no_model(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        shadow_spans = [s for s in snapshot.spans if s.span_type == "shadow_eval"]
        assert shadow_spans == []


# ---------------------------------------------------------------------------
# ShadowEvaluator – with active model
# ---------------------------------------------------------------------------


class TestShadowEvaluatorWithModel:
    def test_returns_shadow_comparison(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)

        task = _make_task()
        descriptors = [_make_descriptor("a1"), _make_descriptor("a2", capabilities=["analysis.code"])]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(task, descriptors, production, trace_id=trace_id)

        assert isinstance(result, ShadowComparison)
        assert result.trace_id == trace_id
        assert result.version_id == registry.get_active().version_id

    def test_production_decision_not_modified(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)

        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        original_agent = production.selected_agent_id
        original_score = production.selected_score
        trace_id = _make_trace(ts)

        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)

        assert production.selected_agent_id == original_agent
        assert production.selected_score == original_score

    def test_shadow_span_written_to_trace_store(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)

        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)

        snapshot = ts.get_trace(trace_id)
        shadow_spans = [s for s in snapshot.spans if s.span_type == "shadow_eval"]
        assert len(shadow_spans) == 1

    def test_shadow_span_name_is_canonical(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        span = next(s for s in snapshot.spans if s.span_type == "shadow_eval")
        assert span.name == "learningops.shadow_evaluation"

    def test_shadow_span_attributes_complete(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        span = next(s for s in snapshot.spans if s.span_type == "shadow_eval")
        attrs = span.attributes
        assert "shadow.version_id" in attrs
        assert "shadow.agreement" in attrs
        assert "shadow.score_divergence" in attrs
        assert "shadow.top_k_overlap" in attrs
        assert "shadow.k" in attrs

    def test_span_has_shadow_comparison_event(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        span = next(s for s in snapshot.spans if s.span_type == "shadow_eval")
        event_types = [e.event_type for e in span.events]
        assert "shadow_comparison" in event_types

    def test_span_status_is_ok(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        span = next(s for s in snapshot.spans if s.span_type == "shadow_eval")
        assert span.status == "ok"

    def test_agreement_true_when_agents_match(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        # Single descriptor → both must select the same agent
        descriptors = [_make_descriptor("only-agent")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        # With one candidate both production and shadow select the same agent
        if result is not None and production.selected_agent_id is not None:
            assert result.agreement is True

    def test_score_divergence_in_unit_interval(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor("a1"), _make_descriptor("a2")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        if result is not None:
            assert 0.0 <= result.score_divergence <= 1.0

    def test_top_k_overlap_in_unit_interval(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts)
        task = _make_task()
        descriptors = [_make_descriptor(f"a{i}") for i in range(4)]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        if result is not None:
            assert 0.0 <= result.top_k_overlap <= 1.0

    def test_custom_k_respected(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)
        evaluator = ShadowEvaluator(registry=registry, trace_store=ts, k=5)
        task = _make_task()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(task, descriptors)
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(task, descriptors, production, trace_id=trace_id)
        if result is not None:
            assert result.k == 5

    def test_shadow_error_returns_none_not_raises(self, tmp_path):
        """Shadow failures must never raise into the production path."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_and_register(tmp_path, registry)

        class _BrokenEvaluator(ShadowEvaluator):
            def _run_shadow(self, **_kw):
                raise RuntimeError("simulated shadow engine failure")

        evaluator = _BrokenEvaluator(registry=registry, trace_store=ts)
        production = RoutingEngine().route(_make_task(), [_make_descriptor("a1")])
        trace_id = _make_trace(ts)
        result = evaluator.evaluate(_make_task(), [_make_descriptor("a1")], production, trace_id=trace_id)
        assert result is None
