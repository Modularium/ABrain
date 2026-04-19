"""Phase 6 – `abrain brain status` CLI surface tests."""

from __future__ import annotations

import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _report_payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "trace_limit": 250,
        "workflow_filter": "planner",
        "version_filter": None,
        "baseline": {
            "traces_scanned": 42,
            "samples": 30,
            "overall": {
                "sample_count": 30,
                "agreement_rate": 0.83,
                "mean_score_divergence": 0.12,
                "median_score_divergence": 0.09,
                "mean_top_k_overlap": 0.77,
                "coverage_workflows": 3,
                "coverage_versions": 1,
            },
            "per_version": {},
            "per_workflow": {},
            "recommendation": "promote",
            "recommendation_reason": "agreement 83% >= 70%",
            "promotion_thresholds": {},
        },
        "suggestion_feed": {
            "traces_scanned": 42,
            "shadow_samples": 30,
            "disagreement_samples": 5,
            "entries": [],
            "gated": True,
            "gate_passed": True,
            "gate_reason": "baseline promote",
            "min_score_divergence": 0.0,
        },
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_baseline_and_feed_summary(self):
        module = _module()
        text = module._render_brain_status(_report_payload())
        assert "=== Brain v1 Operations Report ===" in text
        assert "Recommendation:   promote" in text
        assert "Reason:           agreement 83% >= 70%" in text
        assert "agreement=83.0%" in text
        assert "Gate passed:      True" in text
        assert "Disagreements:    5" in text

    def test_renders_error_payload_for_missing_trace_store(self):
        module = _module()
        text = module._render_brain_status(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/x.sqlite3"}
        )
        assert "trace_store_unavailable" in text
        assert "/tmp/x.sqlite3" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_status_delegates_to_services_core_with_parsed_args(
        self, monkeypatch, capsys
    ):
        module = _module()
        captured: dict = {}

        def fake_snapshot(**kwargs):
            captured.update(kwargs)
            return _report_payload()

        monkeypatch.setattr(
            "services.core.get_brain_operations_snapshot", fake_snapshot
        )

        exit_code = module.main(
            [
                "brain",
                "status",
                "--trace-limit",
                "250",
                "--workflow",
                "planner",
                "--max-feed-entries",
                "5",
            ]
        )
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "trace_limit": 250,
            "workflow_filter": "planner",
            "version_filter": None,
            "max_feed_entries": 5,
        }
        assert "Brain v1 Operations Report" in output
        assert "promote" in output

    def test_status_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_brain_operations_snapshot",
            lambda **_: _report_payload(),
        )

        exit_code = module.main(["brain", "status", "--json"])
        output = capsys.readouterr().out

        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["baseline"]["recommendation"] == "promote"
        assert parsed["suggestion_feed"]["gate_passed"] is True

    def test_status_enforces_minimum_trace_limit_of_one(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake_snapshot(**kwargs):
            captured.update(kwargs)
            return _report_payload()

        monkeypatch.setattr(
            "services.core.get_brain_operations_snapshot", fake_snapshot
        )

        module.main(["brain", "status", "--trace-limit", "0", "--json"])
        # The handler clamps trace_limit to >=1 before delegating.
        assert captured["trace_limit"] == 1

    def test_status_surfaces_service_error_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_brain_operations_snapshot",
            lambda **_: {
                "error": "trace_store_unavailable",
                "trace_store_path": "/tmp/missing.sqlite3",
            },
        )

        exit_code = module.main(["brain", "status"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert "Brain status unavailable" in output
        assert "trace_store_unavailable" in output
