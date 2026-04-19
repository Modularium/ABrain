"""§6.4 – `abrain governance retention-prune` CLI surface tests."""

from __future__ import annotations

import importlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _dry_payload() -> dict:
    return {
        "executed_at": "2026-04-19T00:00:00+00:00",
        "dry_run": True,
        "apply": False,
        "trace_candidates": 2,
        "approval_candidates": 1,
        "traces_deleted": 0,
        "approvals_deleted": 0,
        "outcomes": [
            {"kind": "trace", "record_id": "t-0000", "deleted": True, "dry_run": True},
            {"kind": "trace", "record_id": "t-0001", "deleted": True, "dry_run": True},
            {"kind": "approval", "record_id": "a-1", "deleted": True, "dry_run": True},
        ],
        "report": {
            "policy": {
                "trace_retention_days": 30,
                "approval_retention_days": 30,
                "keep_open_traces": True,
                "keep_pending_approvals": True,
            },
            "totals": {"traces": 2, "approvals": 1},
        },
    }


def _applied_payload() -> dict:
    return {
        "executed_at": "2026-04-19T00:00:00+00:00",
        "dry_run": False,
        "apply": True,
        "trace_candidates": 2,
        "approval_candidates": 0,
        "traces_deleted": 2,
        "approvals_deleted": 0,
        "outcomes": [
            {"kind": "trace", "record_id": "t-0000", "deleted": True, "dry_run": False},
            {"kind": "trace", "record_id": "t-0001", "deleted": True, "dry_run": False},
        ],
        "report": {
            "policy": {
                "trace_retention_days": 30,
                "approval_retention_days": 30,
                "keep_open_traces": True,
                "keep_pending_approvals": True,
            },
            "totals": {"traces": 2, "approvals": 0},
        },
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_dry_run_summary(self):
        module = _module()
        text = module._render_governance_retention_prune(_dry_payload())
        assert "=== Governance Retention Prune (DRY-RUN) ===" in text
        assert "trace_retention_days:        30" in text
        assert "Trace candidates:            2" in text
        assert "Approval candidates:         1" in text
        assert "Traces deleted:              0" in text
        assert "[DEL ] trace:t-0000" in text
        assert "[DEL ] approval:a-1" in text
        assert "dry-run (no record deleted; re-run with --apply to commit)" in text

    def test_renders_applied_summary_without_dry_run_notice(self):
        module = _module()
        text = module._render_governance_retention_prune(_applied_payload())
        assert "=== Governance Retention Prune (APPLIED) ===" in text
        assert "Traces deleted:              2" in text
        assert "[DEL ] trace:t-0000" in text
        assert "dry_run=False" in text
        assert "dry-run (no record deleted" not in text

    def test_renders_skip_marker_for_not_deleted_outcomes(self):
        module = _module()
        payload = _dry_payload()
        payload["outcomes"][0]["deleted"] = False
        text = module._render_governance_retention_prune(payload)
        assert "[SKIP] trace:t-0000" in text

    def test_renders_empty_outcomes_with_none_placeholder(self):
        module = _module()
        payload = _dry_payload()
        payload["outcomes"] = []
        text = module._render_governance_retention_prune(payload)
        assert "Outcomes (0):" in text
        assert "(none)" in text

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_governance_retention_prune(
            {"error": "trace_store_unavailable", "trace_store_path": "/tmp/missing.sqlite3"}
        )
        assert "Retention prune unavailable: trace_store_unavailable" in text
        assert "/tmp/missing.sqlite3" in text


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_retention_prune_delegates_with_defaults_dry_run(
        self, monkeypatch, capsys
    ):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _dry_payload()

        monkeypatch.setattr("services.core.apply_retention_prune", fake)

        exit_code = module.main(["governance", "retention-prune"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "trace_retention_days": 90,
            "approval_retention_days": 90,
            "trace_limit": 10_000,
            "keep_open_traces": True,
            "keep_pending_approvals": True,
            "apply": False,
        }
        assert "Governance Retention Prune (DRY-RUN)" in output

    def test_retention_prune_forwards_apply_and_policy_flags(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.apply_retention_prune",
            lambda **kw: captured.update(kw) or _applied_payload(),
        )

        module.main(
            [
                "governance",
                "retention-prune",
                "--apply",
                "--trace-retention-days",
                "30",
                "--approval-retention-days",
                "7",
                "--trace-limit",
                "50",
                "--include-open-traces",
                "--include-pending-approvals",
                "--json",
            ]
        )
        assert captured["apply"] is True
        assert captured["trace_retention_days"] == 30
        assert captured["approval_retention_days"] == 7
        assert captured["trace_limit"] == 50
        assert captured["keep_open_traces"] is False
        assert captured["keep_pending_approvals"] is False

    def test_retention_prune_clamps_non_positive_day_inputs(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.apply_retention_prune",
            lambda **kw: captured.update(kw) or _dry_payload(),
        )

        module.main(
            [
                "governance",
                "retention-prune",
                "--trace-retention-days",
                "-1",
                "--approval-retention-days",
                "0",
                "--trace-limit",
                "-8",
                "--json",
            ]
        )
        assert captured["trace_retention_days"] == 1
        assert captured["approval_retention_days"] == 1
        assert captured["trace_limit"] == 1

    def test_retention_prune_json_mode_emits_dumpable_payload(
        self, monkeypatch, capsys
    ):
        module = _module()
        monkeypatch.setattr(
            "services.core.apply_retention_prune",
            lambda **_: _applied_payload(),
        )

        exit_code = module.main(["governance", "retention-prune", "--apply", "--json"])
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["apply"] is True
        assert parsed["traces_deleted"] == 2


# ---------------------------------------------------------------------------
# Service integration (real TraceStore + ApprovalStore)
# ---------------------------------------------------------------------------


FIXED_NOW = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


def _write_trace_with_age(ts, *, days_old: float, trace_id_hint: str) -> str:
    trace = ts.create_trace(f"wf-{trace_id_hint}")
    span = ts.start_span(trace.trace_id, span_type="step", name="s1", attributes={})
    ts.finish_span(span.span_id, status="ok")
    ts.finish_trace(trace.trace_id, status="ok")

    started = (FIXED_NOW - timedelta(days=days_old)).isoformat()
    conn = sqlite3.connect(ts.path)
    try:
        conn.execute(
            "UPDATE traces SET started_at=?, ended_at=? WHERE trace_id=?",
            (started, started, trace.trace_id),
        )
        conn.commit()
    finally:
        conn.close()
    return trace.trace_id


class TestServiceIntegration:
    def test_service_surfaces_trace_store_unavailable(self, monkeypatch):
        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_trace_state",
            lambda: {"store": None, "path": "/tmp/abrain-missing.sqlite3"},
        )
        report = core_module.apply_retention_prune()
        assert report["error"] == "trace_store_unavailable"
        assert report["trace_store_path"] == "/tmp/abrain-missing.sqlite3"

    def test_service_dry_run_keeps_traces_intact(self, monkeypatch, tmp_path: Path):
        from core.approval.store import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        trace_id = _write_trace_with_age(trace_store, days_old=60, trace_id_hint="old")

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

        report = core_module.apply_retention_prune(trace_retention_days=30)
        assert report["apply"] is False
        assert report["dry_run"] is True
        assert report["trace_candidates"] == 1
        # In dry-run, `traces_deleted` reflects records that *would* be
        # deleted — the authoritative check is that the store still has
        # the trace.
        assert trace_store.get_trace(trace_id) is not None

    def test_service_apply_deletes_overdue_traces(
        self, monkeypatch, tmp_path: Path
    ):
        from core.approval.store import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        old_id = _write_trace_with_age(trace_store, days_old=60, trace_id_hint="old")
        fresh_id = _write_trace_with_age(trace_store, days_old=1, trace_id_hint="new")

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

        report = core_module.apply_retention_prune(
            trace_retention_days=30, apply=True
        )
        assert report["apply"] is True
        assert report["dry_run"] is False
        assert report["trace_candidates"] == 1
        assert report["traces_deleted"] == 1
        # Only the overdue trace is removed; the fresh one stays.
        assert trace_store.get_trace(old_id) is None
        assert trace_store.get_trace(fresh_id) is not None

    def test_service_apply_without_candidates_is_noop(
        self, monkeypatch, tmp_path: Path
    ):
        from core.approval.store import ApprovalStore
        from core.audit.trace_store import TraceStore
        import services.core as core_module

        trace_store = TraceStore(str(tmp_path / "traces.sqlite3"))
        approval_store = ApprovalStore(path=tmp_path / "approvals.json")
        fresh_id = _write_trace_with_age(trace_store, days_old=1, trace_id_hint="new")

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

        report = core_module.apply_retention_prune(
            trace_retention_days=90, apply=True
        )
        assert report["trace_candidates"] == 0
        assert report["traces_deleted"] == 0
        assert report["outcomes"] == []
        assert trace_store.get_trace(fresh_id) is not None
