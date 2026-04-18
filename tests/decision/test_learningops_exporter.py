"""Phase 5 – LearningOps L2: DatasetExporter tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.decision.learning.exporter import DatasetExporter, ExportManifest, SCHEMA_VERSION
from core.decision.learning.record import LearningRecord

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rec(**kwargs) -> LearningRecord:
    defaults = dict(
        trace_id="t1",
        workflow_name="w1",
        has_routing_decision=True,
        has_outcome=True,
        has_approval_outcome=False,
    )
    defaults.update(kwargs)
    return LearningRecord(**defaults)


# ---------------------------------------------------------------------------
# DatasetExporter – export
# ---------------------------------------------------------------------------


class TestDatasetExporterExport:
    def test_creates_output_dir_if_missing(self, tmp_path):
        new_dir = tmp_path / "exports" / "sub"
        exporter = DatasetExporter(new_dir)
        exporter.export([])
        assert new_dir.is_dir()

    def test_empty_export_produces_manifest_only(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        path = exporter.export([], filename="empty.jsonl")
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        manifest = json.loads(lines[0])
        assert manifest["__manifest__"] is True
        assert manifest["record_count"] == 0

    def test_export_returns_path_to_created_file(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        path = exporter.export([_rec()], filename="test.jsonl")
        assert path.exists()
        assert path.suffix == ".jsonl"

    def test_record_is_written_as_second_line(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        rec = _rec(trace_id="trace-abc", selected_agent_id="agent-X")
        path = exporter.export([rec], filename="single.jsonl")
        lines = path.read_text().splitlines()
        assert len(lines) == 2
        data = json.loads(lines[1])
        assert data["trace_id"] == "trace-abc"
        assert data["selected_agent_id"] == "agent-X"

    def test_manifest_counts_are_correct(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        r_routing = _rec(has_routing_decision=True, has_outcome=True, has_approval_outcome=True)
        r_no_routing = _rec(has_routing_decision=False, has_outcome=True, has_approval_outcome=False)
        path = exporter.export([r_routing, r_no_routing], filename="counts.jsonl")
        manifest = json.loads(path.read_text().splitlines()[0])
        assert manifest["record_count"] == 2
        assert manifest["has_routing_count"] == 1
        assert manifest["has_outcome_count"] == 2
        assert manifest["has_approval_count"] == 1

    def test_manifest_contains_schema_version(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        path = exporter.export([], filename="v.jsonl")
        manifest = json.loads(path.read_text().splitlines()[0])
        assert manifest["schema_version"] == SCHEMA_VERSION

    def test_manifest_contains_exported_at_iso(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        path = exporter.export([], filename="ts.jsonl")
        manifest = json.loads(path.read_text().splitlines()[0])
        ts = manifest["exported_at"]
        assert "T" in ts and ("+" in ts or "Z" in ts or "z" in ts or ts.endswith("+00:00"))

    def test_default_filename_contains_schema_version(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        path = exporter.export([])
        assert f"v{SCHEMA_VERSION}" in path.name

    def test_multiple_records_produce_correct_line_count(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        records = [_rec(trace_id=f"t{i}") for i in range(5)]
        path = exporter.export(records, filename="multi.jsonl")
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 6  # 1 manifest + 5 records

    def test_custom_schema_version(self, tmp_path):
        exporter = DatasetExporter(tmp_path, schema_version="2.0")
        path = exporter.export([], filename="v2.jsonl")
        manifest = json.loads(path.read_text().splitlines()[0])
        assert manifest["schema_version"] == "2.0"


# ---------------------------------------------------------------------------
# DatasetExporter – load (round-trip)
# ---------------------------------------------------------------------------


class TestDatasetExporterLoad:
    def test_round_trip_preserves_all_fields(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        original = _rec(
            trace_id="trace-42",
            workflow_name="my-flow",
            selected_agent_id="agent-Z",
            candidate_agent_ids=["agent-Z", "agent-Y"],
            selected_score=0.77,
            routing_confidence=0.88,
            score_gap=0.11,
            confidence_band="medium",
            policy_effect="allow",
            matched_policy_ids=["p-1"],
            approval_required=False,
            success=True,
            cost_usd=0.002,
            latency_ms=500.0,
            has_routing_decision=True,
            has_outcome=True,
            has_approval_outcome=False,
        )
        path = exporter.export([original], filename="roundtrip.jsonl")
        manifest, loaded = exporter.load(path)

        assert len(loaded) == 1
        rec = loaded[0]
        assert rec.trace_id == "trace-42"
        assert rec.selected_agent_id == "agent-Z"
        assert rec.candidate_agent_ids == ["agent-Z", "agent-Y"]
        assert rec.selected_score == pytest.approx(0.77)
        assert rec.routing_confidence == pytest.approx(0.88)
        assert rec.confidence_band == "medium"
        assert rec.policy_effect == "allow"
        assert rec.success is True
        assert rec.cost_usd == pytest.approx(0.002)
        assert rec.has_routing_decision

    def test_load_returns_correct_manifest(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        path = exporter.export([_rec(), _rec(trace_id="t2")], filename="mf.jsonl")
        manifest, records = exporter.load(path)
        assert isinstance(manifest, ExportManifest)
        assert manifest.record_count == 2
        assert manifest.schema_version == SCHEMA_VERSION

    def test_load_empty_file_raises(self, tmp_path):
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        exporter = DatasetExporter(tmp_path)
        with pytest.raises(ValueError, match="empty"):
            exporter.load(empty)

    def test_load_missing_manifest_raises(self, tmp_path):
        bad = tmp_path / "bad.jsonl"
        bad.write_text('{"trace_id": "x", "workflow_name": "y"}\n', encoding="utf-8")
        exporter = DatasetExporter(tmp_path)
        with pytest.raises(ValueError, match="manifest"):
            exporter.load(bad)

    def test_load_multiple_records_round_trip(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        records = [_rec(trace_id=f"tr{i}") for i in range(10)]
        path = exporter.export(records, filename="batch.jsonl")
        _, loaded = exporter.load(path)
        assert len(loaded) == 10
        assert [r.trace_id for r in loaded] == [f"tr{i}" for i in range(10)]


# ---------------------------------------------------------------------------
# DatasetExporter – list_exports
# ---------------------------------------------------------------------------


class TestDatasetExporterListExports:
    def test_list_exports_empty_when_no_dir(self, tmp_path):
        exporter = DatasetExporter(tmp_path / "nonexistent")
        assert exporter.list_exports() == []

    def test_list_exports_returns_jsonl_files(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        exporter.export([], filename="a.jsonl")
        exporter.export([], filename="b.jsonl")
        exports = exporter.list_exports()
        names = {p.name for p in exports}
        assert "a.jsonl" in names
        assert "b.jsonl" in names

    def test_list_exports_ignores_non_jsonl(self, tmp_path):
        exporter = DatasetExporter(tmp_path)
        exporter.export([], filename="data.jsonl")
        (tmp_path / "readme.txt").write_text("ignored")
        exports = exporter.list_exports()
        assert all(p.suffix == ".jsonl" for p in exports)


# ---------------------------------------------------------------------------
# ExportManifest
# ---------------------------------------------------------------------------


class TestExportManifest:
    def test_repr_includes_key_fields(self):
        m = ExportManifest({
            "schema_version": "1.0",
            "exported_at": "2026-01-01T00:00:00+00:00",
            "record_count": 7,
            "has_routing_count": 5,
            "has_outcome_count": 3,
            "has_approval_count": 1,
        })
        r = repr(m)
        assert "1.0" in r
        assert "7" in r

    def test_defaults_for_missing_keys(self):
        m = ExportManifest({})
        assert m.schema_version == "unknown"
        assert m.record_count == 0
