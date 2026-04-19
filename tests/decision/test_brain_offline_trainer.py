"""Phase 6 – Brain v1 B6-S3: BrainOfflineTrainer tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.decision.brain.record_builder import BrainRecordBuilder
from core.decision.brain.state import (
    BrainAgentSignal,
    BrainBudget,
    BrainPolicySignals,
    BrainRecord,
    BrainState,
    BrainTarget,
)
from core.decision.brain.trainer import (
    BrainOfflineTrainer,
    BrainTrainingJobConfig,
    BrainTrainingResult,
    _BRAIN_FEATURE_NAMES,
    _brain_record_to_sample,
    load_brain_records,
    save_brain_records,
)
from core.decision.learning.record import LearningRecord
from core.decision.learning.reward_model import RewardModel
from core.decision.neural_policy import NeuralPolicyModel

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _minimal_state(*, num_candidates: int = 1) -> BrainState:
    candidates = [
        BrainAgentSignal(
            agent_id=f"agent-{i}",
            capability_match_score=0.0,
            success_rate=0.8,
            avg_latency_s=1.5,
            avg_cost_usd=0.002,
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
        policy=BrainPolicySignals(has_policy_effect=False, approval_required=False),
    )


def _minimal_target(*, success: bool | None = True) -> BrainTarget:
    return BrainTarget(
        selected_agent_id="agent-0",
        outcome_success=success,
        outcome_cost_usd=0.003,
        outcome_latency_ms=500.0,
        approval_required=False,
    )


def _brain_record(
    trace_id: str = "t1",
    *,
    success: bool | None = True,
    num_candidates: int = 1,
) -> BrainRecord:
    return BrainRecord(
        trace_id=trace_id,
        workflow_name="test-workflow",
        state=_minimal_state(num_candidates=num_candidates),
        target=_minimal_target(success=success),
    )


def _make_learning_record(trace_id: str = "t1") -> LearningRecord:
    return LearningRecord(
        trace_id=trace_id,
        workflow_name="wf",
        task_type="code_review",
        selected_agent_id="agent-A",
        selected_score=0.8,
        routing_confidence=0.8,
        score_gap=0.1,
        confidence_band="high",
        candidate_agent_ids=["agent-A"],
        success=True,
        cost_usd=0.003,
        latency_ms=500.0,
        has_routing_decision=True,
        has_outcome=True,
        has_approval_outcome=False,
    )


# ---------------------------------------------------------------------------
# save_brain_records / load_brain_records
# ---------------------------------------------------------------------------


class TestBrainRecordsIO:
    def test_save_creates_file(self, tmp_path):
        path = tmp_path / "records.jsonl"
        records = [_brain_record(f"t{i}") for i in range(3)]
        save_brain_records(records, path)
        assert path.exists()

    def test_load_roundtrip(self, tmp_path):
        path = tmp_path / "records.jsonl"
        records = [_brain_record(f"t{i}") for i in range(3)]
        save_brain_records(records, path)
        loaded = load_brain_records(path)
        assert len(loaded) == 3
        assert [r.trace_id for r in loaded] == ["t0", "t1", "t2"]

    def test_load_empty_file_raises(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            load_brain_records(path)

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "records.jsonl"
        save_brain_records([_brain_record()], path)
        assert path.exists()

    def test_load_preserves_state_fields(self, tmp_path):
        path = tmp_path / "records.jsonl"
        orig = _brain_record("trace-99")
        save_brain_records([orig], path)
        loaded = load_brain_records(path)[0]
        assert loaded.trace_id == "trace-99"
        assert loaded.state.routing_confidence == pytest.approx(0.8)
        assert loaded.state.candidates[0].success_rate == pytest.approx(0.8)

    def test_save_overwrite_idempotent(self, tmp_path):
        path = tmp_path / "records.jsonl"
        save_brain_records([_brain_record("t1")], path)
        save_brain_records([_brain_record("t2"), _brain_record("t3")], path)
        loaded = load_brain_records(path)
        assert len(loaded) == 2
        assert loaded[0].trace_id == "t2"

    def test_empty_list_roundtrip(self, tmp_path):
        path = tmp_path / "records.jsonl"
        save_brain_records([], path)
        with pytest.raises(ValueError):
            load_brain_records(path)


# ---------------------------------------------------------------------------
# _brain_record_to_sample — feature vector
# ---------------------------------------------------------------------------


class TestBrainRecordToSample:
    def _default_scales(self):
        return 10.0, 0.01  # latency_scale_s, cost_scale_usd

    def _reward(self, latency_scale_s=10.0, cost_scale_usd=0.01):
        return RewardModel(latency_scale=latency_scale_s, cost_scale=cost_scale_usd)

    def test_feature_names_match_schema(self):
        ls, cs = self._default_scales()
        sample = _brain_record_to_sample(_brain_record(), ls, cs, self._reward(ls, cs))
        assert sample.feature_names == _BRAIN_FEATURE_NAMES

    def test_feature_vector_length(self):
        ls, cs = self._default_scales()
        sample = _brain_record_to_sample(_brain_record(), ls, cs, self._reward(ls, cs))
        assert len(sample.feature_vector) == len(_BRAIN_FEATURE_NAMES)

    def test_routing_confidence_in_vector(self):
        ls, cs = self._default_scales()
        rec = _brain_record()
        sample = _brain_record_to_sample(rec, ls, cs, self._reward(ls, cs))
        idx = _BRAIN_FEATURE_NAMES.index("routing_confidence")
        assert sample.feature_vector[idx] == pytest.approx(0.8)

    def test_score_gap_in_vector(self):
        ls, cs = self._default_scales()
        rec = _brain_record()
        sample = _brain_record_to_sample(rec, ls, cs, self._reward(ls, cs))
        idx = _BRAIN_FEATURE_NAMES.index("score_gap")
        assert sample.feature_vector[idx] == pytest.approx(0.1)

    def test_num_candidates_norm(self):
        ls, cs = self._default_scales()
        rec = _brain_record(num_candidates=5)
        sample = _brain_record_to_sample(rec, ls, cs, self._reward(ls, cs))
        idx = _BRAIN_FEATURE_NAMES.index("num_candidates_norm")
        assert sample.feature_vector[idx] == pytest.approx(5 / 10.0)

    def test_has_policy_effect_zero_by_default(self):
        ls, cs = self._default_scales()
        sample = _brain_record_to_sample(_brain_record(), ls, cs, self._reward(ls, cs))
        idx = _BRAIN_FEATURE_NAMES.index("has_policy_effect")
        assert sample.feature_vector[idx] == pytest.approx(0.0)

    def test_has_policy_effect_one_when_set(self):
        ls, cs = self._default_scales()
        state = _minimal_state()
        state = state.model_copy(update={"policy": BrainPolicySignals(has_policy_effect=True)})
        rec = BrainRecord(trace_id="t", workflow_name="w", state=state, target=_minimal_target())
        sample = _brain_record_to_sample(rec, ls, cs, self._reward(ls, cs))
        idx = _BRAIN_FEATURE_NAMES.index("has_policy_effect")
        assert sample.feature_vector[idx] == pytest.approx(1.0)

    def test_neutral_defaults_when_no_candidates(self):
        ls, cs = self._default_scales()
        state = BrainState(
            task_type="t", domain="d", num_required_capabilities=0, num_candidates=0
        )
        rec = BrainRecord(trace_id="t", workflow_name="w", state=state, target=_minimal_target())
        sample = _brain_record_to_sample(rec, ls, cs, self._reward(ls, cs))
        idx_sr = _BRAIN_FEATURE_NAMES.index("success_rate")
        assert sample.feature_vector[idx_sr] == pytest.approx(0.5)

    def test_reward_in_unit_interval(self):
        ls, cs = self._default_scales()
        sample = _brain_record_to_sample(_brain_record(), ls, cs, self._reward(ls, cs))
        assert 0.0 <= sample.reward <= 1.0

    def test_reward_higher_for_success(self):
        ls, cs = self._default_scales()
        rm = self._reward(ls, cs)
        s_ok = _brain_record_to_sample(_brain_record(success=True), ls, cs, rm)
        s_fail = _brain_record_to_sample(_brain_record(success=False), ls, cs, rm)
        assert s_ok.reward > s_fail.reward

    def test_agent_id_from_target(self):
        ls, cs = self._default_scales()
        sample = _brain_record_to_sample(_brain_record(), ls, cs, self._reward(ls, cs))
        assert sample.agent_id == "agent-0"

    def test_latency_norm_clamped_to_one(self):
        ls, cs = 1.0, 0.01  # very small latency scale → latency will exceed it
        state = _minimal_state()
        # avg_latency_s = 1.5 > latency_scale_s = 1.0 → clamped to 1.0
        sample = _brain_record_to_sample(
            BrainRecord(trace_id="t", workflow_name="w", state=state, target=_minimal_target()),
            ls, cs, self._reward(ls, cs),
        )
        idx = _BRAIN_FEATURE_NAMES.index("avg_latency_norm")
        assert sample.feature_vector[idx] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# BrainTrainingJobConfig schema
# ---------------------------------------------------------------------------


class TestBrainTrainingJobConfig:
    def test_extra_fields_rejected(self, tmp_path):
        with pytest.raises(Exception):
            BrainTrainingJobConfig(
                brain_records_path=tmp_path / "r.jsonl",
                output_artifact_path=tmp_path / "m.json",
                unknown="x",  # type: ignore[call-arg]
            )

    def test_batch_size_positive(self, tmp_path):
        with pytest.raises(Exception):
            BrainTrainingJobConfig(
                brain_records_path=tmp_path / "r.jsonl",
                output_artifact_path=tmp_path / "m.json",
                batch_size=0,
            )

    def test_defaults_sensible(self, tmp_path):
        cfg = BrainTrainingJobConfig(
            brain_records_path=tmp_path / "r.jsonl",
            output_artifact_path=tmp_path / "m.json",
        )
        assert cfg.batch_size == 8
        assert cfg.epochs == 1
        assert cfg.require_outcome is False


# ---------------------------------------------------------------------------
# BrainOfflineTrainer.run
# ---------------------------------------------------------------------------


class TestBrainOfflineTrainerRun:
    def _make_records_file(self, tmp_path: Path, n: int = 4) -> Path:
        path = tmp_path / "brain_records.jsonl"
        records = [_brain_record(f"t{i}") for i in range(n)]
        save_brain_records(records, path)
        return path

    def _make_config(self, tmp_path: Path, records_path: Path, **kw) -> BrainTrainingJobConfig:
        return BrainTrainingJobConfig(
            brain_records_path=records_path,
            output_artifact_path=tmp_path / "artifacts" / "brain.json",
            min_samples=1,
            **kw,
        )

    def test_returns_training_result(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert isinstance(result, BrainTrainingResult)

    def test_records_loaded_count(self, tmp_path):
        rp = self._make_records_file(tmp_path, n=5)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert result.records_loaded == 5

    def test_all_accepted_without_require_outcome(self, tmp_path):
        path = tmp_path / "records.jsonl"
        records = [_brain_record(f"t{i}", success=None) for i in range(3)]
        save_brain_records(records, path)
        cfg = self._make_config(tmp_path, path, require_outcome=False)
        result = BrainOfflineTrainer(cfg).run()
        assert result.records_accepted == 3
        assert result.records_rejected == 0

    def test_no_outcome_records_rejected_when_required(self, tmp_path):
        path = tmp_path / "records.jsonl"
        records = [_brain_record("good", success=True), _brain_record("bad", success=None)]
        save_brain_records(records, path)
        cfg = self._make_config(tmp_path, path, require_outcome=True)
        result = BrainOfflineTrainer(cfg).run()
        assert result.records_accepted == 1
        assert result.records_rejected == 1

    def test_artifact_written_to_disk(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert Path(result.artifact_path).exists()

    def test_artifact_loadable_as_neural_policy(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        policy = NeuralPolicyModel()
        policy.load_model(result.artifact_path)
        assert policy.model_source == "loaded_weights"

    def test_feature_names_in_result(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert result.feature_names == _BRAIN_FEATURE_NAMES

    def test_samples_converted_equals_accepted(self, tmp_path):
        rp = self._make_records_file(tmp_path, n=4)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert result.samples_converted == result.records_accepted

    def test_training_metrics_present(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert result.training_metrics.trained_steps >= 0
        assert result.training_metrics.average_loss >= 0.0

    def test_parent_dirs_created(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        artifact = tmp_path / "deep" / "nested" / "brain.json"
        cfg = BrainTrainingJobConfig(
            brain_records_path=rp,
            output_artifact_path=artifact,
            min_samples=1,
        )
        BrainOfflineTrainer(cfg).run()
        assert artifact.exists()

    def test_result_artifact_path_matches_config(self, tmp_path):
        rp = self._make_records_file(tmp_path)
        cfg = self._make_config(tmp_path, rp)
        result = BrainOfflineTrainer(cfg).run()
        assert result.artifact_path == str(cfg.output_artifact_path)


# ---------------------------------------------------------------------------
# Integration: LearningRecord → BrainRecord → JSONL → Train
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    def test_learning_records_to_brain_training(self, tmp_path):
        """Full pipeline: LearningRecord → BrainRecord → JSONL → BrainOfflineTrainer."""
        learning_records = [_make_learning_record(f"t{i}") for i in range(6)]
        builder = BrainRecordBuilder()
        brain_records = builder.build_batch(learning_records)
        assert len(brain_records) == 6

        jsonl_path = tmp_path / "brain_records.jsonl"
        save_brain_records(brain_records, jsonl_path)

        cfg = BrainTrainingJobConfig(
            brain_records_path=jsonl_path,
            output_artifact_path=tmp_path / "brain.json",
            min_samples=1,
            epochs=2,
        )
        result = BrainOfflineTrainer(cfg).run()

        assert result.records_loaded == 6
        assert result.records_accepted == 6
        assert Path(result.artifact_path).exists()

        policy = NeuralPolicyModel()
        policy.load_model(result.artifact_path)
        assert policy.model_source == "loaded_weights"
