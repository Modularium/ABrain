"""§6.4 / Phase 5 – `abrain learningops export` CLI surface tests."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _dry_payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "apply": False,
        "policy": {
            "require_routing_decision": True,
            "require_outcome": False,
            "require_approval_outcome": False,
            "min_quality_score": 0.0,
        },
        "totals": {"total": 10, "accepted": 7, "rejected": 3},
        "violations_by_field": {"has_routing_decision": 3},
        "output_dir": "/tmp/learning_exports",
        "written": False,
        "planned_filename": "<auto>",
    }


def _applied_payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "apply": True,
        "policy": {
            "require_routing_decision": True,
            "require_outcome": False,
            "require_approval_outcome": False,
            "min_quality_score": 0.0,
        },
        "totals": {"total": 10, "accepted": 7, "rejected": 3},
        "violations_by_field": {},
        "output_dir": "/tmp/learning_exports",
        "written": True,
        "written_path": "/tmp/learning_exports/learning_records_ts_v1.0.jsonl",
        "written_filename": "learning_records_ts_v1.0.jsonl",
        "record_count": 7,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_dry_run_summary(self):
        module = _module()
        text = module._render_learningops_export(_dry_payload())
        assert "=== LearningOps Dataset Export (DRY-RUN) ===" in text
        assert "require_routing_decision:    True" in text
        assert "Total records:         10" in text
        assert "Accepted:              7" in text
        assert "Rejected:              3" in text
        assert "- has_routing_decision: 3" in text
        assert "Directory:             /tmp/learning_exports" in text
        assert "Planned filename:      <auto>" in text
        assert "dry-run" in text

    def test_renders_applied_summary_with_written_path(self):
        module = _module()
        text = module._render_learningops_export(_applied_payload())
        assert "=== LearningOps Dataset Export (APPLIED) ===" in text
        assert "(none)" in text
        assert "Written path:          /tmp/learning_exports/learning_records_ts_v1.0.jsonl" in text
        assert "Record count written:  7" in text

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_learningops_export(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/missing.sqlite3"}
        )
        assert "Dataset export unavailable: trace_store_unavailable" in text
        assert "/tmp/missing.sqlite3" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_export_delegates_with_defaults_dry_run(self, monkeypatch, capsys):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _dry_payload()

        monkeypatch.setattr("services.core.export_learning_dataset", fake)

        exit_code = module.main(["learningops", "export"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "require_routing_decision": True,
            "require_outcome": False,
            "require_approval_outcome": False,
            "min_quality_score": 0.0,
            "limit": 1000,
            "output_dir": None,
            "filename": None,
            "apply": False,
        }
        assert "DRY-RUN" in output

    def test_export_forwards_apply_output_dir_and_filename(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.export_learning_dataset",
            lambda **kw: captured.update(kw) or _applied_payload(),
        )

        module.main(
            [
                "learningops",
                "export",
                "--apply",
                "--output-dir",
                "/tmp/out",
                "--filename",
                "pinned.jsonl",
                "--no-require-routing-decision",
                "--require-outcome",
                "--min-quality-score",
                "0.5",
                "--limit",
                "250",
                "--json",
            ]
        )
        assert captured["apply"] is True
        assert captured["output_dir"] == "/tmp/out"
        assert captured["filename"] == "pinned.jsonl"
        assert captured["require_routing_decision"] is False
        assert captured["require_outcome"] is True
        assert captured["min_quality_score"] == 0.5
        assert captured["limit"] == 250

    def test_export_clamps_non_positive_limit(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.export_learning_dataset",
            lambda **kw: captured.update(kw) or _dry_payload(),
        )

        module.main(["learningops", "export", "--limit", "-5", "--json"])
        assert captured["limit"] == 1

    def test_export_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.export_learning_dataset",
            lambda **_: _applied_payload(),
        )

        exit_code = module.main(["learningops", "export", "--apply", "--json"])
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["written"] is True
        assert parsed["record_count"] == 7


# ---------------------------------------------------------------------------
# Service integration (real TraceStore + DatasetExporter)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_surfaces_trace_store_unavailable(self, monkeypatch):
        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": None, "path": "/tmp/abrain-missing.sqlite3"},
        )
        report = core_module.export_learning_dataset()
        assert report["error"] == "trace_store_unavailable"
        assert report["trace_store_path"] == "/tmp/abrain-missing.sqlite3"

    def test_service_dry_run_writes_no_file(self, monkeypatch, tmp_path: Path):
        from core.approval import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        trace_store.create_trace(
            workflow_name="wf",
            task_id="task-a",
            trace_id="t-0000",
            metadata={"task_type": "demo"},
        )
        trace_store.finish_trace("t-0000", status="ok")

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": trace_store, "path": "unused"},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": approval_store, "policy": None},
        )

        output_dir = tmp_path / "exports"
        report = core_module.export_learning_dataset(
            output_dir=str(output_dir),
            require_routing_decision=False,
        )
        assert report["apply"] is False
        assert report["written"] is False
        assert report["output_dir"] == str(output_dir)
        assert report["totals"]["total"] == 1
        assert not output_dir.exists()

    def test_service_apply_writes_jsonl_with_manifest(
        self, monkeypatch, tmp_path: Path
    ):
        from core.approval import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        for idx in range(2):
            trace_store.create_trace(
                workflow_name="wf",
                task_id=f"task-{idx}",
                trace_id=f"t-{idx:04d}",
                metadata={"task_type": "demo"},
            )
            trace_store.finish_trace(f"t-{idx:04d}", status="ok")

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": trace_store, "path": "unused"},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": approval_store, "policy": None},
        )

        output_dir = tmp_path / "exports"
        report = core_module.export_learning_dataset(
            require_routing_decision=False,
            apply=True,
            output_dir=str(output_dir),
            filename="pinned.jsonl",
        )
        assert report["written"] is True
        assert report["written_filename"] == "pinned.jsonl"
        target = output_dir / "pinned.jsonl"
        assert target.exists()
        lines = target.read_text().splitlines()
        manifest = json.loads(lines[0])
        assert manifest["__manifest__"] is True
        assert manifest["record_count"] == 2
        assert report["record_count"] == 2

    def test_service_respects_env_var_default_output_dir(
        self, monkeypatch, tmp_path: Path
    ):
        from core.approval import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": trace_store, "path": "unused"},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": approval_store, "policy": None},
        )

        env_dir = tmp_path / "from-env"
        monkeypatch.setenv("ABRAIN_LEARNING_EXPORTS_DIR", str(env_dir))

        report = core_module.export_learning_dataset()
        assert report["output_dir"] == str(env_dir)
        # Dry-run must not create the directory.
        assert not env_dir.exists()

    def test_service_filter_policy_drops_rejected_before_export(
        self, monkeypatch, tmp_path: Path
    ):
        from core.approval import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        for idx in range(3):
            trace_store.create_trace(
                workflow_name="wf",
                task_id=f"task-{idx}",
                trace_id=f"t-{idx:04d}",
                metadata={"task_type": "demo"},
            )
            trace_store.finish_trace(f"t-{idx:04d}", status="ok")

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": trace_store, "path": "unused"},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": approval_store, "policy": None},
        )

        output_dir = tmp_path / "exports"
        # require_routing_decision=True — no trace has one, so all rejected.
        report = core_module.export_learning_dataset(
            require_routing_decision=True,
            apply=True,
            output_dir=str(output_dir),
            filename="filtered.jsonl",
        )
        assert report["totals"] == {"total": 3, "accepted": 0, "rejected": 3}
        assert report["record_count"] == 0
        assert report["violations_by_field"] == {"has_routing_decision": 3}

        target = output_dir / "filtered.jsonl"
        assert target.exists()
        lines = target.read_text().splitlines()
        # manifest only — no records written.
        assert len(lines) == 1
        manifest = json.loads(lines[0])
        assert manifest["record_count"] == 0
