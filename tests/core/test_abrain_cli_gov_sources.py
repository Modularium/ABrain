"""§6.4 – `abrain governance sources` CLI surface tests."""

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
        "path": "/tmp/abrain_knowledge_sources.json",
        "file_present": True,
        "source_count": 2,
        "load_warnings": [],
        "advisory_warnings": [],
        "sources": [
            {
                "source_id": "docs",
                "display_name": "Internal Docs",
                "trust": "trusted",
                "source_type": "document",
                "pii_risk": False,
                "has_provenance": False,
                "has_license": True,
                "retention_days": 30,
            },
            {
                "source_id": "ext",
                "display_name": "Ext",
                "trust": "external",
                "source_type": "document",
                "pii_risk": False,
                "has_provenance": True,
                "has_license": False,
                "retention_days": None,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_header_path_counts_and_sources(self):
        module = _module()
        text = module._render_governance_sources(_payload())
        assert "=== Knowledge Sources Registry ===" in text
        assert "Path:                 /tmp/abrain_knowledge_sources.json" in text
        assert "File present:         True" in text
        assert "Source count:         2" in text
        assert "Load warnings:        0" in text
        assert "Advisory warnings:    0" in text
        assert "Sources (2):" in text
        assert "- docs" in text
        assert "trust=trusted" in text
        assert "retention=30" in text
        assert "- ext" in text
        assert "retention=-" in text

    def test_renders_load_and_advisory_warnings_when_present(self):
        module = _module()
        payload = _payload()
        payload["load_warnings"] = [
            "entry_0_registration_failed: external missing provenance",
        ]
        payload["advisory_warnings"] = [
            "pii-src: pii_risk=True has no retention_days",
        ]
        text = module._render_governance_sources(payload)
        assert "Load warnings:        1" in text
        assert "Load warnings (1):" in text
        assert "- entry_0_registration_failed:" in text
        assert "Advisory warnings:    1" in text
        assert "Advisory warnings (1):" in text
        assert "- pii-src:" in text

    def test_renders_empty_registry_with_none_placeholder(self):
        module = _module()
        payload = _payload()
        payload["sources"] = []
        payload["source_count"] = 0
        text = module._render_governance_sources(payload)
        assert "Source count:         0" in text
        assert "Sources (0):" in text
        assert "(none)" in text

    def test_omits_warning_blocks_when_lists_empty(self):
        module = _module()
        text = module._render_governance_sources(_payload())
        assert "Load warnings (" not in text
        assert "Advisory warnings (" not in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_sources_delegates_to_service(self, monkeypatch, capsys):
        module = _module()
        called: dict = {"count": 0}

        def fake():
            called["count"] += 1
            return _payload()

        monkeypatch.setattr("services.core.get_knowledge_sources_status", fake)

        exit_code = module.main(["governance", "sources"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert called["count"] == 1
        assert "Knowledge Sources Registry" in output
        assert "Source count:         2" in output

    def test_sources_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_knowledge_sources_status",
            lambda: _payload(),
        )

        exit_code = module.main(["governance", "sources", "--json"])
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["source_count"] == 2
        assert parsed["sources"][1]["source_id"] == "ext"


# ---------------------------------------------------------------------------
# Service integration (real registry via bootstrap file)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_reflects_bootstrap_file(self, monkeypatch, tmp_path: Path):
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
                        "license": "MIT",
                    },
                ]
            )
        )
        monkeypatch.setenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", str(path))
        if hasattr(core_module._get_knowledge_registry_state, "_state"):
            delattr(core_module._get_knowledge_registry_state, "_state")

        status = core_module.get_knowledge_sources_status()
        assert status["path"] == str(path)
        assert status["file_present"] is True
        assert status["source_count"] == 1
        assert status["load_warnings"] == []
        assert status["sources"][0]["source_id"] == "docs"

    def test_service_reports_missing_file(self, monkeypatch, tmp_path: Path):
        import services.core as core_module

        path = tmp_path / "absent.json"
        monkeypatch.setenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", str(path))
        if hasattr(core_module._get_knowledge_registry_state, "_state"):
            delattr(core_module._get_knowledge_registry_state, "_state")

        status = core_module.get_knowledge_sources_status()
        assert status["file_present"] is False
        assert status["source_count"] == 0
        assert status["sources"] == []
