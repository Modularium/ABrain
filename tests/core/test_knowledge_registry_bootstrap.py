"""§6.4 / Phase 3 – KnowledgeSourceRegistry bootstrap loader tests.

Covers the canonical persistence loader wired into ``services.core``
via ``_get_knowledge_registry_state`` + ``get_knowledge_sources_status``.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _fresh_core(monkeypatch, *, env_path: str | None = None):
    """Import ``services.core`` with a clean registry-state cache."""
    import services.core as core_module

    if hasattr(core_module._get_knowledge_registry_state, "_state"):
        delattr(core_module._get_knowledge_registry_state, "_state")
    if env_path is not None:
        monkeypatch.setenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", env_path)
    else:
        monkeypatch.delenv("ABRAIN_KNOWLEDGE_SOURCES_PATH", raising=False)
    return core_module


def _trusted_source(source_id: str = "docs", **overrides):
    payload = {
        "source_id": source_id,
        "display_name": "Internal Docs",
        "trust": "trusted",
        "source_type": "document",
    }
    payload.update(overrides)
    return payload


class TestBootstrapLoader:
    def test_missing_file_yields_empty_registry(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "absent.json"
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert state["file_present"] is False
        assert state["load_warnings"] == []
        assert state["advisory_warnings"] == []
        assert len(state["registry"]) == 0

    def test_unreadable_json_surfaces_load_warning(
        self, monkeypatch, tmp_path: Path
    ):
        path = tmp_path / "sources.json"
        path.write_text("{not-json")
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert state["file_present"] is True
        assert len(state["registry"]) == 0
        assert any(
            w.startswith("knowledge_sources_unreadable:")
            for w in state["load_warnings"]
        )

    def test_non_list_top_level_surfaces_schema_warning(
        self, monkeypatch, tmp_path: Path
    ):
        path = tmp_path / "sources.json"
        path.write_text(json.dumps({"not": "a list"}))
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert len(state["registry"]) == 0
        assert any(
            w.startswith("knowledge_sources_schema_invalid:")
            for w in state["load_warnings"]
        )

    def test_non_object_entry_is_skipped(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "sources.json"
        path.write_text(json.dumps(["not-an-object", _trusted_source("docs")]))
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert len(state["registry"]) == 1
        assert any(
            w.startswith("entry_0_schema_invalid:") for w in state["load_warnings"]
        )

    def test_pydantic_validation_failure_is_skipped(
        self, monkeypatch, tmp_path: Path
    ):
        path = tmp_path / "sources.json"
        # Missing required display_name on the first entry; second is valid.
        path.write_text(
            json.dumps(
                [
                    {"source_id": "bad", "trust": "trusted", "source_type": "doc"},
                    _trusted_source("good"),
                ]
            )
        )
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert [s.source_id for s in state["registry"].list_all()] == ["good"]
        assert any(
            w.startswith("entry_0_validation_failed:")
            for w in state["load_warnings"]
        )

    def test_registration_error_is_skipped(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "sources.json"
        # External source without provenance violates registry governance.
        path.write_text(
            json.dumps(
                [
                    {
                        "source_id": "ext",
                        "display_name": "Ext",
                        "trust": "external",
                        "source_type": "doc",
                    },
                    _trusted_source("docs"),
                ]
            )
        )
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert [s.source_id for s in state["registry"].list_all()] == ["docs"]
        assert any(
            w.startswith("entry_0_registration_failed:")
            for w in state["load_warnings"]
        )

    def test_valid_sources_register_and_surface_advisory_warnings(
        self, monkeypatch, tmp_path: Path
    ):
        path = tmp_path / "sources.json"
        path.write_text(
            json.dumps(
                [
                    _trusted_source("docs"),
                    {
                        "source_id": "pii-src",
                        "display_name": "PII",
                        "trust": "internal",
                        "source_type": "doc",
                        "pii_risk": True,
                    },
                ]
            )
        )
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()

        assert [s.source_id for s in state["registry"].list_all()] == [
            "docs",
            "pii-src",
        ]
        assert state["load_warnings"] == []
        assert any("pii-src" in w and "retention_days" in w for w in state["advisory_warnings"])

    def test_cache_is_idempotent_across_calls(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "sources.json"
        path.write_text(json.dumps([_trusted_source("docs")]))
        core = _fresh_core(monkeypatch, env_path=str(path))

        state_a = core._get_knowledge_registry_state()
        # Rewrite the file — cache must not be re-read.
        path.write_text(json.dumps([_trusted_source("docs"), _trusted_source("other")]))
        state_b = core._get_knowledge_registry_state()

        assert state_a is state_b
        assert len(state_b["registry"]) == 1


class TestStatusService:
    def test_status_exposes_path_and_counts(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "sources.json"
        path.write_text(
            json.dumps(
                [
                    _trusted_source("docs", retention_days=30, license="MIT"),
                ]
            )
        )
        core = _fresh_core(monkeypatch, env_path=str(path))
        status = core.get_knowledge_sources_status()

        assert status["path"] == str(path)
        assert status["file_present"] is True
        assert status["source_count"] == 1
        assert status["load_warnings"] == []
        assert status["advisory_warnings"] == []
        assert len(status["sources"]) == 1
        entry = status["sources"][0]
        assert entry["source_id"] == "docs"
        assert entry["trust"] == "trusted"
        assert entry["has_provenance"] is False
        assert entry["has_license"] is True
        assert entry["retention_days"] == 30

    def test_status_reports_load_warnings_when_file_absent(
        self, monkeypatch, tmp_path: Path
    ):
        path = tmp_path / "absent.json"
        core = _fresh_core(monkeypatch, env_path=str(path))
        status = core.get_knowledge_sources_status()

        assert status["file_present"] is False
        assert status["source_count"] == 0
        assert status["sources"] == []

    def test_status_returns_copies_not_live_references(
        self, monkeypatch, tmp_path: Path
    ):
        path = tmp_path / "sources.json"
        path.write_text(json.dumps([_trusted_source("docs")]))
        core = _fresh_core(monkeypatch, env_path=str(path))
        state = core._get_knowledge_registry_state()
        status = core.get_knowledge_sources_status()

        status["load_warnings"].append("mutation attempt")
        status["advisory_warnings"].append("mutation attempt")
        # The cached state must not be mutated by caller-side edits.
        assert state["load_warnings"] == []
        assert state["advisory_warnings"] == []
