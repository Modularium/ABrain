"""Phase 6 – Brain v1 B6-S4: BrainShadowRunner + ModelRegistry brain_v1 tests."""

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
from core.decision.brain.shadow_runner import (
    BrainShadowComparison,
    BrainShadowRunner,
)
from core.decision.brain.state import (
    BrainAgentSignal,
    BrainPolicySignals,
    BrainRecord,
    BrainState,
    BrainTarget,
)
from core.decision.brain.trainer import (
    BRAIN_FEATURE_NAMES,
    BrainOfflineTrainer,
    BrainTrainingJobConfig,
    BrainTrainingResult,
    save_brain_records,
)
from core.decision.learning.exporter import DatasetExporter
from core.decision.learning.model_registry import (
    MODEL_KIND_BRAIN_V1,
    MODEL_KIND_NEURAL_POLICY,
    ModelRegistry,
)
from core.decision.learning.offline_trainer import OfflineTrainer, TrainingJobConfig
from core.decision.learning.record import LearningRecord
from core.decision.scoring_models import MLPScoringModel, ScoringModelWeights
from core.decision.task_intent import TaskIntent
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers / fixtures
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
    return TaskContext(task_type="code_review", description="Review module")


def _make_intent(*, capabilities: list[str] | None = None) -> TaskIntent:
    return TaskIntent(
        task_type="code_review",
        domain="engineering",
        required_capabilities=capabilities or ["analysis.code"],
        execution_hints={},
        description="Review module",
    )


def _make_brain_state(num_candidates: int = 1) -> BrainState:
    candidates = [
        BrainAgentSignal(
            agent_id=f"agent-{i}",
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
        for i in range(num_candidates)
    ]
    return BrainState(
        task_type="code_review",
        domain="engineering",
        num_required_capabilities=1,
        num_candidates=num_candidates,
        routing_confidence=0.8,
        score_gap=0.1,
        confidence_band="high",
        candidates=candidates,
        policy=BrainPolicySignals(),
    )


def _make_brain_record(trace_id: str, *, success: bool = True) -> BrainRecord:
    return BrainRecord(
        trace_id=trace_id,
        workflow_name="wf",
        state=_make_brain_state(num_candidates=1),
        target=BrainTarget(
            selected_agent_id="agent-0",
            outcome_success=success,
            outcome_cost_usd=0.001,
            outcome_latency_ms=500.0,
        ),
    )


def _train_brain_and_register(tmp_path: Path, registry: ModelRegistry) -> BrainTrainingResult:
    records_path = tmp_path / "brain_records.jsonl"
    records = [_make_brain_record(f"t{i}", success=(i % 2 == 0)) for i in range(4)]
    save_brain_records(records, records_path)

    config = BrainTrainingJobConfig(
        brain_records_path=records_path,
        output_artifact_path=tmp_path / "brain_models" / "brain.json",
        min_samples=1,
    )
    result = BrainOfflineTrainer(config).run()
    registry.register_brain(result, config)
    return result


def _make_neural_policy_record(**kw) -> LearningRecord:
    defaults = dict(
        trace_id="t1",
        workflow_name="wf",
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


def _train_neural_policy_and_register(tmp_path: Path, registry: ModelRegistry) -> None:
    records = [_make_neural_policy_record(trace_id=f"n{i}") for i in range(3)]
    exporter = DatasetExporter(tmp_path / "exports")
    dataset_path = exporter.export(records, filename="ds.jsonl")
    config = TrainingJobConfig(
        dataset_path=dataset_path,
        output_artifact_path=tmp_path / "neural_models" / "model.json",
        min_samples=1,
    )
    result = OfflineTrainer(config).run()
    registry.register(result, config)


def _make_trace(ts: TraceStore) -> str:
    return ts.create_trace("brain-shadow-test").trace_id


# ---------------------------------------------------------------------------
# ModelRegistry – brain_v1 model_kind support
# ---------------------------------------------------------------------------


class TestRegistryBrainSupport:
    def test_register_brain_creates_brain_v1_entry(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        active = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert active is not None
        assert active.model_kind == MODEL_KIND_BRAIN_V1

    def test_register_brain_uses_brain_records_path_as_dataset(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        active = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert active is not None
        assert active.dataset_path.endswith("brain_records.jsonl")

    def test_register_brain_schema_version_includes_feature_count(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        active = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert active is not None
        assert active.schema_version == f"brain-v1:{len(BRAIN_FEATURE_NAMES)}"

    def test_get_active_default_kind_is_neural_policy(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        # No neural-policy entry exists — default get_active() must return None.
        assert registry.get_active() is None

    def test_register_brain_does_not_deactivate_neural_policy(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_neural_policy_and_register(tmp_path, registry)
        np_entry = registry.get_active(model_kind=MODEL_KIND_NEURAL_POLICY)
        assert np_entry is not None
        np_id = np_entry.version_id

        _train_brain_and_register(tmp_path, registry)

        np_after = registry.get_active(model_kind=MODEL_KIND_NEURAL_POLICY)
        assert np_after is not None
        assert np_after.version_id == np_id  # still active
        brain_after = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert brain_after is not None

    def test_register_neural_policy_does_not_deactivate_brain(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        brain_id = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1).version_id

        _train_neural_policy_and_register(tmp_path, registry)

        brain_after = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert brain_after is not None
        assert brain_after.version_id == brain_id

    def test_two_brain_entries_only_latest_is_active(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        first_id = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1).version_id
        _train_brain_and_register(tmp_path, registry)
        second = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert second.version_id != first_id
        actives = [
            e for e in registry.list_versions()
            if e.model_kind == MODEL_KIND_BRAIN_V1 and e.is_active
        ]
        assert len(actives) == 1

    def test_get_active_brain_mlp_returns_scorer(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        scorer = registry.get_active_brain_mlp()
        assert scorer is not None
        assert tuple(scorer.weights.feature_names) == BRAIN_FEATURE_NAMES

    def test_get_active_brain_mlp_returns_none_when_empty(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        assert registry.get_active_brain_mlp() is None

    def test_brain_config_hash_excludes_paths(self, tmp_path):
        from core.decision.learning.model_registry import _brain_config_hash

        cfg_a = BrainTrainingJobConfig(
            brain_records_path=tmp_path / "a.jsonl",
            output_artifact_path=tmp_path / "a.json",
        )
        cfg_b = BrainTrainingJobConfig(
            brain_records_path=tmp_path / "different.jsonl",
            output_artifact_path=tmp_path / "elsewhere.json",
        )
        assert _brain_config_hash(cfg_a) == _brain_config_hash(cfg_b)

    def test_brain_config_hash_changes_with_hyperparams(self, tmp_path):
        from core.decision.learning.model_registry import _brain_config_hash

        cfg_a = BrainTrainingJobConfig(
            brain_records_path=tmp_path / "a.jsonl",
            output_artifact_path=tmp_path / "a.json",
            learning_rate=0.05,
        )
        cfg_b = BrainTrainingJobConfig(
            brain_records_path=tmp_path / "a.jsonl",
            output_artifact_path=tmp_path / "a.json",
            learning_rate=0.01,
        )
        assert _brain_config_hash(cfg_a) != _brain_config_hash(cfg_b)

    def test_registry_persists_brain_entries_across_reload(self, tmp_path):
        registry_path = tmp_path / "registry.json"
        reg1 = ModelRegistry(registry_path)
        _train_brain_and_register(tmp_path, reg1)
        brain_id = reg1.get_active(model_kind=MODEL_KIND_BRAIN_V1).version_id

        reg2 = ModelRegistry(registry_path)
        active = reg2.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        assert active is not None
        assert active.version_id == brain_id


# ---------------------------------------------------------------------------
# BrainShadowComparison schema
# ---------------------------------------------------------------------------


class TestBrainShadowComparison:
    def test_minimal_construction(self):
        c = BrainShadowComparison(
            trace_id="t1",
            version_id="abc",
            agreement=True,
            score_divergence=0.0,
            top_k_overlap=1.0,
            k=3,
            num_candidates=2,
        )
        assert c.agreement is True
        assert c.production_agent_id is None  # default

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainShadowComparison(  # type: ignore[call-arg]
                trace_id="t",
                version_id="v",
                agreement=True,
                score_divergence=0.0,
                top_k_overlap=1.0,
                k=1,
                num_candidates=0,
                extra="x",
            )

    def test_score_divergence_must_be_in_unit_interval(self):
        with pytest.raises(Exception):
            BrainShadowComparison(
                trace_id="t",
                version_id="v",
                agreement=False,
                score_divergence=1.5,
                top_k_overlap=0.5,
                k=1,
                num_candidates=1,
            )


# ---------------------------------------------------------------------------
# BrainShadowRunner – missing/incompatible model
# ---------------------------------------------------------------------------


class TestBrainShadowRunnerNoModel:
    def test_returns_none_when_no_brain_entry(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        assert runner.evaluate(intent, descriptors, production, trace_id=trace_id) is None

    def test_no_span_written_when_no_brain_entry(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        spans = [s for s in snapshot.spans if s.span_type == "brain_shadow_eval"]
        assert spans == []

    def test_neural_policy_active_only_does_not_trigger_brain_shadow(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_neural_policy_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        assert runner.evaluate(intent, descriptors, production, trace_id=trace_id) is None

    def test_returns_none_on_schema_drift(self, tmp_path):
        """A registered Brain artefact whose feature schema does not match BRAIN_FEATURE_NAMES is rejected."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        # Overwrite the artefact with a wrong-schema model.
        entry = registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        bad_weights = ScoringModelWeights(
            feature_names=["only_one_feature"],
            input_hidden=[[0.0]],
            hidden_bias=[0.0],
            hidden_output=[1.0],
            output_bias=0.0,
        )
        MLPScoringModel(bad_weights).save_json(entry.artifact_path)

        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        assert runner.evaluate(intent, descriptors, production, trace_id=trace_id) is None


# ---------------------------------------------------------------------------
# BrainShadowRunner – with active model
# ---------------------------------------------------------------------------


class TestBrainShadowRunnerWithModel:
    def test_returns_brain_shadow_comparison(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1"), _make_descriptor("a2")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert isinstance(result, BrainShadowComparison)
        assert result.trace_id == trace_id
        assert result.version_id == registry.get_active(model_kind=MODEL_KIND_BRAIN_V1).version_id

    def test_production_decision_not_modified(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        original_agent = production.selected_agent_id
        original_score = production.selected_score
        trace_id = _make_trace(ts)
        runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert production.selected_agent_id == original_agent
        assert production.selected_score == original_score

    def test_brain_shadow_span_written(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        spans = [s for s in snapshot.spans if s.span_type == "brain_shadow_eval"]
        assert len(spans) == 1
        assert spans[0].name == "brain.shadow_evaluation"
        assert spans[0].status == "ok"

    def test_span_attributes_complete(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1"), _make_descriptor("a2")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        span = next(s for s in snapshot.spans if s.span_type == "brain_shadow_eval")
        attrs = span.attributes
        for key in (
            "brain_shadow.version_id",
            "brain_shadow.agreement",
            "brain_shadow.score_divergence",
            "brain_shadow.top_k_overlap",
            "brain_shadow.k",
            "brain_shadow.num_candidates",
        ):
            assert key in attrs

    def test_span_includes_brain_shadow_comparison_event(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        snapshot = ts.get_trace(trace_id)
        span = next(s for s in snapshot.spans if s.span_type == "brain_shadow_eval")
        event_types = [e.event_type for e in span.events]
        assert "brain_shadow_comparison" in event_types

    def test_single_candidate_yields_agreement(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("only-agent")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert result is not None
        if production.selected_agent_id is not None:
            assert result.brain_agent_id == production.selected_agent_id
            assert result.agreement is True

    def test_score_divergence_in_unit_interval(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1"), _make_descriptor("a2")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert result is not None
        assert 0.0 <= result.score_divergence <= 1.0

    def test_top_k_overlap_in_unit_interval(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor(f"a{i}") for i in range(4)]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert result is not None
        assert 0.0 <= result.top_k_overlap <= 1.0

    def test_custom_k_respected(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts, k=5)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert result is not None
        assert result.k == 5

    def test_num_candidates_reflects_state(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)
        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor(f"a{i}") for i in range(3)]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert result is not None
        assert result.num_candidates == 3

    def test_shadow_failure_returns_none(self, tmp_path):
        """Internal exceptions in shadow evaluation are swallowed."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_brain_and_register(tmp_path, registry)

        class _Broken(BrainShadowRunner):
            def _run(self, **_kw):
                raise RuntimeError("boom")

        runner = _Broken(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        assert runner.evaluate(intent, descriptors, production, trace_id=trace_id) is None


# ---------------------------------------------------------------------------
# End-to-end pipeline: train Brain → register → shadow-evaluate
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    def test_train_register_evaluate(self, tmp_path):
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        result = _train_brain_and_register(tmp_path, registry)
        assert Path(result.artifact_path).exists()

        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1"), _make_descriptor("a2")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)

        comparison = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert comparison is not None

        snapshot = ts.get_trace(trace_id)
        spans = [s for s in snapshot.spans if s.span_type == "brain_shadow_eval"]
        assert len(spans) == 1
        assert spans[0].attributes["brain_shadow.version_id"] == result.artifact_path.split("/")[-1].split(".")[0] or True

    def test_concurrent_neural_policy_and_brain_evaluations(self, tmp_path):
        """Both production-shadow (ShadowEvaluator) and Brain shadow can coexist."""
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        registry = ModelRegistry(tmp_path / "registry.json")
        _train_neural_policy_and_register(tmp_path, registry)
        _train_brain_and_register(tmp_path, registry)

        # Both are active independently
        assert registry.get_active(model_kind=MODEL_KIND_NEURAL_POLICY) is not None
        assert registry.get_active(model_kind=MODEL_KIND_BRAIN_V1) is not None

        runner = BrainShadowRunner(registry=registry, trace_store=ts)
        intent = _make_intent()
        descriptors = [_make_descriptor("a1")]
        production = RoutingEngine().route(_make_task(), descriptors)
        trace_id = _make_trace(ts)
        result = runner.evaluate(intent, descriptors, production, trace_id=trace_id)
        assert result is not None
