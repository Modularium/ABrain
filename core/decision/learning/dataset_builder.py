"""DatasetBuilder – assembles LearningRecords from TraceStore + ApprovalStore.

Reads completed traces (with explainability records) and joins approval
outcomes where available.  The builder is read-only with respect to both
stores; it never mutates them.

Usage::

    builder = DatasetBuilder(trace_store=ts, approval_store=approvals)
    records = builder.build(limit=500)
"""

from __future__ import annotations

from core.approval.store import ApprovalStore
from core.audit.trace_store import TraceStore

from .record import LearningRecord


class DatasetBuilder:
    """Construct offline training records from operational store snapshots.

    Parameters
    ----------
    trace_store:
        The canonical TraceStore instance.
    approval_store:
        The canonical ApprovalStore instance.  Pass ``None`` to build
        records without approval signals.
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        approval_store: ApprovalStore | None = None,
    ) -> None:
        self._traces = trace_store
        self._approvals = approval_store

    def build(self, limit: int = 1000) -> list[LearningRecord]:
        """Return up to *limit* LearningRecords ordered newest-first."""
        if limit <= 0:
            raise ValueError("limit must be positive")
        trace_records = self._traces.list_recent_traces(limit)
        records: list[LearningRecord] = []
        for trace in trace_records:
            snapshot = self._traces.get_trace(trace.trace_id)
            if snapshot is None:
                continue
            record = self._build_record(snapshot)
            records.append(record)
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_record(self, snapshot) -> LearningRecord:  # TraceSnapshot
        trace = snapshot.trace
        explainability = snapshot.explainability  # list[ExplainabilityRecord]

        # Pick the first (primary) routing decision if present.
        primary = explainability[0] if explainability else None

        has_routing = primary is not None
        approval_id = primary.approval_id if primary else None

        # Resolve approval outcome from ApprovalStore.
        approval_decision: str | None = None
        has_approval_outcome = False
        if approval_id and self._approvals:
            req = self._approvals.get_request(approval_id)
            if req is not None:
                approval_decision = str(req.status)
                # "approved", "rejected", "expired", "cancelled" are resolved.
                has_approval_outcome = approval_decision != "pending"

        # Resolve execution outcome from trace metadata.
        meta = trace.metadata or {}
        success_raw = meta.get("success")
        success: bool | None = bool(success_raw) if success_raw is not None else None
        cost_usd: float | None = _try_float(meta.get("cost_usd") or meta.get("cost"))
        latency_ms: float | None = _try_float(meta.get("latency_ms") or meta.get("duration_ms"))
        has_outcome = success is not None

        # Collect candidate agent IDs across all routing steps.
        all_candidate_ids: list[str] = []
        all_policy_ids: list[str] = []
        if primary:
            all_candidate_ids = list(primary.candidate_agent_ids)
            all_policy_ids = list(primary.matched_policy_ids)

        return LearningRecord(
            trace_id=trace.trace_id,
            workflow_name=trace.workflow_name,
            task_type=meta.get("task_type"),
            task_id=trace.task_id,
            started_at=trace.started_at.isoformat() if trace.started_at else None,
            ended_at=trace.ended_at.isoformat() if trace.ended_at else None,
            trace_status=trace.status,
            # Routing
            selected_agent_id=primary.selected_agent_id if primary else None,
            candidate_agent_ids=all_candidate_ids,
            selected_score=primary.selected_score if primary else None,
            routing_confidence=primary.routing_confidence if primary else None,
            score_gap=primary.score_gap if primary else None,
            confidence_band=primary.confidence_band if primary else None,
            policy_effect=primary.policy_effect if primary else None,
            matched_policy_ids=all_policy_ids,
            approval_required=primary.approval_required if primary else False,
            # Approval
            approval_id=approval_id,
            approval_decision=approval_decision,
            # Outcome
            success=success,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            # Metadata passthrough (strip already-extracted keys to avoid duplication)
            metadata={
                k: v
                for k, v in meta.items()
                if k not in {"task_type", "success", "cost_usd", "cost", "latency_ms", "duration_ms"}
            },
            # Quality flags
            has_routing_decision=has_routing,
            has_outcome=has_outcome,
            has_approval_outcome=has_approval_outcome,
        )


def _try_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
