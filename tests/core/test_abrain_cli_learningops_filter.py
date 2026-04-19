"""§6.4 / Phase 5 – `abrain learningops filter` CLI surface tests."""

from __future__ import annotations

import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "policy": {
            "require_routing_decision": True,
            "require_outcome": False,
            "require_approval_outcome": False,
            "min_quality_score": 0.5,
        },
        "totals": {
            "total": 100,
            "accepted": 60,
            "rejected": 40,
            "acceptance_rate": 0.6,
        },
        "violations_by_field": {
            "has_routing_decision": 25,
            "quality_score": 15,
        },
        "rejected_sample": [
            {
                "trace_id": "t-0001",
                "workflow_name": "wf",
                "task_type": "demo",
                "quality_score": 0.33,
                "violations": [
                    {"field": "has_routing_decision", "reason": "no routing decision"},
                ],
            }
        ],
        "rejected_sample_truncated": True,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_totals_violations_and_sample(self):
        module = _module()
        text = module._render_learningops_filter(_payload())
        assert "=== LearningOps Quality Filter Preview ===" in text
        assert "require_routing_decision: True" in text
        assert "min_quality_score:        0.5000" in text
        assert "Total records:   100" in text
        assert "Accepted:        60" in text
        assert "Rejected:        40" in text
        assert "Acceptance rate: 0.6000" in text
        assert "- has_routing_decision: 25" in text
        assert "- quality_score: 15" in text
        assert "trace=t-0001" in text
        assert "wf=wf" in text
        assert "task=demo" in text
        assert "q=0.33" in text
        assert "* has_routing_decision: no routing decision" in text
        assert "... (39 more rejected, truncated)" in text

    def test_renders_empty_violations_and_sample(self):
        module = _module()
        payload = _payload()
        payload["violations_by_field"] = {}
        payload["rejected_sample"] = []
        payload["rejected_sample_truncated"] = False
        payload["totals"]["rejected"] = 0
        text = module._render_learningops_filter(payload)
        assert "Violations by field (0):" in text
        assert "Rejected sample (0):" in text
        assert text.count("(none)") == 2

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_learningops_filter(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/x"}
        )
        assert "Quality filter preview unavailable: trace_store_unavailable" in text
        assert "/tmp/x" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_filter_delegates_with_defaults(self, monkeypatch, capsys):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_dataset_quality_report", fake)

        exit_code = module.main(["learningops", "filter"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "require_routing_decision": True,
            "require_outcome": False,
            "require_approval_outcome": False,
            "min_quality_score": 0.0,
            "limit": 1000,
            "rejected_sample_size": 20,
        }
        assert "LearningOps Quality Filter Preview" in output

    def test_filter_disables_routing_requirement_and_enables_outcomes(
        self, monkeypatch
    ):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_dataset_quality_report",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "learningops",
                "filter",
                "--no-require-routing-decision",
                "--require-outcome",
                "--require-approval-outcome",
                "--min-quality-score",
                "0.75",
                "--json",
            ]
        )
        assert captured["require_routing_decision"] is False
        assert captured["require_outcome"] is True
        assert captured["require_approval_outcome"] is True
        assert captured["min_quality_score"] == 0.75

    def test_filter_clamps_negative_limit_and_sample_size(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_dataset_quality_report",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "learningops",
                "filter",
                "--limit",
                "-8",
                "--sample-size",
                "-3",
                "--json",
            ]
        )
        assert captured["limit"] == 1
        assert captured["rejected_sample_size"] == 0

    def test_filter_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_dataset_quality_report",
            lambda **_: _payload(),
        )

        exit_code = module.main(["learningops", "filter", "--json"])
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["totals"]["accepted"] == 60
        assert parsed["rejected_sample"][0]["trace_id"] == "t-0001"


# ---------------------------------------------------------------------------
# Service integration
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_surfaces_trace_store_unavailable(self, monkeypatch):
        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": None, "path": "/tmp/abrain-missing.sqlite3"},
        )
        report = core_module.get_dataset_quality_report()
        assert report["error"] == "trace_store_unavailable"
        assert report["trace_store_path"] == "/tmp/abrain-missing.sqlite3"

    def test_service_clamps_min_quality_score_into_unit_interval(self, monkeypatch):
        import services.core as core_module

        class _EmptyStore:
            def list_recent_traces(self, limit):
                return []

            def get_trace(self, trace_id):  # pragma: no cover - never reached
                return None

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": _EmptyStore(), "path": "unused"},
        )
        monkeypatch.setattr(
            core_module,
            "_get_approval_state",
            lambda: {"store": None, "policy": None},
        )

        report = core_module.get_dataset_quality_report(min_quality_score=5.0)
        assert report["policy"]["min_quality_score"] == 1.0
        assert report["totals"] == {
            "total": 0,
            "accepted": 0,
            "rejected": 0,
            "acceptance_rate": 0.0,
        }

    def test_service_reports_violations_over_real_stores(
        self, monkeypatch, tmp_path
    ):
        from core.approval import ApprovalStore
        from core.audit.trace_store import TraceStore

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")

        # Create three traces: none has an explainability record, so all
        # LearningRecords will have has_routing_decision=False.
        for idx in range(3):
            trace_store.create_trace(
                workflow_name="wf-demo",
                task_id=f"task-{idx}",
                trace_id=f"t-{idx:04d}",
                metadata={"task_type": "demo"},
            )
            trace_store.finish_trace(f"t-{idx:04d}", status="ok")

        import services.core as core_module

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

        report = core_module.get_dataset_quality_report(
            require_routing_decision=True
        )
        assert report["totals"]["total"] == 3
        assert report["totals"]["accepted"] == 0
        assert report["totals"]["rejected"] == 3
        assert report["violations_by_field"]["has_routing_decision"] == 3
        assert {item["trace_id"] for item in report["rejected_sample"]} == {
            "t-0000",
            "t-0001",
            "t-0002",
        }
        assert report["rejected_sample_truncated"] is False
