"""§6.4 / Phase 5 – `abrain learningops split` CLI surface tests."""

from __future__ import annotations

import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _payload() -> dict:
    return {
        "manifest": {
            "config": {
                "train_ratio": 0.7,
                "val_ratio": 0.15,
                "test_ratio": 0.15,
                "seed": 42,
                "group_by": "trace_id",
            },
            "generated_at": "2026-04-19T00:00:00+00:00",
            "total_records": 100,
            "total_groups": 100,
            "train_size": 70,
            "val_size": 15,
            "test_size": 15,
            "ungrouped_records": 0,
            "dataset_fingerprint": "abc123",
        },
        "sizes": {"train": 70, "val": 15, "test": 15},
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_manifest_and_sizes(self):
        module = _module()
        text = module._render_learningops_split(_payload())
        assert "=== LearningOps Dataset Split ===" in text
        assert "Group by:            trace_id" in text
        assert "Seed:                42" in text
        assert "train=0.7000" in text
        assert "val=0.1500" in text
        assert "Total records:     100" in text
        assert "Fingerprint:       abc123" in text
        assert "train:             70" in text
        assert "val:               15" in text
        assert "test:              15" in text

    def test_renders_sample_trace_ids_when_present(self):
        module = _module()
        payload = _payload()
        payload["sample_trace_ids"] = {
            "train": ["t-0000", "t-0001"],
            "val": [],
            "test": ["t-0099"],
        }
        text = module._render_learningops_split(payload)
        assert "Sample trace_ids (first 20 per bucket):" in text
        assert "train (2):" in text
        assert "- t-0000" in text
        assert "val (0):" in text
        assert "(none)" in text
        assert "test (1):" in text
        assert "- t-0099" in text

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_learningops_split(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/x"}
        )
        assert "Dataset split unavailable: trace_store_unavailable" in text
        assert "/tmp/x" in text

    def test_renders_split_invalid_error(self):
        module = _module()
        text = module._render_learningops_split(
            {"error": "split_invalid", "detail": "ValueError: duplicate"}
        )
        assert "Dataset split unavailable: split_invalid" in text
        assert "ValueError: duplicate" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_split_delegates_to_services_core_with_defaults(self, monkeypatch, capsys):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_dataset_split", fake)

        exit_code = module.main(
            [
                "learningops",
                "split",
                "--train",
                "0.7",
                "--val",
                "0.15",
                "--test",
                "0.15",
                "--seed",
                "42",
            ]
        )
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "test_ratio": 0.15,
            "seed": 42,
            "group_by": "trace_id",
            "limit": 1000,
            "include_sample_trace_ids": False,
        }
        assert "LearningOps Dataset Split" in output

    def test_split_forwards_group_by_limit_and_show_trace_ids(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_dataset_split",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "learningops",
                "split",
                "--train",
                "0.8",
                "--val",
                "0.1",
                "--test",
                "0.1",
                "--seed",
                "7",
                "--group-by",
                "workflow_name",
                "--limit",
                "250",
                "--show-trace-ids",
                "--json",
            ]
        )
        assert captured["group_by"] == "workflow_name"
        assert captured["limit"] == 250
        assert captured["include_sample_trace_ids"] is True
        assert captured["seed"] == 7

    def test_split_clamps_negative_seed_and_limit(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_dataset_split",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "learningops",
                "split",
                "--train",
                "0.7",
                "--val",
                "0.15",
                "--test",
                "0.15",
                "--seed",
                "-5",
                "--limit",
                "-9",
                "--json",
            ]
        )
        assert captured["seed"] == 0
        assert captured["limit"] == 1

    def test_split_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_dataset_split",
            lambda **_: _payload(),
        )

        exit_code = module.main(
            [
                "learningops",
                "split",
                "--train",
                "0.7",
                "--val",
                "0.15",
                "--test",
                "0.15",
                "--seed",
                "42",
                "--json",
            ]
        )
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["sizes"]["train"] == 70
        assert parsed["manifest"]["dataset_fingerprint"] == "abc123"


# ---------------------------------------------------------------------------
# Service integration (no monkeypatch of the primitive — real stores)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_surfaces_trace_store_unavailable(self, monkeypatch):
        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": None, "path": "/tmp/abrain-missing.sqlite3"},
        )
        report = core_module.get_dataset_split(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=1,
        )
        assert report["error"] == "trace_store_unavailable"
        assert report["trace_store_path"] == "/tmp/abrain-missing.sqlite3"

    def test_service_surfaces_invalid_config_without_touching_stores(
        self, monkeypatch
    ):
        import services.core as core_module

        class _SentinelStore:
            def list_recent_traces(self, *args, **kwargs):  # pragma: no cover
                raise AssertionError("store must not be touched on config error")

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": _SentinelStore(), "path": "unused"},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": None, "policy": None},
        )
        # ratios that do not sum to 1.0
        report = core_module.get_dataset_split(
            train_ratio=0.5,
            val_ratio=0.2,
            test_ratio=0.2,
            seed=0,
        )
        assert report["error"] == "split_config_invalid"

    def test_service_splits_real_trace_records_deterministically(
        self, monkeypatch, tmp_path
    ):
        from core.approval import ApprovalStore
        from core.audit.trace_store import TraceStore

        trace_path = tmp_path / "traces.sqlite3"
        approval_path = tmp_path / "approvals.json"
        trace_store = TraceStore(str(trace_path))
        approval_store = ApprovalStore(path=approval_path)

        for idx in range(20):
            trace_store.create_trace(
                workflow_name="wf-demo",
                task_id=f"task-{idx}",
                trace_id=f"t-{idx:04d}",
                metadata={"task_type": "demo", "success": True},
            )
            trace_store.finish_trace(f"t-{idx:04d}", status="ok")

        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": trace_store, "path": str(trace_path)},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": approval_store, "policy": None},
        )

        report_a = core_module.get_dataset_split(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=123,
        )
        report_b = core_module.get_dataset_split(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=123,
        )
        assert "error" not in report_a
        # Deterministic across runs.
        assert (
            report_a["manifest"]["dataset_fingerprint"]
            == report_b["manifest"]["dataset_fingerprint"]
        )
        assert report_a["sizes"] == report_b["sizes"]
        total = sum(report_a["sizes"].values())
        assert total == 20
        assert report_a["manifest"]["total_records"] == 20
