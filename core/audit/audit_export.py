"""Standardized audit export — read-only bundle over trace + approval stores.

Closes §6.1 Sicherheit task *"standardisierte Audit-Exports"* with a single
canonical module that reads from the two canonical audit-bearing stores:

- ``TraceStore`` — single source of truth for traces / spans / events.
- ``ApprovalStore`` — single source of truth for approval requests and
  decisions.

The exporter is strictly **read-only**:

- no writes to either store;
- no second audit log;
- no ownership of the production routing / governance / execution path;
- no business logic beyond flattening and filtering.

Output is a ``AuditExport`` Pydantic model with a frozen
``schema_version`` so downstream consumers (forensics, compliance reports,
long-term archive) can version their parsers. Optional ``since`` / ``until``
time windows and workflow / approval-status filters scope the export.

Stdlib + pydantic only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.approval.models import ApprovalRequest, ApprovalStatus, CapabilityRisk
from core.approval.store import ApprovalStore
from core.audit.trace_models import TraceRecord
from core.audit.trace_store import TraceStore

AUDIT_EXPORT_SCHEMA_VERSION = "1.0.0"


class TraceExportEntry(BaseModel):
    """Flat per-trace summary for export bundles."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    workflow_name: str
    task_id: str | None = None
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    span_count: int = Field(ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class ApprovalExportEntry(BaseModel):
    """Flat per-approval summary for export bundles."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str
    plan_id: str
    step_id: str
    agent_id: str | None = None
    status: ApprovalStatus
    risk: CapabilityRisk
    reason: str
    requested_at: datetime
    task_summary: str
    proposed_action_summary: str


class AuditExport(BaseModel):
    """Canonical standardized audit export bundle."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(
        description="Semantic version of this export schema — consumers should pin it"
    )
    generated_at: datetime
    since: datetime | None = None
    until: datetime | None = None
    workflow_filter: str | None = None
    approval_status_filter: ApprovalStatus | None = None
    trace_limit: int = Field(ge=0)
    traces: list[TraceExportEntry] = Field(default_factory=list)
    approvals: list[ApprovalExportEntry] = Field(default_factory=list)


class AuditExporter:
    """Build standardized ``AuditExport`` bundles from the canonical stores.

    Parameters
    ----------
    trace_store:
        Canonical ``TraceStore`` — read-only usage (``list_recent_traces``
        + ``get_trace`` for span counts).
    approval_store:
        Canonical ``ApprovalStore`` — read-only usage (``snapshot``).
    include_span_counts:
        When ``True`` (default), each exported trace carries its
        ``span_count`` computed from ``get_trace``.  Set ``False`` to skip
        per-trace fetches for very large windows.
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        approval_store: ApprovalStore,
        include_span_counts: bool = True,
    ) -> None:
        self.trace_store = trace_store
        self.approval_store = approval_store
        self.include_span_counts = include_span_counts

    def export(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        workflow_filter: str | None = None,
        approval_status_filter: ApprovalStatus | None = None,
        trace_limit: int = 10_000,
    ) -> AuditExport:
        """Build a filtered, standardized audit export bundle.

        Parameters
        ----------
        since / until:
            Closed time window on ``started_at`` for traces and
            ``requested_at`` for approvals.  ``None`` means "no bound on
            that side".  A trace whose ``started_at`` equals ``since`` is
            included.
        workflow_filter:
            When set, only traces whose ``workflow_name`` matches are
            exported.  Does not filter approvals (they are plan-scoped).
        approval_status_filter:
            When set, only approvals with that status are exported.
        trace_limit:
            Cap on how many recent traces to scan.  Default 10 000 — plenty
            for normal audit windows; set higher for bulk archive exports.
        """
        traces = self._collect_traces(
            since=since,
            until=until,
            workflow_filter=workflow_filter,
            trace_limit=trace_limit,
        )
        approvals = self._collect_approvals(
            since=since,
            until=until,
            approval_status_filter=approval_status_filter,
        )
        return AuditExport(
            schema_version=AUDIT_EXPORT_SCHEMA_VERSION,
            generated_at=datetime.now(UTC),
            since=since,
            until=until,
            workflow_filter=workflow_filter,
            approval_status_filter=approval_status_filter,
            trace_limit=trace_limit,
            traces=traces,
            approvals=approvals,
        )

    def _collect_traces(
        self,
        *,
        since: datetime | None,
        until: datetime | None,
        workflow_filter: str | None,
        trace_limit: int,
    ) -> list[TraceExportEntry]:
        raw = self.trace_store.list_recent_traces(limit=trace_limit)
        entries: list[TraceExportEntry] = []
        for trace in raw:
            if not _in_window(trace.started_at, since, until):
                continue
            if workflow_filter is not None and trace.workflow_name != workflow_filter:
                continue
            entries.append(self._entry_from_trace(trace))
        entries.sort(key=lambda e: (e.started_at, e.trace_id))
        return entries

    def _entry_from_trace(self, trace: TraceRecord) -> TraceExportEntry:
        span_count = 0
        if self.include_span_counts:
            snapshot = self.trace_store.get_trace(trace.trace_id)
            if snapshot is not None:
                span_count = len(snapshot.spans)
        return TraceExportEntry(
            trace_id=trace.trace_id,
            workflow_name=trace.workflow_name,
            task_id=trace.task_id,
            status=trace.status,
            started_at=trace.started_at,
            ended_at=trace.ended_at,
            span_count=span_count,
            metadata=dict(trace.metadata),
        )

    def _collect_approvals(
        self,
        *,
        since: datetime | None,
        until: datetime | None,
        approval_status_filter: ApprovalStatus | None,
    ) -> list[ApprovalExportEntry]:
        entries: list[ApprovalExportEntry] = []
        for request in self.approval_store.snapshot():
            if not _in_window(request.requested_at, since, until):
                continue
            if approval_status_filter is not None and request.status != approval_status_filter:
                continue
            entries.append(_entry_from_approval(request))
        return entries


def _entry_from_approval(request: ApprovalRequest) -> ApprovalExportEntry:
    return ApprovalExportEntry(
        approval_id=request.approval_id,
        plan_id=request.plan_id,
        step_id=request.step_id,
        agent_id=request.agent_id,
        status=request.status,
        risk=request.risk,
        reason=request.reason,
        requested_at=request.requested_at,
        task_summary=request.task_summary,
        proposed_action_summary=request.proposed_action_summary,
    )


def _in_window(
    ts: datetime | None,
    since: datetime | None,
    until: datetime | None,
) -> bool:
    if ts is None:
        return False
    if since is not None and ts < since:
        return False
    if until is not None and ts > until:
        return False
    return True


__all__ = [
    "AUDIT_EXPORT_SCHEMA_VERSION",
    "ApprovalExportEntry",
    "AuditExport",
    "AuditExporter",
    "TraceExportEntry",
]
