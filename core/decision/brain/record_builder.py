"""Phase 6 – Brain v1 B6-S2: BrainRecordBuilder.

Converts ``LearningRecord`` objects (Phase 5 LearningOps pipeline) into
``BrainRecord`` training pairs for the Brain decision network.

A ``LearningRecord`` is a post-hoc flat snapshot — it holds routing *results*
but not the full routing *context* (AgentDescriptor list, TaskIntent, etc.).
``BrainRecordBuilder`` therefore builds a best-effort ``BrainRecord``, using
neutral defaults for signals that are not recoverable:

- ``domain`` → "unknown"  (not stored in LearningRecord)
- ``required_capabilities`` → []  (not stored in LearningRecord)
- ``capability_match_score`` → 0.0 for all candidates (not recoverable)
- ``trust_level_ord`` → 0.0  (UNKNOWN ordinal)
- ``availability_ord`` → 0.5  (UNKNOWN ordinal)

Per-agent performance history *is* recoverable when a
``PerformanceHistoryStore`` is provided — it is looked up by ``agent_id``.

Design invariants:
- Read-only: no mutation of input objects.
- Best-effort: conversion errors return ``None`` from ``build``; ``build_batch``
  skips invalid records by default.
- No side effects: does not write to TraceStore, ApprovalStore, or any store.
"""

from __future__ import annotations

from typing import Any

from ..performance_history import PerformanceHistoryStore
from .state import (
    BrainAgentSignal,
    BrainBudget,
    BrainPolicySignals,
    BrainRecord,
    BrainState,
    BrainTarget,
)

# Sentinel ordinals used when descriptor-level data is unavailable.
_TRUST_ORD_UNKNOWN = 0.0
_AVAILABILITY_ORD_UNKNOWN = 0.5  # midpoint — UNKNOWN is between OFFLINE and ONLINE


class BrainRecordBuilder:
    """Convert ``LearningRecord`` objects to ``BrainRecord`` training pairs.

    Parameters
    ----------
    performance_history:
        Optional ``PerformanceHistoryStore``.  When provided, per-agent
        performance signals (success_rate, avg_latency_s, etc.) are read from
        it.  When absent, all agents receive neutral defaults from the empty
        default store.
    require_routing_decision:
        When ``True`` (default), ``build()`` raises ``ValueError`` for records
        where ``has_routing_decision is False`` — such records carry no
        actionable routing signal for Brain training.  Set to ``False`` to
        convert all records regardless.
    """

    def __init__(
        self,
        *,
        performance_history: PerformanceHistoryStore | None = None,
        require_routing_decision: bool = True,
    ) -> None:
        self._history = performance_history or PerformanceHistoryStore()
        self.require_routing_decision = require_routing_decision

    def build(self, record: Any) -> BrainRecord:
        """Convert one ``LearningRecord`` to a ``BrainRecord``.

        Parameters
        ----------
        record:
            A ``LearningRecord`` instance.

        Returns
        -------
        ``BrainRecord`` with state + target derived from the record.

        Raises
        ------
        ``ValueError``
            When ``require_routing_decision=True`` and
            ``record.has_routing_decision is False``.
        """
        if self.require_routing_decision and not record.has_routing_decision:
            raise ValueError(
                f"LearningRecord {record.trace_id!r} has no routing decision "
                "and require_routing_decision=True"
            )
        return BrainRecord(
            trace_id=record.trace_id,
            workflow_name=record.workflow_name,
            state=self._build_state(record),
            target=self._build_target(record),
        )

    def build_batch(
        self,
        records: list[Any],
        *,
        skip_invalid: bool = True,
    ) -> list[BrainRecord]:
        """Batch-convert ``LearningRecord`` objects.

        Parameters
        ----------
        records:
            Sequence of ``LearningRecord`` instances.
        skip_invalid:
            When ``True`` (default), records that raise during conversion are
            silently skipped.  When ``False``, the first error propagates.

        Returns
        -------
        List of successfully converted ``BrainRecord`` objects.
        """
        result: list[BrainRecord] = []
        for record in records:
            if skip_invalid:
                try:
                    result.append(self.build(record))
                except Exception:
                    continue
            else:
                result.append(self.build(record))
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_state(self, record: Any) -> BrainState:
        task_type = record.task_type or "unknown"

        # Policy signals — derive from policy_effect string.
        # Any non-None policy_effect means at least one policy was evaluated.
        has_policy_effect = record.policy_effect is not None
        policy = BrainPolicySignals(
            has_policy_effect=has_policy_effect,
            approval_required=record.approval_required,
            matched_policy_ids=list(record.matched_policy_ids),
        )

        candidates = self._build_agent_signals(record)

        return BrainState(
            task_type=task_type,
            domain="unknown",
            num_required_capabilities=0,
            policy=policy,
            candidates=candidates,
            num_candidates=len(candidates),
            budget=BrainBudget(),
            routing_confidence=record.routing_confidence,
            score_gap=record.score_gap,
            confidence_band=record.confidence_band,
        )

    def _build_target(self, record: Any) -> BrainTarget:
        # Decode approval_granted from the approval_decision string.
        approval_granted: bool | None = None
        if record.has_approval_outcome:
            if record.approval_decision == "approved":
                approval_granted = True
            elif record.approval_decision == "rejected":
                approval_granted = False

        return BrainTarget(
            selected_agent_id=record.selected_agent_id,
            outcome_success=record.success,
            outcome_cost_usd=record.cost_usd,
            outcome_latency_ms=record.latency_ms,
            approval_required=record.approval_required,
            approval_granted=approval_granted,
        )

    def _build_agent_signals(self, record: Any) -> list[BrainAgentSignal]:
        """Build per-agent signals from candidate_agent_ids.

        Ordering: selected agent first (best production decision); all other
        candidates follow in their original order.  If ``selected_agent_id``
        is absent or not in the candidate list, no reordering is applied.

        ``capability_match_score`` is set to 0.0 for all candidates — it is
        not recoverable from a ``LearningRecord``.  The selection signal is
        instead captured in ``BrainTarget.selected_agent_id``.
        """
        agent_ids: list[str] = list(record.candidate_agent_ids)

        # Ensure selected agent is present and placed first.
        selected = record.selected_agent_id
        if selected:
            if selected not in agent_ids:
                agent_ids = [selected] + agent_ids
            elif agent_ids[0] != selected:
                agent_ids = [selected] + [a for a in agent_ids if a != selected]

        signals: list[BrainAgentSignal] = []
        for agent_id in agent_ids:
            history = self._history.get(agent_id)
            signals.append(
                BrainAgentSignal(
                    agent_id=agent_id,
                    capability_match_score=0.0,
                    success_rate=history.success_rate,
                    avg_latency_s=history.avg_latency,
                    avg_cost_usd=history.avg_cost,
                    recent_failures=history.recent_failures,
                    execution_count=history.execution_count,
                    load_factor=history.load_factor,
                    trust_level_ord=_TRUST_ORD_UNKNOWN,
                    availability_ord=_AVAILABILITY_ORD_UNKNOWN,
                )
            )
        return signals
