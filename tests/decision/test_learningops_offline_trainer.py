"""Phase 5 – LearningOps L3: OfflineTrainer + TrainingJobConfig tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.decision.learning.exporter import DatasetExporter
from core.decision.learning.offline_trainer import (
    OfflineTrainer,
    OfflineTrainingResult,
    TrainingJobConfig,
    _record_to_sample,
    _OFFLINE_FEATURE_NAMES,
)
from core.decision.learning.record import LearningRecord
from core.decision.learning.reward_model import RewardModel

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rec(**kwargs) -> LearningRecord:
    defaults = dict(
        trace_id="t1",
        workflow_name="w1",
        selected_agent_id="agent-A",
        selected_score=0.8,
        routing_confidence=0.9,
        score_gap=0.1,
        candidate_agent_ids=["agent-A", "agent-B"],
        success=True,
        cost_usd=0.002,
        latency_ms=800.0,
        has_routing_decision=True,
        has_outcome=True,
        has_approval_outcome=False,
    )
    defaults.update(kwargs)
    return LearningRecord(**defaults)


def _make_dataset_file(tmp_path: Path, records: list[LearningRecord]) -> Path:
    exporter = DatasetExporter(tmp_path / "exports")
    return exporter.export(records, filename="test_dataset.jsonl")


def _make_config(tmp_path: Path, dataset_path: Path, **kwargs) -> TrainingJobConfig:
    return TrainingJobConfig(
        dataset_path=dataset_path,
        output_artifact_path=tmp_path / "artifacts" / "model.json",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# TrainingJobConfig schema
# ---------------------------------------------------------------------------


class TestTrainingJobConfig:
    def test_required_fields(self, tmp_path):
        cfg = TrainingJobConfig(
            dataset_path=tmp_path / "data.jsonl",
            output_artifact_path=tmp_path / "model.json",
        )
        assert cfg.batch_size == 8
        assert cfg.learning_rate == pytest.approx(0.05)
        assert cfg.epochs == 1
        assert cfg.min_samples == 2
        assert cfg.require_routing_decision is True
        assert cfg.require_outcome is False

    def test_extra_fields_rejected(self, tmp_path):
        with pytest.raises(Exception):
            TrainingJobConfig(  # type: ignore[call-arg]
                dataset_path=tmp_path / "d.jsonl",
                output_artifact_path=tmp_path / "m.json",
                unknown_param=True,
            )

    def test_batch_size_must_be_positive(self, tmp_path):
        with pytest.raises(Exception):
            TrainingJobConfig(
                dataset_path=tmp_path / "d.jsonl",
                output_artifact_path=tmp_path / "m.json",
                batch_size=0,
            )

    def test_learning_rate_bounds(self, tmp_path):
        with pytest.raises(Exception):
            TrainingJobConfig(
                dataset_path=tmp_path / "d.jsonl",
                output_artifact_path=tmp_path / "m.json",
                learning_rate=0.0,
            )

    def test_custom_hyperparams_accepted(self, tmp_path):
        cfg = TrainingJobConfig(
            dataset_path=tmp_path / "d.jsonl",
            output_artifact_path=tmp_path / "m.json",
            batch_size=32,
            learning_rate=0.01,
            epochs=5,
            min_samples=10,
        )
        assert cfg.batch_size == 32
        assert cfg.epochs == 5


# ---------------------------------------------------------------------------
# _record_to_sample conversion
# ---------------------------------------------------------------------------


class TestRecordToSample:
    def test_feature_names_match_schema(self):
        sample = _record_to_sample(_rec(), RewardModel())
        assert sample.feature_names == _OFFLINE_FEATURE_NAMES

    def test_feature_vector_length_matches_names(self):
        sample = _record_to_sample(_rec(), RewardModel())
        assert len(sample.feature_vector) == len(_OFFLINE_FEATURE_NAMES)

    def test_success_true_maps_to_1(self):
        sample = _record_to_sample(_rec(success=True), RewardModel())
        assert sample.success == pytest.approx(1.0)
        assert sample.feature_vector[0] == pytest.approx(1.0)

    def test_success_false_maps_to_0(self):
        sample = _record_to_sample(_rec(success=False), RewardModel())
        assert sample.success == pytest.approx(0.0)
        assert sample.feature_vector[0] == pytest.approx(0.0)

    def test_success_none_maps_to_neutral(self):
        sample = _record_to_sample(_rec(success=None, has_outcome=False), RewardModel())
        assert sample.success == pytest.approx(0.5)
        assert sample.feature_vector[0] == pytest.approx(0.5)

    def test_cost_usd_normalised(self):
        sample = _record_to_sample(_rec(cost_usd=0.01), RewardModel())
        # cost_norm = 0.01 / 0.01 = 1.0 (clamped)
        assert sample.feature_vector[1] == pytest.approx(1.0)

    def test_latency_normalised(self):
        sample = _record_to_sample(_rec(latency_ms=5000.0), RewardModel())
        # latency_s = 5.0; latency_norm = 5.0 / 10.0 = 0.5
        assert sample.feature_vector[2] == pytest.approx(0.5)

    def test_missing_cost_defaults_to_zero(self):
        sample = _record_to_sample(_rec(cost_usd=None), RewardModel())
        assert sample.cost == pytest.approx(0.0)
        assert sample.feature_vector[1] == pytest.approx(0.0)

    def test_missing_latency_defaults_to_one_second(self):
        sample = _record_to_sample(_rec(latency_ms=None), RewardModel())
        assert sample.latency == pytest.approx(1.0)

    def test_agent_id_propagated(self):
        sample = _record_to_sample(_rec(selected_agent_id="agent-X"), RewardModel())
        assert sample.agent_id == "agent-X"

    def test_missing_agent_id_defaults_to_unknown(self):
        sample = _record_to_sample(_rec(selected_agent_id=None), RewardModel())
        assert sample.agent_id == "unknown"

    def test_routing_confidence_in_feature_vector(self):
        sample = _record_to_sample(_rec(routing_confidence=0.75), RewardModel())
        assert sample.feature_vector[3] == pytest.approx(0.75)

    def test_score_gap_in_feature_vector(self):
        sample = _record_to_sample(_rec(score_gap=0.2), RewardModel())
        assert sample.feature_vector[4] == pytest.approx(0.2)

    def test_capability_match_from_selected_score(self):
        sample = _record_to_sample(_rec(selected_score=0.65), RewardModel())
        assert sample.capability_match == pytest.approx(0.65)
        assert sample.feature_vector[5] == pytest.approx(0.65)

    def test_reward_is_in_unit_interval(self):
        for success in [True, False, None]:
            sample = _record_to_sample(_rec(success=success, has_outcome=success is not None), RewardModel())
            assert 0.0 <= sample.reward <= 1.0

    def test_task_embedding_is_empty(self):
        sample = _record_to_sample(_rec(), RewardModel())
        assert sample.task_embedding == []


# ---------------------------------------------------------------------------
# OfflineTrainer – full run
# ---------------------------------------------------------------------------


class TestOfflineTrainer:
    def test_run_produces_result(self, tmp_path):
        dataset_path = _make_dataset_file(tmp_path, [_rec(), _rec(trace_id="t2")])
        cfg = _make_config(tmp_path, dataset_path)
        result = OfflineTrainer(cfg).run()
        assert isinstance(result, OfflineTrainingResult)

    def test_records_loaded_count(self, tmp_path):
        records = [_rec(trace_id=f"t{i}") for i in range(5)]
        dataset_path = _make_dataset_file(tmp_path, records)
        cfg = _make_config(tmp_path, dataset_path)
        result = OfflineTrainer(cfg).run()
        assert result.records_loaded == 5
        assert result.records_accepted == 5
        assert result.records_rejected == 0

    def test_rejected_records_excluded(self, tmp_path):
        good = _rec(has_routing_decision=True)
        bad = _rec(trace_id="t-bad", has_routing_decision=False)
        dataset_path = _make_dataset_file(tmp_path, [good, bad])
        cfg = _make_config(tmp_path, dataset_path, require_routing_decision=True)
        result = OfflineTrainer(cfg).run()
        assert result.records_accepted == 1
        assert result.records_rejected == 1

    def test_artifact_is_written(self, tmp_path):
        dataset_path = _make_dataset_file(tmp_path, [_rec(), _rec(trace_id="t2")])
        cfg = _make_config(tmp_path, dataset_path)
        result = OfflineTrainer(cfg).run()
        assert Path(result.artifact_path).exists()

    def test_artifact_path_parent_created(self, tmp_path):
        dataset_path = _make_dataset_file(tmp_path, [_rec()])
        artifact_path = tmp_path / "deep" / "nested" / "model.json"
        cfg = TrainingJobConfig(
            dataset_path=dataset_path,
            output_artifact_path=artifact_path,
            min_samples=1,
        )
        result = OfflineTrainer(cfg).run()
        assert Path(result.artifact_path).exists()

    def test_empty_dataset_trains_zero_steps(self, tmp_path):
        dataset_path = _make_dataset_file(tmp_path, [])
        cfg = _make_config(tmp_path, dataset_path, min_samples=1)
        result = OfflineTrainer(cfg).run()
        assert result.records_loaded == 0
        assert result.samples_converted == 0
        assert result.training_metrics.trained_steps == 0

    def test_samples_converted_equals_accepted(self, tmp_path):
        records = [_rec(trace_id=f"t{i}") for i in range(4)]
        dataset_path = _make_dataset_file(tmp_path, records)
        cfg = _make_config(tmp_path, dataset_path)
        result = OfflineTrainer(cfg).run()
        assert result.samples_converted == result.records_accepted

    def test_manifest_metadata_preserved(self, tmp_path):
        dataset_path = _make_dataset_file(tmp_path, [_rec()])
        cfg = _make_config(tmp_path, dataset_path)
        result = OfflineTrainer(cfg).run()
        assert result.manifest_schema_version == "1.0"
        assert "T" in result.exported_at

    def test_training_metrics_are_valid(self, tmp_path):
        records = [_rec(trace_id=f"t{i}") for i in range(4)]
        dataset_path = _make_dataset_file(tmp_path, records)
        cfg = _make_config(tmp_path, dataset_path, min_samples=2)
        result = OfflineTrainer(cfg).run()
        metrics = result.training_metrics
        assert metrics.batch_size >= 0
        assert metrics.average_loss >= 0.0
        assert metrics.trained_steps >= 0

    def test_training_runs_when_min_samples_met(self, tmp_path):
        records = [_rec(trace_id=f"t{i}") for i in range(4)]
        dataset_path = _make_dataset_file(tmp_path, records)
        cfg = _make_config(tmp_path, dataset_path, min_samples=2, epochs=2)
        result = OfflineTrainer(cfg).run()
        assert result.training_metrics.trained_steps == 2  # epochs

    def test_artifact_path_in_result_matches_config(self, tmp_path):
        dataset_path = _make_dataset_file(tmp_path, [_rec()])
        cfg = _make_config(tmp_path, dataset_path)
        result = OfflineTrainer(cfg).run()
        assert result.artifact_path == str(cfg.output_artifact_path)
