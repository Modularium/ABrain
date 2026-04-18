"""Phase 5 – LearningOps L4: ModelRegistry tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.decision.learning.exporter import DatasetExporter
from core.decision.learning.model_registry import (
    ModelRegistry,
    ModelVersionEntry,
    _config_hash,
    _short_id,
)
from core.decision.learning.offline_trainer import OfflineTrainer, TrainingJobConfig
from core.decision.learning.record import LearningRecord

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rec(**kw) -> LearningRecord:
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


def _run_training(tmp_path: Path, n: int = 3) -> tuple[TrainingJobConfig, object]:
    records = [_rec(trace_id=f"t{i}") for i in range(n)]
    exporter = DatasetExporter(tmp_path / "exports")
    dataset_path = exporter.export(records, filename="ds.jsonl")
    config = TrainingJobConfig(
        dataset_path=dataset_path,
        output_artifact_path=tmp_path / "artifacts" / "model.json",
        min_samples=1,
    )
    result = OfflineTrainer(config).run()
    return config, result


# ---------------------------------------------------------------------------
# _short_id and _config_hash helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_short_id_is_8_hex_chars(self):
        uid = _short_id()
        assert len(uid) == 8
        int(uid, 16)  # raises if not hex

    def test_short_id_unique(self):
        ids = {_short_id() for _ in range(100)}
        assert len(ids) == 100

    def test_config_hash_is_sha256_hex(self):
        config = TrainingJobConfig(
            dataset_path=Path("/tmp/d.jsonl"),
            output_artifact_path=Path("/tmp/m.json"),
        )
        h = _config_hash(config)
        assert len(h) == 64
        int(h, 16)

    def test_same_hyperparams_same_hash(self, tmp_path):
        c1 = TrainingJobConfig(
            dataset_path=tmp_path / "a.jsonl",
            output_artifact_path=tmp_path / "m1.json",
            batch_size=16,
            epochs=3,
        )
        c2 = TrainingJobConfig(
            dataset_path=tmp_path / "b.jsonl",  # different path
            output_artifact_path=tmp_path / "m2.json",
            batch_size=16,
            epochs=3,
        )
        assert _config_hash(c1) == _config_hash(c2)

    def test_different_hyperparams_different_hash(self, tmp_path):
        c1 = TrainingJobConfig(
            dataset_path=tmp_path / "d.jsonl",
            output_artifact_path=tmp_path / "m.json",
            batch_size=8,
        )
        c2 = TrainingJobConfig(
            dataset_path=tmp_path / "d.jsonl",
            output_artifact_path=tmp_path / "m.json",
            batch_size=32,
        )
        assert _config_hash(c1) != _config_hash(c2)


# ---------------------------------------------------------------------------
# ModelVersionEntry schema
# ---------------------------------------------------------------------------


class TestModelVersionEntry:
    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            ModelVersionEntry(  # type: ignore[call-arg]
                version_id="abc",
                artifact_path="/m.json",
                dataset_path="/d.jsonl",
                schema_version="1.0",
                training_config_hash="aa" * 32,
                records_accepted=1,
                records_rejected=0,
                samples_converted=1,
                training_metrics={"batch_size": 1, "average_loss": 0.0, "trained_steps": 1},
                registered_at="2026-01-01T00:00:00+00:00",
                unknown_field="x",
            )

    def test_is_active_defaults_to_false(self):
        from core.decision.learning.trainer import TrainingMetrics

        e = ModelVersionEntry(
            version_id="abc12345",
            artifact_path="/m.json",
            dataset_path="/d.jsonl",
            schema_version="1.0",
            training_config_hash="a" * 64,
            records_accepted=2,
            records_rejected=0,
            samples_converted=2,
            training_metrics=TrainingMetrics(batch_size=2, average_loss=0.1, trained_steps=1),
            registered_at="2026-01-01T00:00:00+00:00",
        )
        assert e.is_active is False


# ---------------------------------------------------------------------------
# ModelRegistry – register
# ---------------------------------------------------------------------------


class TestModelRegistryRegister:
    def test_register_adds_entry(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        registry.register(result, config)
        assert len(registry) == 1

    def test_register_returns_entry(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        entry = registry.register(result, config)
        assert isinstance(entry, ModelVersionEntry)
        assert entry.artifact_path == result.artifact_path

    def test_register_activate_true_makes_entry_active(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        entry = registry.register(result, config, activate=True)
        assert entry.is_active is True
        assert registry.get_active() is not None

    def test_register_activate_false_leaves_no_active(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        registry.register(result, config, activate=False)
        assert registry.get_active() is None

    def test_register_second_entry_deactivates_first(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config1, result1 = _run_training(tmp_path / "run1", n=2)
        config2, result2 = _run_training(tmp_path / "run2", n=3)
        e1 = registry.register(result1, config1)
        e2 = registry.register(result2, config2)
        assert registry.get_active().version_id == e2.version_id
        assert not registry.get_version(e1.version_id).is_active

    def test_register_stores_notes(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        entry = registry.register(result, config, notes="experiment-42")
        assert entry.notes == "experiment-42"

    def test_register_persists_to_disk(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        registry = ModelRegistry(reg_path)
        config, result = _run_training(tmp_path)
        registry.register(result, config)
        assert reg_path.exists()

    def test_register_stores_config_hash(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        entry = registry.register(result, config)
        assert entry.training_config_hash == _config_hash(config)

    def test_register_stores_schema_version(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        entry = registry.register(result, config)
        assert entry.schema_version == "1.0"

    def test_register_stores_record_counts(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path, n=3)
        entry = registry.register(result, config)
        assert entry.records_accepted == result.records_accepted
        assert entry.records_rejected == result.records_rejected


# ---------------------------------------------------------------------------
# ModelRegistry – activate / rollback
# ---------------------------------------------------------------------------


class TestModelRegistryActivate:
    def test_activate_unknown_id_raises(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        with pytest.raises(KeyError):
            registry.activate("nonexistent")

    def test_activate_switches_active_flag(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config1, result1 = _run_training(tmp_path / "r1", n=2)
        config2, result2 = _run_training(tmp_path / "r2", n=2)
        e1 = registry.register(result1, config1)
        e2 = registry.register(result2, config2)
        # e2 is active; roll back to e1
        registry.activate(e1.version_id)
        assert registry.get_active().version_id == e1.version_id
        assert not registry.get_version(e2.version_id).is_active

    def test_activate_persists_change(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        registry = ModelRegistry(reg_path)
        config1, result1 = _run_training(tmp_path / "r1", n=2)
        config2, result2 = _run_training(tmp_path / "r2", n=2)
        e1 = registry.register(result1, config1)
        registry.register(result2, config2)
        registry.activate(e1.version_id)
        # Reload from disk
        reloaded = ModelRegistry(reg_path)
        assert reloaded.get_active().version_id == e1.version_id

    def test_activate_returns_entry(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path)
        e = registry.register(result, config)
        returned = registry.activate(e.version_id)
        assert returned.version_id == e.version_id
        assert returned.is_active is True


# ---------------------------------------------------------------------------
# ModelRegistry – read API
# ---------------------------------------------------------------------------


class TestModelRegistryRead:
    def test_get_active_returns_none_on_empty(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        assert registry.get_active() is None

    def test_get_active_model_returns_none_on_empty(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        assert registry.get_active_model() is None

    def test_get_active_model_loads_trained_model(self, tmp_path):
        from core.decision.neural_policy import NeuralPolicyModel

        registry = ModelRegistry(tmp_path / "registry.json")
        config, result = _run_training(tmp_path, n=3)
        registry.register(result, config)
        model = registry.get_active_model()
        assert isinstance(model, NeuralPolicyModel)

    def test_get_version_returns_none_for_unknown(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        assert registry.get_version("bad") is None

    def test_list_versions_newest_first(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        config1, result1 = _run_training(tmp_path / "r1", n=2)
        config2, result2 = _run_training(tmp_path / "r2", n=2)
        e1 = registry.register(result1, config1)
        e2 = registry.register(result2, config2)
        versions = registry.list_versions()
        assert versions[0].version_id == e2.version_id
        assert versions[1].version_id == e1.version_id

    def test_len_matches_entry_count(self, tmp_path):
        registry = ModelRegistry(tmp_path / "registry.json")
        assert len(registry) == 0
        config, result = _run_training(tmp_path)
        registry.register(result, config)
        assert len(registry) == 1


# ---------------------------------------------------------------------------
# ModelRegistry – persistence round-trip
# ---------------------------------------------------------------------------


class TestModelRegistryPersistence:
    def test_reload_from_disk_preserves_entries(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        registry = ModelRegistry(reg_path)
        config, result = _run_training(tmp_path)
        entry = registry.register(result, config, notes="my-note")

        reloaded = ModelRegistry(reg_path)
        assert len(reloaded) == 1
        r = reloaded.get_version(entry.version_id)
        assert r is not None
        assert r.notes == "my-note"
        assert r.is_active is True

    def test_registry_file_is_valid_json(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        registry = ModelRegistry(reg_path)
        config, result = _run_training(tmp_path)
        registry.register(result, config)
        data = json.loads(reg_path.read_text())
        assert isinstance(data, list)
        assert data[0]["version_id"] is not None

    def test_registry_creates_parent_dirs(self, tmp_path):
        reg_path = tmp_path / "deep" / "nested" / "registry.json"
        registry = ModelRegistry(reg_path)
        config, result = _run_training(tmp_path)
        registry.register(result, config)
        assert reg_path.exists()

    def test_multiple_entries_all_persisted(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        registry = ModelRegistry(reg_path)
        for i in range(3):
            config, result = _run_training(tmp_path / f"run{i}", n=2)
            registry.register(result, config)
        reloaded = ModelRegistry(reg_path)
        assert len(reloaded) == 3
        # Only last one is active
        active_count = sum(1 for e in reloaded.list_versions() if e.is_active)
        assert active_count == 1
