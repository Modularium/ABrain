"""§6.4 – `abrain governance pii` CLI surface tests."""

from __future__ import annotations

import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _payload() -> dict:
    return {
        "retention_report": {
            "generated_at": "2026-04-19T00:00:00+00:00",
            "evaluation_time": "2026-04-19T00:00:00+00:00",
            "policy": {
                "trace_retention_days": 30,
                "approval_retention_days": 14,
                "keep_open_traces": True,
                "keep_pending_approvals": True,
            },
            "trace_limit": 5000,
            "candidates": [],
            "totals": {
                "traces_scanned": 100,
                "approvals_scanned": 25,
                "trace_candidates": 1,
                "approval_candidates": 1,
            },
        },
        "pii_annotation": {
            "total_candidates": 2,
            "candidates_with_findings": 1,
            "annotations": [
                {
                    "kind": "trace",
                    "record_id": "trace-1",
                    "finding_count": 2,
                    "result": {
                        "scanned_fields": 5,
                        "findings": [
                            {
                                "source_path": "trace:trace-1.metadata.user",
                                "matches": [
                                    {
                                        "category": "email",
                                        "span_start": 0,
                                        "span_end": 17,
                                        "placeholder": "[email]",
                                    }
                                ],
                            },
                            {
                                "source_path": "trace:trace-1.span:s1.attributes.note",
                                "matches": [
                                    {
                                        "category": "ipv4",
                                        "span_start": 0,
                                        "span_end": 11,
                                        "placeholder": "[ipv4]",
                                    }
                                ],
                            },
                        ],
                        "category_counts": {"email": 1, "ipv4": 1},
                    },
                },
                {
                    "kind": "approval",
                    "record_id": "appr-1",
                    "finding_count": 0,
                    "result": {
                        "scanned_fields": 3,
                        "findings": [],
                        "category_counts": {},
                    },
                },
            ],
            "category_counts": {"email": 1, "ipv4": 1},
        },
        "policy": {
            "enabled_categories": ["email", "ipv4", "credit_card", "iban", "api_key"],
        },
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_policy_totals_and_flagged_candidates(self):
        module = _module()
        text = module._render_governance_pii(_payload())
        assert "=== Governance PII Annotation" in text
        assert "Total candidates:        2" in text
        assert "Candidates with findings: 1" in text
        assert "- email: 1" in text
        assert "- ipv4: 1" in text
        assert "Flagged candidates (1):" in text
        assert "[trace] trace-1" in text
        assert "categories=email,ipv4" in text

    def test_renders_no_findings_as_none(self):
        module = _module()
        payload = _payload()
        payload["pii_annotation"]["candidates_with_findings"] = 0
        payload["pii_annotation"]["category_counts"] = {}
        for entry in payload["pii_annotation"]["annotations"]:
            entry["finding_count"] = 0
            entry["result"]["findings"] = []
            entry["result"]["category_counts"] = {}
        text = module._render_governance_pii(payload)
        assert "Category counts:    (none)" in text
        assert "Flagged candidates (0):" in text
        assert "(none)" in text

    def test_renders_error_payload_for_missing_trace_store(self):
        module = _module()
        text = module._render_governance_pii(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/x.sqlite3"}
        )
        assert "PII scan unavailable" in text
        assert "trace_store_unavailable" in text
        assert "/tmp/x.sqlite3" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_pii_delegates_to_services_core_with_parsed_args(
        self, monkeypatch, capsys
    ):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_retention_pii_annotation", fake)

        exit_code = module.main(
            [
                "governance",
                "pii",
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
            "enabled_categories": None,
        }
        assert "Governance PII Annotation" in output

    def test_pii_categories_split_and_trim(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_retention_pii_annotation", fake)

        module.main(
            [
                "governance",
                "pii",
                "--categories",
                " email , ipv4 , ,api_key",
                "--json",
            ]
        )
        assert captured["enabled_categories"] == ["email", "ipv4", "api_key"]

    def test_pii_include_flags_flip_keep_defaults(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_retention_pii_annotation", fake)

        module.main(
            [
                "governance",
                "pii",
                "--include-open-traces",
                "--include-pending-approvals",
                "--json",
            ]
        )
        assert captured["keep_open_traces"] is False
        assert captured["keep_pending_approvals"] is False

    def test_pii_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_retention_pii_annotation",
            lambda **_: _payload(),
        )

        exit_code = module.main(["governance", "pii", "--json"])
        output = capsys.readouterr().out

        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["pii_annotation"]["candidates_with_findings"] == 1
        assert parsed["policy"]["enabled_categories"][0] == "email"

    def test_pii_clamps_minimums(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_retention_pii_annotation", fake)

        module.main(
            [
                "governance",
                "pii",
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

    def test_pii_surfaces_service_error_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_retention_pii_annotation",
            lambda **_: {
                "error": "trace_store_unavailable",
                "trace_store_path": "/tmp/missing.sqlite3",
            },
        )

        exit_code = module.main(["governance", "pii"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert "PII scan unavailable" in output
        assert "trace_store_unavailable" in output
