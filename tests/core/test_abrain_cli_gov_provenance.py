"""§6.4 – `abrain governance provenance` CLI surface tests."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "policy": {
            "require_provenance_for": ["external", "untrusted"],
            "require_license_for": ["external", "untrusted"],
            "require_retention_for_pii": True,
            "require_retention_for_all": False,
        },
        "statuses": [
            {
                "source_id": "docs",
                "trust": "trusted",
                "pii_risk": False,
                "has_provenance": False,
                "has_license": True,
                "retention_days": 30,
                "findings": [],
                "compliant": True,
            },
            {
                "source_id": "ext",
                "trust": "external",
                "pii_risk": False,
                "has_provenance": False,
                "has_license": False,
                "retention_days": None,
                "findings": [
                    {
                        "kind": "provenance_missing",
                        "message": "Source 'ext' (trust=external) has no provenance declared.",
                    },
                    {
                        "kind": "license_missing",
                        "message": "Source 'ext' (trust=external) has no license declared.",
                    },
                ],
                "compliant": False,
            },
        ],
        "totals": {
            "sources_scanned": 2,
            "compliant_sources": 1,
            "sources_with_findings": 1,
            "finding_counts": {
                "provenance_missing": 1,
                "license_missing": 1,
            },
        },
        "registry": {
            "path": "/tmp/abrain_knowledge_sources.json",
            "file_present": True,
            "load_warnings": [],
            "advisory_warnings": [],
        },
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_totals_policy_and_statuses(self):
        module = _module()
        text = module._render_governance_provenance(_payload())
        assert "=== Governance Provenance Report ===" in text
        assert "Path:                 /tmp/abrain_knowledge_sources.json" in text
        assert "File present:         True" in text
        assert "require_provenance_for:      external, untrusted" in text
        assert "Sources scanned:       2" in text
        assert "Compliant sources:     1" in text
        assert "- provenance_missing: 1" in text
        assert "- license_missing: 1" in text
        assert "[OK  ] docs" in text
        assert "[FAIL] ext" in text
        assert "* provenance_missing: Source 'ext'" in text

    def test_renders_load_warnings_block_when_present(self):
        module = _module()
        payload = _payload()
        payload["registry"]["load_warnings"] = [
            "entry_0_registration_failed: external missing provenance",
            "entry_2_validation_failed: pydantic thing",
        ]
        text = module._render_governance_provenance(payload)
        assert "Load warnings:        2" in text
        assert "Load warnings (2):" in text
        assert "- entry_0_registration_failed:" in text

    def test_renders_empty_registry_and_no_findings(self):
        module = _module()
        payload = _payload()
        payload["statuses"] = []
        payload["totals"] = {
            "sources_scanned": 0,
            "compliant_sources": 0,
            "sources_with_findings": 0,
            "finding_counts": {},
        }
        text = module._render_governance_provenance(payload)
        assert "Finding counts (0):" in text
        assert "Sources (0):" in text
        assert text.count("(none)") == 2

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_governance_provenance(
            {"error": "provenance_policy_invalid", "detail": "unknown trust level"}
        )
        assert "Provenance report unavailable: provenance_policy_invalid" in text
        assert "unknown trust level" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_provenance_delegates_with_defaults(self, monkeypatch, capsys):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_provenance_report", fake)

        exit_code = module.main(["governance", "provenance"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "require_provenance_for": None,
            "require_license_for": None,
            "require_retention_for_pii": True,
            "require_retention_for_all": False,
        }
        assert "Governance Provenance Report" in output

    def test_provenance_parses_trust_level_lists_and_flips_retention_flags(
        self, monkeypatch
    ):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_provenance_report",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "governance",
                "provenance",
                "--require-provenance-for",
                " trusted , ,internal , external",
                "--require-license-for",
                "external",
                "--no-require-retention-for-pii",
                "--require-retention-for-all",
                "--json",
            ]
        )
        assert captured["require_provenance_for"] == [
            "trusted",
            "internal",
            "external",
        ]
        assert captured["require_license_for"] == ["external"]
        assert captured["require_retention_for_pii"] is False
        assert captured["require_retention_for_all"] is True

    def test_provenance_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_provenance_report",
            lambda **_: _payload(),
        )

        exit_code = module.main(["governance", "provenance", "--json"])
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["totals"]["sources_scanned"] == 2
        assert parsed["statuses"][1]["source_id"] == "ext"


# ---------------------------------------------------------------------------
# Service integration (real registry, real ProvenanceScanner)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_rejects_unknown_trust_level(self, monkeypatch):
        import services.core as core_module

        if hasattr(core_module._get_knowledge_registry_state, "_state"):
            delattr(core_module._get_knowledge_registry_state, "_state")

        report = core_module.get_provenance_report(
            require_provenance_for=["trusted", "not-a-real-level"]
        )
        assert report["error"] == "provenance_policy_invalid"
        assert "not-a-real-level" in report["detail"]

    def test_service_scans_real_registry_from_bootstrap_file(
        self, monkeypatch, tmp_path: Path
    ):
        import services.core as core_module

        path = tmp_path / "sources.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "source_id": "docs",
                        "display_name": "Docs",
                        "trust": "trusted",
                        "source_type": "document",
                        "retention_days": 30,
                    },
                    {
                        "source_id": "ext",
                        "display_name": "Ext",
                        "trust": "external",
                        "source_type": "document",
                        "provenance": "https://example.com",
                    },
                ]
            )
        )
        monkeypatch.setenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", str(path))
        if hasattr(core_module._get_knowledge_registry_state, "_state"):
            delattr(core_module._get_knowledge_registry_state, "_state")

        report = core_module.get_provenance_report()
        assert "error" not in report
        assert report["totals"]["sources_scanned"] == 2
        # ext has no license → flagged; docs is trusted + has retention → clean.
        assert report["totals"]["sources_with_findings"] == 1
        assert report["totals"]["finding_counts"] == {"license_missing": 1}
        assert report["registry"]["path"] == str(path)
        assert report["registry"]["file_present"] is True

    def test_service_require_retention_for_all_widens_findings(
        self, monkeypatch, tmp_path: Path
    ):
        import services.core as core_module

        path = tmp_path / "sources.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "source_id": "docs",
                        "display_name": "Docs",
                        "trust": "trusted",
                        "source_type": "document",
                    },
                ]
            )
        )
        monkeypatch.setenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", str(path))
        if hasattr(core_module._get_knowledge_registry_state, "_state"):
            delattr(core_module._get_knowledge_registry_state, "_state")

        report = core_module.get_provenance_report(require_retention_for_all=True)
        assert report["totals"]["sources_with_findings"] == 1
        assert report["totals"]["finding_counts"] == {"retention_missing": 1}

    def test_service_echoes_bootstrap_load_warnings(
        self, monkeypatch, tmp_path: Path
    ):
        import services.core as core_module

        path = tmp_path / "sources.json"
        # Top-level non-list → triggers knowledge_sources_schema_invalid warning.
        path.write_text(json.dumps({"not": "a list"}))
        monkeypatch.setenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", str(path))
        if hasattr(core_module._get_knowledge_registry_state, "_state"):
            delattr(core_module._get_knowledge_registry_state, "_state")

        report = core_module.get_provenance_report()
        assert report["totals"]["sources_scanned"] == 0
        assert any(
            w.startswith("knowledge_sources_schema_invalid:")
            for w in report["registry"]["load_warnings"]
        )
