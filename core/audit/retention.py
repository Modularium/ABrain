"""Retention scanner — read-only deletion-candidate report.

Closes the first §6.4 Data Governance task
*"Retention- und Löschkonzept"* with a single canonical read-only surface
that reports overdue deletion candidates in ``TraceStore`` and
``ApprovalStore`` based on a frozen ``RetentionPolicy``.

This turn is **strictly observational** — no record is deleted here.
Phase N explicitly left TTL / pruning as a later concern
(``docs/architecture/PERSISTENT_STATE_AND_DURABLE_RUNTIME.md``); this
scanner produces the candidate list that a future pruner would operate
on. That separation is deliberate:

- the policy surface (what counts as overdue) becomes reviewable on its
  own, independent of any destructive action;
- operators can dry-run a retention window, see what would be deleted,
  and adjust the policy before any pruning step is wired.

Strictly read-only:

- no writes to either store;
- no second trace / approval log;
- no ownership of routing / governance / approval / execution paths;
- no hidden side-effects — only pure projection + threshold comparison.

Stdlib + pydantic only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.approval.models import ApprovalRequest, ApprovalStatus
from core.approval.store import ApprovalStore
from core.audit.trace_models import TraceRecord
from core.audit.trace_store import TraceStore

RetentionKind = Literal["trace", "approval"]


class RetentionPolicy(BaseModel):
    """Frozen retention policy — how long each record kind may be kept.

    Both retention windows are in **days** and must be at least ``1``.
    The scanner compares each record's age (at evaluation time) against
    the applicable window and flags records strictly older than it.
    """

    model_config = ConfigDict(extra="forbid")

    trace_retention_days: int = Field(
        ge=1,
        description="Max age in days for a trace record before it becomes a deletion candidate.",
    )
    approval_retention_days: int = Field(
        ge=1,
        description="Max age in days for an approval record before it becomes a deletion candidate.",
    )
    keep_open_traces: bool = Field(
        default=True,
        description="When True, traces without ``ended_at`` are never candidates regardless of age.",
    )
    keep_pending_approvals: bool = Field(
        default=True,
        description="When True, approvals with status=PENDING are never candidates regardless of age.",
    )


class RetentionCandidate(BaseModel):
    """One overdue deletion candidate."""

    model_config = ConfigDict(extra="forbid")

    kind: RetentionKind
    record_id: str
    age_days: float = Field(ge=0.0)
    retention_days: int = Field(ge=1)
    reason: str


class RetentionTotals(BaseModel):
    """Aggregate counts for a retention report."""

    model_config = ConfigDict(extra="forbid")

    traces_scanned: int = Field(ge=0)
    approvals_scanned: int = Field(ge=0)
    trace_candidates: int = Field(ge=0)
    approval_candidates: int = Field(ge=0)


class RetentionReport(BaseModel):
    """Scanner output: overdue candidates grouped with policy context."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    evaluation_time: datetime = Field(
        description="Reference 'now' used to compute record age — injected for determinism in tests."
    )
    policy: RetentionPolicy
    trace_limit: int = Field(ge=0)
    candidates: list[RetentionCandidate] = Field(default_factory=list)
    totals: RetentionTotals


class RetentionScanner:
    """Scan ``TraceStore`` + ``ApprovalStore`` for overdue retention candidates.

    Parameters
    ----------
    trace_store:
        Canonical ``TraceStore``.  Read-only usage
        (``list_recent_traces``).
    approval_store:
        Canonical ``ApprovalStore``.  Read-only usage (``snapshot``).
    policy:
        Frozen ``RetentionPolicy`` instance.
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        approval_store: ApprovalStore,
        policy: RetentionPolicy,
    ) -> None:
        self.trace_store = trace_store
        self.approval_store = approval_store
        self.policy = policy

    def scan(
        self,
        *,
        evaluation_time: datetime | None = None,
        trace_limit: int = 10_000,
    ) -> RetentionReport:
        """Produce a retention candidate report.

        Parameters
        ----------
        evaluation_time:
            Reference timestamp treated as "now" for age computation.
            ``None`` → ``datetime.now(UTC)``.  Inject a fixed value for
            deterministic tests or historical what-if evaluation.
        trace_limit:
            Cap on how many recent traces to scan.  Default 10 000.
        """
        now = evaluation_time or datetime.now(UTC)

        traces = self.trace_store.list_recent_traces(limit=trace_limit)
        approvals = self.approval_store.snapshot()

        candidates: list[RetentionCandidate] = []
        trace_candidate_count = 0
        approval_candidate_count = 0

        trace_cutoff = timedelta(days=self.policy.trace_retention_days)
        approval_cutoff = timedelta(days=self.policy.approval_retention_days)

        for trace in traces:
            candidate = self._evaluate_trace(trace, now=now, cutoff=trace_cutoff)
            if candidate is not None:
                candidates.append(candidate)
                trace_candidate_count += 1

        for request in approvals:
            candidate = self._evaluate_approval(
                request, now=now, cutoff=approval_cutoff
            )
            if candidate is not None:
                candidates.append(candidate)
                approval_candidate_count += 1

        return RetentionReport(
            generated_at=datetime.now(UTC),
            evaluation_time=now,
            policy=self.policy,
            trace_limit=trace_limit,
            candidates=candidates,
            totals=RetentionTotals(
                traces_scanned=len(traces),
                approvals_scanned=len(approvals),
                trace_candidates=trace_candidate_count,
                approval_candidates=approval_candidate_count,
            ),
        )

    def _evaluate_trace(
        self,
        trace: TraceRecord,
        *,
        now: datetime,
        cutoff: timedelta,
    ) -> RetentionCandidate | None:
        if self.policy.keep_open_traces and trace.ended_at is None:
            return None
        reference = trace.ended_at or trace.started_at
        age = now - reference
        if age <= cutoff:
            return None
        return RetentionCandidate(
            kind="trace",
            record_id=trace.trace_id,
            age_days=_days(age),
            retention_days=self.policy.trace_retention_days,
            reason=(
                f"trace age {_days(age):.2f}d > retention window "
                f"{self.policy.trace_retention_days}d"
            ),
        )

    def _evaluate_approval(
        self,
        request: ApprovalRequest,
        *,
        now: datetime,
        cutoff: timedelta,
    ) -> RetentionCandidate | None:
        if (
            self.policy.keep_pending_approvals
            and request.status == ApprovalStatus.PENDING
        ):
            return None
        age = now - request.requested_at
        if age <= cutoff:
            return None
        return RetentionCandidate(
            kind="approval",
            record_id=request.approval_id,
            age_days=_days(age),
            retention_days=self.policy.approval_retention_days,
            reason=(
                f"approval age {_days(age):.2f}d > retention window "
                f"{self.policy.approval_retention_days}d"
            ),
        )


def _days(delta: timedelta) -> float:
    return delta.total_seconds() / 86400.0


__all__ = [
    "RetentionCandidate",
    "RetentionKind",
    "RetentionPolicy",
    "RetentionReport",
    "RetentionScanner",
    "RetentionTotals",
]
