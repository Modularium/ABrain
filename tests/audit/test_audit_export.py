"""§6.1 Sicherheit — AuditExporter tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.approval.models import ApprovalRequest, ApprovalStatus, CapabilityRisk
from core.approval.store import ApprovalStore
from core.audit.audit_export import (
    AUDIT_EXPORT_SCHEMA_VERSION,
    ApprovalExportEntry,
    AuditExport,
    AuditExporter,
    TraceExportEntry,
)
from core.audit.trace_store import TraceStore

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_approval(
    *,
    approval_id: str,
    plan_id: str = "plan-1",
    step_id: str = "step-1",
    agent_id: str | None = "agent-1",
    reason: str = "needs review",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
    requested_at: datetime | None = None,
    task_summary: str = "task",
    proposed_action_summary: str = "action",
) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=approval_id,
        plan_id=plan_id,
        step_id=step_id,
        agent_id=agent_id,
        reason=reason,
        risk=risk,
        requested_at=requested_at or datetime.now(UTC),
        task_summary=task_summary,
        proposed_action_summary=proposed_action_summary,
    )


def _write_trace(
    ts: TraceStore,
    *,
    workflow: str = "wf",
    status: str = "ok",
    with_span: bool = True,
) -> str:
    trace = ts.create_trace(workflow)
    if with_span:
        span = ts.start_span(trace.trace_id, span_type="step", name="s1", attributes={})
        ts.finish_span(span.span_id, status="ok")
    ts.finish_trace(trace.trace_id, status=status)
    return trace.trace_id


def _make_exporter(tmp_path, **kwargs):
    ts = TraceStore(str(tmp_path / "traces.sqlite3"))
    approvals = ApprovalStore()
    return AuditExporter(trace_store=ts, approval_store=approvals, **kwargs), ts, approvals


# ---------------------------------------------------------------------------
# Store snapshot accessor
# ---------------------------------------------------------------------------


class TestApprovalStoreSnapshot:
    def test_snapshot_orders_by_requested_at(self):
        store = ApprovalStore()
        t0 = datetime.now(UTC)
        store.create_request(_make_approval(approval_id="a2", requested_at=t0 + timedelta(seconds=1)))
        store.create_request(_make_approval(approval_id="a1", requested_at=t0))
        snap = store.snapshot()
        assert [r.approval_id for r in snap] == ["a1", "a2"]


# ---------------------------------------------------------------------------
# Empty / schema
# ---------------------------------------------------------------------------


class TestEmptyExport:
    def test_empty_stores_yield_empty_bundle(self, tmp_path):
        exporter, _ts, _ap = _make_exporter(tmp_path)
        export = exporter.export()
        assert isinstance(export, AuditExport)
        assert export.schema_version == AUDIT_EXPORT_SCHEMA_VERSION
        assert export.traces == []
        assert export.approvals == []
        assert export.since is None and export.until is None

    def test_schema_version_is_stable(self):
        assert AUDIT_EXPORT_SCHEMA_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------


class TestTraceExport:
    def test_traces_are_surfaced_with_span_count(self, tmp_path):
        exporter, ts, _ap = _make_exporter(tmp_path)
        tid = _write_trace(ts, workflow="wf-a")
        export = exporter.export()
        assert len(export.traces) == 1
        entry = export.traces[0]
        assert entry.trace_id == tid
        assert entry.workflow_name == "wf-a"
        assert entry.span_count == 1
        assert entry.status == "ok"

    def test_workflow_filter_only_exports_matching_traces(self, tmp_path):
        exporter, ts, _ap = _make_exporter(tmp_path)
        _write_trace(ts, workflow="wf-keep")
        _write_trace(ts, workflow="wf-skip")
        export = exporter.export(workflow_filter="wf-keep")
        assert len(export.traces) == 1
        assert export.traces[0].workflow_name == "wf-keep"
        assert export.workflow_filter == "wf-keep"

    def test_time_window_bounds_traces(self, tmp_path):
        exporter, ts, _ap = _make_exporter(tmp_path)
        before = datetime.now(UTC) - timedelta(hours=1)
        _write_trace(ts, workflow="wf")
        # until in the past → no traces.
        export = exporter.export(until=before)
        assert export.traces == []
        # since in the past → includes current traces.
        export = exporter.export(since=before)
        assert len(export.traces) == 1

    def test_span_count_can_be_disabled(self, tmp_path):
        exporter, ts, _ap = _make_exporter(tmp_path, include_span_counts=False)
        _write_trace(ts, with_span=True)
        export = exporter.export()
        # span_count skipped → zero.
        assert export.traces[0].span_count == 0

    def test_traces_sorted_by_started_at(self, tmp_path):
        exporter, ts, _ap = _make_exporter(tmp_path)
        ids = [_write_trace(ts, workflow=f"wf-{i}") for i in range(3)]
        export = exporter.export()
        exported_ids = [e.trace_id for e in export.traces]
        assert sorted(exported_ids) == sorted(ids)
        # Sorted ascending by started_at (ties broken by trace_id).
        started = [e.started_at for e in export.traces]
        assert started == sorted(started)


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


class TestApprovalExport:
    def test_all_approvals_surfaced_by_default(self, tmp_path):
        exporter, _ts, approvals = _make_exporter(tmp_path)
        approvals.create_request(_make_approval(approval_id="a1"))
        approvals.create_request(_make_approval(approval_id="a2"))
        export = exporter.export()
        ids = {a.approval_id for a in export.approvals}
        assert ids == {"a1", "a2"}

    def test_status_filter(self, tmp_path):
        exporter, _ts, approvals = _make_exporter(tmp_path)
        approvals.create_request(_make_approval(approval_id="a1"))
        approved = _make_approval(approval_id="a2")
        approvals.create_request(approved)
        from core.approval.models import ApprovalDecision

        approvals.record_decision(
            "a2",
            ApprovalDecision(
                approval_id="a2",
                decision=ApprovalStatus.APPROVED,
                decided_by="admin",
                decided_at=datetime.now(UTC),
            ),
        )
        export = exporter.export(approval_status_filter=ApprovalStatus.APPROVED)
        assert [a.approval_id for a in export.approvals] == ["a2"]
        assert export.approvals[0].status == ApprovalStatus.APPROVED
        assert export.approval_status_filter == ApprovalStatus.APPROVED

    def test_approval_time_window(self, tmp_path):
        exporter, _ts, approvals = _make_exporter(tmp_path)
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        approvals.create_request(_make_approval(approval_id="old", requested_at=t0))
        approvals.create_request(
            _make_approval(approval_id="new", requested_at=t0 + timedelta(days=30))
        )
        export = exporter.export(since=t0 + timedelta(days=10))
        assert [a.approval_id for a in export.approvals] == ["new"]

    def test_approval_fields_round_trip(self, tmp_path):
        exporter, _ts, approvals = _make_exporter(tmp_path)
        approvals.create_request(
            _make_approval(
                approval_id="a1",
                plan_id="plan-7",
                step_id="step-3",
                agent_id="engineer-bot",
                reason="requires sign-off",
                risk=CapabilityRisk.HIGH,
                task_summary="deploy fix",
                proposed_action_summary="apply patch to prod",
            )
        )
        export = exporter.export()
        assert len(export.approvals) == 1
        a = export.approvals[0]
        assert a.plan_id == "plan-7"
        assert a.step_id == "step-3"
        assert a.agent_id == "engineer-bot"
        assert a.risk == CapabilityRisk.HIGH
        assert a.reason == "requires sign-off"
        assert a.task_summary == "deploy fix"
        assert a.proposed_action_summary == "apply patch to prod"


# ---------------------------------------------------------------------------
# Schema hardening
# ---------------------------------------------------------------------------


class TestSchemaHardening:
    def test_audit_export_extra_forbid(self):
        with pytest.raises(ValueError):
            AuditExport(
                schema_version=AUDIT_EXPORT_SCHEMA_VERSION,
                generated_at=datetime.now(UTC),
                trace_limit=10,
                rogue="nope",  # type: ignore[call-arg]
            )

    def test_trace_entry_extra_forbid(self):
        with pytest.raises(ValueError):
            TraceExportEntry(
                trace_id="t",
                workflow_name="wf",
                status="ok",
                started_at=datetime.now(UTC),
                span_count=0,
                rogue="nope",  # type: ignore[call-arg]
            )

    def test_approval_entry_extra_forbid(self):
        with pytest.raises(ValueError):
            ApprovalExportEntry(
                approval_id="a",
                plan_id="p",
                step_id="s",
                status=ApprovalStatus.PENDING,
                risk=CapabilityRisk.LOW,
                reason="r",
                requested_at=datetime.now(UTC),
                task_summary="t",
                proposed_action_summary="x",
                rogue="nope",  # type: ignore[call-arg]
            )
