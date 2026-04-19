"""§6.4 Data Governance — RetentionPruner tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.approval.models import ApprovalRequest, ApprovalStatus, CapabilityRisk
from core.approval.store import ApprovalStore
from core.audit.retention import RetentionPolicy, RetentionScanner
from core.audit.retention_pruner import (
    RetentionPruneOutcome,
    RetentionPruneResult,
    RetentionPruner,
)
from core.audit.trace_store import TraceStore

pytestmark = pytest.mark.unit


FIXED_NOW = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers (mirror test_retention.py patterns intentionally — the pruner is
# the destructive twin and must consume the same report shape)
# ---------------------------------------------------------------------------


def _make_approval(
    *,
    approval_id: str,
    requested_at: datetime,
    status: ApprovalStatus = ApprovalStatus.APPROVED,
) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=approval_id,
        plan_id="p",
        step_id="s",
        task_summary="t",
        reason="r",
        risk=CapabilityRisk.LOW,
        requested_at=requested_at,
        proposed_action_summary="x",
        status=status,
    )


def _write_trace_with_age(
    ts: TraceStore, *, days_old: float, trace_id_hint: str = ""
) -> str:
    trace = ts.create_trace(f"wf-{trace_id_hint}" if trace_id_hint else "wf")
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


def _make_pruner(tmp_path, policy: RetentionPolicy):
    ts = TraceStore(str(tmp_path / "traces.sqlite3"))
    approvals = ApprovalStore()
    scanner = RetentionScanner(trace_store=ts, approval_store=approvals, policy=policy)
    pruner = RetentionPruner(trace_store=ts, approval_store=approvals)
    return scanner, pruner, ts, approvals


# ---------------------------------------------------------------------------
# Dry-run default
# ---------------------------------------------------------------------------


class TestDryRunDefault:
    def test_prune_defaults_to_dry_run_and_touches_nothing(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, approvals = _make_pruner(tmp_path, policy)
        old = _write_trace_with_age(ts, days_old=90)
        approvals.create_request(
            _make_approval(
                approval_id="a-old",
                requested_at=FIXED_NOW - timedelta(days=120),
                status=ApprovalStatus.APPROVED,
            )
        )

        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert len(report.candidates) == 2

        result = pruner.prune(report)
        assert isinstance(result, RetentionPruneResult)
        assert result.dry_run is True
        # Both deletions "would" happen — the records still exist.
        assert result.traces_deleted == 1
        assert result.approvals_deleted == 1
        # And the stores are untouched.
        assert ts.get_trace(old) is not None
        assert approvals.get_request("a-old") is not None

    def test_dry_run_outcome_entries_mark_dry_run_true(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, _ap = _make_pruner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=90)
        report = scanner.scan(evaluation_time=FIXED_NOW)

        result = pruner.prune(report)
        assert all(o.dry_run is True for o in result.outcomes)


# ---------------------------------------------------------------------------
# Commit path (destructive)
# ---------------------------------------------------------------------------


class TestCommitPath:
    def test_commit_deletes_trace_candidates(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, _ap = _make_pruner(tmp_path, policy)
        old = _write_trace_with_age(ts, days_old=90, trace_id_hint="old")
        fresh = _write_trace_with_age(ts, days_old=1, trace_id_hint="fresh")

        report = scanner.scan(evaluation_time=FIXED_NOW)
        result = pruner.prune(report, commit=True)

        assert result.dry_run is False
        assert result.traces_deleted == 1
        assert ts.get_trace(old) is None
        # Fresh trace is untouched — it was not a candidate.
        assert ts.get_trace(fresh) is not None

    def test_commit_deletes_approval_candidates(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, _ts, approvals = _make_pruner(tmp_path, policy)
        approvals.create_request(
            _make_approval(
                approval_id="a-old",
                requested_at=FIXED_NOW - timedelta(days=120),
                status=ApprovalStatus.APPROVED,
            )
        )
        approvals.create_request(
            _make_approval(
                approval_id="a-fresh",
                requested_at=FIXED_NOW - timedelta(days=1),
                status=ApprovalStatus.APPROVED,
            )
        )

        report = scanner.scan(evaluation_time=FIXED_NOW)
        result = pruner.prune(report, commit=True)

        assert result.approvals_deleted == 1
        assert approvals.get_request("a-old") is None
        assert approvals.get_request("a-fresh") is not None

    def test_commit_removes_spans_and_explainability_rows(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, _ap = _make_pruner(tmp_path, policy)
        old = _write_trace_with_age(ts, days_old=90)

        # Sanity: store has spans before prune.
        conn = sqlite3.connect(ts.path)
        try:
            span_rows = conn.execute(
                "SELECT COUNT(*) FROM spans WHERE trace_id=?", (old,)
            ).fetchone()[0]
        finally:
            conn.close()
        assert span_rows > 0

        report = scanner.scan(evaluation_time=FIXED_NOW)
        pruner.prune(report, commit=True)

        conn = sqlite3.connect(ts.path)
        try:
            remaining_spans = conn.execute(
                "SELECT COUNT(*) FROM spans WHERE trace_id=?", (old,)
            ).fetchone()[0]
            remaining_explain = conn.execute(
                "SELECT COUNT(*) FROM explainability WHERE trace_id=?", (old,)
            ).fetchone()[0]
        finally:
            conn.close()
        assert remaining_spans == 0
        assert remaining_explain == 0


# ---------------------------------------------------------------------------
# Idempotency / concurrent-deletion tolerance
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_second_commit_is_noop(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, _ap = _make_pruner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=90)

        report = scanner.scan(evaluation_time=FIXED_NOW)
        first = pruner.prune(report, commit=True)
        assert first.traces_deleted == 1

        # Re-running with the same report: trace already gone, prune
        # returns deleted=False for each candidate, does not raise.
        second = pruner.prune(report, commit=True)
        assert second.traces_deleted == 0
        assert all(not o.deleted for o in second.outcomes)

    def test_dry_run_after_commit_shows_nothing_left(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, _ap = _make_pruner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=90)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        pruner.prune(report, commit=True)

        # A fresh scan would return an empty report.
        post_report = scanner.scan(evaluation_time=FIXED_NOW)
        assert post_report.candidates == []


# ---------------------------------------------------------------------------
# Empty / combined / ordering
# ---------------------------------------------------------------------------


class TestEmptyAndCombined:
    def test_empty_report_is_noop(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, _ts, _ap = _make_pruner(tmp_path, policy)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        result = pruner.prune(report, commit=True)
        assert result.traces_deleted == 0
        assert result.approvals_deleted == 0
        assert result.outcomes == []

    def test_combined_commit_counts_match_report(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, pruner, ts, approvals = _make_pruner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=90, trace_id_hint="t1")
        _write_trace_with_age(ts, days_old=100, trace_id_hint="t2")
        approvals.create_request(
            _make_approval(
                approval_id="a1",
                requested_at=FIXED_NOW - timedelta(days=120),
                status=ApprovalStatus.APPROVED,
            )
        )

        report = scanner.scan(evaluation_time=FIXED_NOW)
        result = pruner.prune(report, commit=True)

        assert result.trace_candidates == 2
        assert result.approval_candidates == 1
        assert result.traces_deleted == 2
        assert result.approvals_deleted == 1


# ---------------------------------------------------------------------------
# Schema hardening
# ---------------------------------------------------------------------------


class TestSchemaHardening:
    def test_prune_result_extra_forbid(self):
        with pytest.raises(ValueError):
            RetentionPruneResult(
                executed_at=FIXED_NOW,
                dry_run=True,
                trace_candidates=0,
                approval_candidates=0,
                traces_deleted=0,
                approvals_deleted=0,
                rogue="nope",  # type: ignore[call-arg]
            )

    def test_prune_outcome_extra_forbid(self):
        with pytest.raises(ValueError):
            RetentionPruneOutcome(
                kind="trace",
                record_id="t",
                deleted=True,
                dry_run=False,
                rogue="nope",  # type: ignore[call-arg]
            )
