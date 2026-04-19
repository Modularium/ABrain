"""§6.4 Data Governance — RetentionScanner tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    CapabilityRisk,
)
from core.approval.store import ApprovalStore
from core.audit.retention import (
    RetentionCandidate,
    RetentionPolicy,
    RetentionReport,
    RetentionScanner,
)
from core.audit.trace_store import TraceStore

pytestmark = pytest.mark.unit


FIXED_NOW = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_approval(
    *,
    approval_id: str,
    requested_at: datetime,
    status: ApprovalStatus = ApprovalStatus.PENDING,
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


def _record_approval_decision(
    store: ApprovalStore, approval_id: str, status: ApprovalStatus
) -> None:
    store.record_decision(
        approval_id,
        ApprovalDecision(
            approval_id=approval_id,
            decision=status,
            decided_by="admin",
            decided_at=FIXED_NOW,
        ),
    )


def _write_trace_with_age(
    ts: TraceStore, *, days_old: float, trace_id_hint: str = ""
) -> str:
    """Create a trace whose started_at is ``days_old`` days before FIXED_NOW.

    The TraceStore doesn't expose a back-date API, so we mutate the
    underlying SQLite row directly for test setup only (tests are the
    exclusive caller of this helper).
    """
    import sqlite3

    trace = ts.create_trace(f"wf-{trace_id_hint}" if trace_id_hint else "wf")
    span = ts.start_span(trace.trace_id, span_type="step", name="s1", attributes={})
    ts.finish_span(span.span_id, status="ok")
    ts.finish_trace(trace.trace_id, status="ok")

    started = (FIXED_NOW - timedelta(days=days_old)).isoformat()
    ended = started  # good enough — we compare on ended_at or started_at
    conn = sqlite3.connect(ts.path)
    try:
        conn.execute(
            "UPDATE traces SET started_at=?, ended_at=? WHERE trace_id=?",
            (started, ended, trace.trace_id),
        )
        conn.commit()
    finally:
        conn.close()
    return trace.trace_id


def _write_open_trace(ts: TraceStore, *, days_old: float) -> str:
    """Create a trace with started_at back-dated but no ended_at."""
    import sqlite3

    trace = ts.create_trace("wf-open")
    started = (FIXED_NOW - timedelta(days=days_old)).isoformat()
    conn = sqlite3.connect(ts.path)
    try:
        conn.execute(
            "UPDATE traces SET started_at=?, ended_at=NULL, status='running' WHERE trace_id=?",
            (started, trace.trace_id),
        )
        conn.commit()
    finally:
        conn.close()
    return trace.trace_id


def _make_scanner(tmp_path, policy: RetentionPolicy):
    ts = TraceStore(str(tmp_path / "traces.sqlite3"))
    approvals = ApprovalStore()
    scanner = RetentionScanner(
        trace_store=ts, approval_store=approvals, policy=policy
    )
    return scanner, ts, approvals


# ---------------------------------------------------------------------------
# Policy schema
# ---------------------------------------------------------------------------


class TestRetentionPolicy:
    def test_requires_at_least_one_day_windows(self):
        with pytest.raises(ValueError):
            RetentionPolicy(trace_retention_days=0, approval_retention_days=90)
        with pytest.raises(ValueError):
            RetentionPolicy(trace_retention_days=90, approval_retention_days=0)

    def test_defaults_keep_open_and_pending(self):
        p = RetentionPolicy(trace_retention_days=30, approval_retention_days=60)
        assert p.keep_open_traces is True
        assert p.keep_pending_approvals is True

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValueError):
            RetentionPolicy(
                trace_retention_days=30,
                approval_retention_days=60,
                rogue=True,  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Empty / basic
# ---------------------------------------------------------------------------


class TestEmptyScan:
    def test_empty_stores_yield_empty_report(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, _ts, _ap = _make_scanner(tmp_path, policy)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert isinstance(report, RetentionReport)
        assert report.candidates == []
        assert report.totals.traces_scanned == 0
        assert report.totals.approvals_scanned == 0
        assert report.totals.trace_candidates == 0
        assert report.totals.approval_candidates == 0
        assert report.policy == policy
        assert report.evaluation_time == FIXED_NOW


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------


class TestTraceRetention:
    def test_fresh_trace_is_not_candidate(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, ts, _ap = _make_scanner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=5)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.traces_scanned == 1
        assert report.totals.trace_candidates == 0
        assert report.candidates == []

    def test_expired_trace_becomes_candidate(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, ts, _ap = _make_scanner(tmp_path, policy)
        tid = _write_trace_with_age(ts, days_old=45)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.trace_candidates == 1
        candidate = report.candidates[0]
        assert candidate.kind == "trace"
        assert candidate.record_id == tid
        assert candidate.retention_days == 30
        assert candidate.age_days == pytest.approx(45.0, abs=0.01)
        assert "retention window 30d" in candidate.reason

    def test_trace_exactly_at_boundary_is_not_candidate(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, ts, _ap = _make_scanner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=30)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        # age == retention window → not strictly older → not a candidate.
        assert report.totals.trace_candidates == 0

    def test_open_trace_protected_by_default(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, ts, _ap = _make_scanner(tmp_path, policy)
        _write_open_trace(ts, days_old=90)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.traces_scanned == 1
        assert report.totals.trace_candidates == 0

    def test_open_trace_surfaced_when_policy_disables_protection(self, tmp_path):
        policy = RetentionPolicy(
            trace_retention_days=30,
            approval_retention_days=30,
            keep_open_traces=False,
        )
        scanner, ts, _ap = _make_scanner(tmp_path, policy)
        tid = _write_open_trace(ts, days_old=90)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.trace_candidates == 1
        assert report.candidates[0].record_id == tid


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


class TestApprovalRetention:
    def test_fresh_approval_is_not_candidate(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=60)
        scanner, _ts, approvals = _make_scanner(tmp_path, policy)
        approvals.create_request(
            _make_approval(
                approval_id="a1",
                requested_at=FIXED_NOW - timedelta(days=10),
                status=ApprovalStatus.APPROVED,
            )
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.approvals_scanned == 1
        assert report.totals.approval_candidates == 0

    def test_expired_approval_becomes_candidate(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=60)
        scanner, _ts, approvals = _make_scanner(tmp_path, policy)
        approvals.create_request(
            _make_approval(
                approval_id="old",
                requested_at=FIXED_NOW - timedelta(days=120),
                status=ApprovalStatus.APPROVED,
            )
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.approval_candidates == 1
        candidate = report.candidates[0]
        assert candidate.kind == "approval"
        assert candidate.record_id == "old"
        assert candidate.retention_days == 60

    def test_pending_approval_protected_by_default(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, _ts, approvals = _make_scanner(tmp_path, policy)
        approvals.create_request(
            _make_approval(
                approval_id="pending-forever",
                requested_at=FIXED_NOW - timedelta(days=365),
                status=ApprovalStatus.PENDING,
            )
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.approvals_scanned == 1
        assert report.totals.approval_candidates == 0

    def test_pending_approval_surfaced_when_policy_disables_protection(self, tmp_path):
        policy = RetentionPolicy(
            trace_retention_days=30,
            approval_retention_days=30,
            keep_pending_approvals=False,
        )
        scanner, _ts, approvals = _make_scanner(tmp_path, policy)
        approvals.create_request(
            _make_approval(
                approval_id="pending-too-old",
                requested_at=FIXED_NOW - timedelta(days=365),
                status=ApprovalStatus.PENDING,
            )
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.approval_candidates == 1


# ---------------------------------------------------------------------------
# Combined + schema
# ---------------------------------------------------------------------------


class TestCombined:
    def test_traces_and_approvals_reported_together(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=10, approval_retention_days=20)
        scanner, ts, approvals = _make_scanner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=15, trace_id_hint="old-trace")
        _write_trace_with_age(ts, days_old=5, trace_id_hint="fresh-trace")
        approvals.create_request(
            _make_approval(
                approval_id="old-approval",
                requested_at=FIXED_NOW - timedelta(days=30),
                status=ApprovalStatus.REJECTED,
            )
        )
        approvals.create_request(
            _make_approval(
                approval_id="fresh-approval",
                requested_at=FIXED_NOW - timedelta(days=5),
                status=ApprovalStatus.APPROVED,
            )
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.trace_candidates == 1
        assert report.totals.approval_candidates == 1
        kinds = {c.kind: c.record_id for c in report.candidates}
        assert kinds["approval"] == "old-approval"
        assert kinds["trace"]  # trace id generated by store — just assert presence


class TestSchemaHardening:
    def test_candidate_extra_forbid(self):
        with pytest.raises(ValueError):
            RetentionCandidate(
                kind="trace",
                record_id="t",
                age_days=50.0,
                retention_days=30,
                reason="x",
                rogue=True,  # type: ignore[call-arg]
            )

    def test_report_extra_forbid(self):
        from core.audit.retention import RetentionTotals

        with pytest.raises(ValueError):
            RetentionReport(
                generated_at=FIXED_NOW,
                evaluation_time=FIXED_NOW,
                policy=RetentionPolicy(
                    trace_retention_days=30, approval_retention_days=30
                ),
                trace_limit=10,
                candidates=[],
                totals=RetentionTotals(
                    traces_scanned=0,
                    approvals_scanned=0,
                    trace_candidates=0,
                    approval_candidates=0,
                ),
                rogue=True,  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Evaluation-time injection
# ---------------------------------------------------------------------------


class TestEvaluationTime:
    def test_what_if_future_evaluation_increases_candidates(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, ts, _ap = _make_scanner(tmp_path, policy)
        _write_trace_with_age(ts, days_old=20)
        now_report = scanner.scan(evaluation_time=FIXED_NOW)
        assert now_report.totals.trace_candidates == 0
        future_report = scanner.scan(evaluation_time=FIXED_NOW + timedelta(days=30))
        assert future_report.totals.trace_candidates == 1


class TestDecisionRecordedApproval:
    """Covers the realistic path where an approval was decided and later aged out."""

    def test_decided_approval_can_age_out(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        scanner, _ts, approvals = _make_scanner(tmp_path, policy)
        approvals.create_request(
            _make_approval(
                approval_id="decided",
                requested_at=FIXED_NOW - timedelta(days=90),
                status=ApprovalStatus.PENDING,
            )
        )
        _record_approval_decision(approvals, "decided", ApprovalStatus.APPROVED)
        report = scanner.scan(evaluation_time=FIXED_NOW)
        assert report.totals.approval_candidates == 1
        assert report.candidates[0].record_id == "decided"
