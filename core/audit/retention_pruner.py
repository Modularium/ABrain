"""Retention pruner — destructive half of the §6.4 retention concept.

Consumes a ``RetentionReport`` produced by ``RetentionScanner`` and
deletes the candidate records from ``TraceStore`` / ``ApprovalStore``.

The pruner defaults to **dry-run**: calling ``prune(report)`` without
``commit=True`` returns the same accounting that a real prune would
produce, but touches no store.  Operators inspect the planned deletions
against the scanner's candidate list before flipping the switch.

Deliberately scope-narrow:

- the report is the **only** source of truth for which records go;
- no policy re-evaluation happens here — the scanner already decided;
- one pass per kind, no retries, no partial-failure recovery logic;
- no audit-log write from the pruner itself: the caller owns the
  operator audit trail (``audit_action`` or a governance surface), so
  the pruner stays a pure destructive primitive that does not grow a
  second audit stack.

Stdlib + pydantic only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.approval.store import ApprovalStore
from core.audit.retention import RetentionCandidate, RetentionKind, RetentionReport
from core.audit.trace_store import TraceStore


class RetentionPruneOutcome(BaseModel):
    """Per-candidate outcome of a prune pass."""

    model_config = ConfigDict(extra="forbid")

    kind: RetentionKind
    record_id: str
    deleted: bool = Field(
        description="True if the record was removed from its store. False means the record was already absent (dry-run, or concurrent deletion)."
    )
    dry_run: bool


class RetentionPruneResult(BaseModel):
    """Aggregate result of a ``RetentionPruner.prune`` call."""

    model_config = ConfigDict(extra="forbid")

    executed_at: datetime
    dry_run: bool
    trace_candidates: int = Field(ge=0)
    approval_candidates: int = Field(ge=0)
    traces_deleted: int = Field(ge=0)
    approvals_deleted: int = Field(ge=0)
    outcomes: list[RetentionPruneOutcome] = Field(default_factory=list)


class RetentionPruner:
    """Delete overdue candidates produced by ``RetentionScanner``.

    Parameters
    ----------
    trace_store:
        Canonical ``TraceStore``.  ``delete_trace`` is invoked once per
        trace candidate.
    approval_store:
        Canonical ``ApprovalStore``.  ``delete_request`` is invoked once
        per approval candidate.
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        approval_store: ApprovalStore,
    ) -> None:
        self.trace_store = trace_store
        self.approval_store = approval_store

    def prune(
        self,
        report: RetentionReport,
        *,
        commit: bool = False,
    ) -> RetentionPruneResult:
        """Delete every candidate in ``report``.

        Parameters
        ----------
        report:
            The ``RetentionReport`` to act on.  The pruner trusts the
            report — it does not re-evaluate policy.
        commit:
            ``False`` (default) → dry-run: the result lists what would
            be deleted but no store is modified.
            ``True`` → destructive: each candidate is removed.
        """
        dry_run = not commit
        outcomes: list[RetentionPruneOutcome] = []
        traces_deleted = 0
        approvals_deleted = 0
        trace_candidates = 0
        approval_candidates = 0

        for candidate in report.candidates:
            if candidate.kind == "trace":
                trace_candidates += 1
                deleted = self._handle_trace(candidate, dry_run=dry_run)
                if deleted:
                    traces_deleted += 1
                outcomes.append(
                    RetentionPruneOutcome(
                        kind="trace",
                        record_id=candidate.record_id,
                        deleted=deleted,
                        dry_run=dry_run,
                    )
                )
            elif candidate.kind == "approval":
                approval_candidates += 1
                deleted = self._handle_approval(candidate, dry_run=dry_run)
                if deleted:
                    approvals_deleted += 1
                outcomes.append(
                    RetentionPruneOutcome(
                        kind="approval",
                        record_id=candidate.record_id,
                        deleted=deleted,
                        dry_run=dry_run,
                    )
                )

        return RetentionPruneResult(
            executed_at=datetime.now(UTC),
            dry_run=dry_run,
            trace_candidates=trace_candidates,
            approval_candidates=approval_candidates,
            traces_deleted=traces_deleted,
            approvals_deleted=approvals_deleted,
            outcomes=outcomes,
        )

    def _handle_trace(
        self,
        candidate: RetentionCandidate,
        *,
        dry_run: bool,
    ) -> bool:
        if dry_run:
            return self.trace_store.get_trace(candidate.record_id) is not None
        return self.trace_store.delete_trace(candidate.record_id)

    def _handle_approval(
        self,
        candidate: RetentionCandidate,
        *,
        dry_run: bool,
    ) -> bool:
        if dry_run:
            return self.approval_store.get_request(candidate.record_id) is not None
        return self.approval_store.delete_request(candidate.record_id)


__all__ = [
    "RetentionPruneOutcome",
    "RetentionPruneResult",
    "RetentionPruner",
]
