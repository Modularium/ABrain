"""§6.4 – `abrain governance retention` CLI surface tests."""

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
        "evaluation_time": "2026-04-19T00:00:00+00:00",
        "policy": {
            "trace_retention_days": 30,
            "approval_retention_days": 14,
            "keep_open_traces": True,
            "keep_pending_approvals": True,
        },
        "trace_limit": 5000,
        "candidates": [
            {
                "kind": "trace",
                "record_id": "trace-1",
                "age_days": 45.7,
                "retention_days": 30,
                "reason": "trace age 45.70d > retention window 30d",
            },
            {
                "kind": "approval",
                "record_id": "appr-1",
                "age_days": 22.0,
                "retention_days": 14,
                "reason": "approval age 22.00d > retention window 14d",
            },
        ],
        "totals": {
            "traces_scanned": 100,
            "approvals_scanned": 25,
            "trace_candidates": 1,
            "approval_candidates": 1,
        },
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_policy_totals_and_candidates(self):
        module = _module()
        text = module._render_governance_retention(_report_payload())
        assert "=== Governance Retention Report ===" in text
        assert "trace_retention_days:    30" in text
        assert "approval_retention_days: 14" in text
        assert "Trace candidates:    1" in text
        assert "Approval candidates: 1" in text
        assert "[trace] trace-1" in text
        assert "[approval] appr-1" in text

    def test_renders_empty_candidate_list_as_none(self):
        module = _module()
        payload = _report_payload()
        payload["candidates"] = []
        payload["totals"]["trace_candidates"] = 0
        payload["totals"]["approval_candidates"] = 0
        text = module._render_governance_retention(payload)
        assert "Candidates (0):" in text
        assert "(none)" in text

    def test_renders_error_payload_for_missing_trace_store(self):
        module = _module()
        text = module._render_governance_retention(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/x.sqlite3"}
        )
        assert "Retention scan unavailable" in text
        assert "trace_store_unavailable" in text
        assert "/tmp/x.sqlite3" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_retention_delegates_to_services_core_with_parsed_args(
        self, monkeypatch, capsys
    ):
        module = _module()
        captured: dict = {}

        def fake_scan(**kwargs):
            captured.update(kwargs)
            return _report_payload()

        monkeypatch.setattr("services.core.get_retention_scan", fake_scan)

        exit_code = module.main(
            [
                "governance",
                "retention",
                "--trace-retention-days",
                "30",
                "--approval-retention-days",
                "14",
                "--trace-limit",
                "5000",
            ]
        )
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "trace_retention_days": 30,
            "approval_retention_days": 14,
            "trace_limit": 5000,
            "keep_open_traces": True,
            "keep_pending_approvals": True,
        }
        assert "Governance Retention Report" in output

    def test_retention_include_flags_flip_keep_defaults(self, monkeypatch, capsys):
        module = _module()
        captured: dict = {}

        def fake_scan(**kwargs):
            captured.update(kwargs)
            return _report_payload()

        monkeypatch.setattr("services.core.get_retention_scan", fake_scan)

        module.main(
            [
                "governance",
                "retention",
                "--include-open-traces",
                "--include-pending-approvals",
            ]
        )
        assert captured["keep_open_traces"] is False
        assert captured["keep_pending_approvals"] is False

    def test_retention_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_retention_scan",
            lambda **_: _report_payload(),
        )

        exit_code = module.main(["governance", "retention", "--json"])
        output = capsys.readouterr().out

        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["totals"]["trace_candidates"] == 1
        assert parsed["candidates"][0]["kind"] == "trace"

    def test_retention_clamps_minimums(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake_scan(**kwargs):
            captured.update(kwargs)
            return _report_payload()

        monkeypatch.setattr("services.core.get_retention_scan", fake_scan)

        module.main(
            [
                "governance",
                "retention",
                "--trace-retention-days",
                "0",
                "--approval-retention-days",
                "-5",
                "--trace-limit",
                "0",
                "--json",
            ]
        )
        assert captured["trace_retention_days"] == 1
        assert captured["approval_retention_days"] == 1
        assert captured["trace_limit"] == 1

    def test_retention_surfaces_service_error_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_retention_scan",
            lambda **_: {
                "error": "trace_store_unavailable",
                "trace_store_path": "/tmp/missing.sqlite3",
            },
        )

        exit_code = module.main(["governance", "retention"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert "Retention scan unavailable" in output
        assert "trace_store_unavailable" in output
