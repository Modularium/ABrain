"""Phase 6 – Brain v1 B6-S1: BrainStateEncoder.

Converts ABrain routing primitives (``TaskIntent``, ``AgentDescriptor`` list,
``PerformanceHistoryStore``) into a ``BrainState`` ready for the Brain
decision network.

Design constraints:
- Read-only: never mutates any input object.
- No heavy dependencies: only canonical ABrain components.
- Deterministic: same inputs always produce the same ``BrainState``.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..agent_descriptor import AgentAvailability, AgentDescriptor, AgentTrustLevel
from ..performance_history import PerformanceHistoryStore
from ..routing_engine import RoutingDecision
from ..task_intent import TaskIntent
from .state import (
    BrainAgentSignal,
    BrainBudget,
    BrainPolicySignals,
    BrainState,
)

# Ordinal mappings — higher value = more desirable.
_TRUST_ORD: dict[AgentTrustLevel, float] = {
    AgentTrustLevel.UNKNOWN: 0.0,
    AgentTrustLevel.SANDBOXED: 1 / 3,
    AgentTrustLevel.TRUSTED: 2 / 3,
    AgentTrustLevel.PRIVILEGED: 1.0,
}

_AVAILABILITY_ORD: dict[AgentAvailability, float] = {
    AgentAvailability.OFFLINE: 0.0,
    AgentAvailability.DEGRADED: 1 / 3,
    AgentAvailability.UNKNOWN: 0.5,
    AgentAvailability.ONLINE: 1.0,
}


def _capability_match(descriptor: AgentDescriptor, required: list[str]) -> float:
    """Fraction of required capabilities covered by this descriptor."""
    if not required:
        return 1.0
    covered = sum(1 for cap in required if cap in descriptor.capabilities)
    return covered / len(required)


class BrainStateEncoder:
    """Convert ABrain routing primitives to ``BrainState``.

    Parameters
    ----------
    latency_scale_s:
        Divisor for normalising ``avg_latency_s`` into a rough [0,∞) signal.
        Default 10.0 seconds matches the OfflineTrainer feature convention.
    cost_scale_usd:
        Divisor for normalising ``avg_cost_usd``.
        Default 0.01 USD per call.
    """

    def __init__(
        self,
        *,
        latency_scale_s: float = 10.0,
        cost_scale_usd: float = 0.01,
    ) -> None:
        self.latency_scale_s = latency_scale_s
        self.cost_scale_usd = cost_scale_usd

    def encode(
        self,
        intent: TaskIntent,
        descriptors: Sequence[AgentDescriptor],
        performance_history: PerformanceHistoryStore,
        *,
        routing_decision: RoutingDecision | None = None,
        budget: BrainBudget | None = None,
        policy: BrainPolicySignals | None = None,
    ) -> BrainState:
        """Build a ``BrainState`` from canonical ABrain primitives.

        Parameters
        ----------
        intent:
            Normalised task intent used by the production router.
        descriptors:
            Candidate agent descriptors (all agents, pre-filter).  When
            ``routing_decision`` is provided its ranked order is used;
            otherwise agents are sorted by capability match score descending.
        performance_history:
            Shared ``PerformanceHistoryStore``.
        routing_decision:
            Optional production ``RoutingDecision``.  When present:
            - ``routing_confidence``, ``score_gap``, ``confidence_band`` are
              copied directly.
            - Candidate order follows the production ranking.
            - ``capability_match_score`` values are taken from the decision.
        budget:
            Optional budget constraints.  Defaults to an unconstrained
            ``BrainBudget``.
        policy:
            Optional policy signals.  Defaults to ``BrainPolicySignals()``
            (no policy effects).
        """
        desc_by_id = {d.agent_id: d for d in descriptors}
        candidates = self._encode_candidates(
            intent, descriptors, performance_history, routing_decision, desc_by_id
        )

        routing_confidence = None
        score_gap = None
        confidence_band = None
        if routing_decision is not None:
            routing_confidence = routing_decision.routing_confidence
            score_gap = routing_decision.score_gap
            confidence_band = routing_decision.confidence_band

        return BrainState(
            task_type=intent.task_type,
            domain=intent.domain,
            risk=intent.risk,
            required_capabilities=list(intent.required_capabilities),
            num_required_capabilities=len(intent.required_capabilities),
            description=intent.description,
            budget=budget or BrainBudget(),
            policy=policy or BrainPolicySignals(),
            candidates=candidates,
            num_candidates=len(candidates),
            routing_confidence=routing_confidence,
            score_gap=score_gap,
            confidence_band=confidence_band,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _encode_candidates(
        self,
        intent: TaskIntent,
        descriptors: Sequence[AgentDescriptor],
        performance_history: PerformanceHistoryStore,
        routing_decision: RoutingDecision | None,
        desc_by_id: dict[str, AgentDescriptor],
    ) -> list[BrainAgentSignal]:
        if routing_decision is not None and routing_decision.ranked_candidates:
            # Follow production ranking; capability_match_score from decision.
            cap_match_by_id = {
                rc.agent_id: rc.capability_match_score
                for rc in routing_decision.ranked_candidates
            }
            ordered_ids = [rc.agent_id for rc in routing_decision.ranked_candidates]
            # Include descriptors not in ranked list at the end (in original order).
            remaining = [
                d.agent_id for d in descriptors
                if d.agent_id not in {aid for aid in ordered_ids}
            ]
            agent_ids = ordered_ids + remaining
        else:
            # No prior routing decision — sort by capability match score.
            cap_match_by_id = {
                d.agent_id: _capability_match(d, list(intent.required_capabilities))
                for d in descriptors
            }
            agent_ids = sorted(
                [d.agent_id for d in descriptors],
                key=lambda aid: cap_match_by_id.get(aid, 0.0),
                reverse=True,
            )

        signals: list[BrainAgentSignal] = []
        for agent_id in agent_ids:
            descriptor = desc_by_id.get(agent_id)
            if descriptor is None:
                continue
            history = performance_history.get_for_descriptor(descriptor)
            cap_match = cap_match_by_id.get(agent_id, 0.0)
            signals.append(
                BrainAgentSignal(
                    agent_id=agent_id,
                    capability_match_score=cap_match,
                    success_rate=history.success_rate,
                    avg_latency_s=history.avg_latency,
                    avg_cost_usd=history.avg_cost,
                    recent_failures=history.recent_failures,
                    execution_count=history.execution_count,
                    load_factor=history.load_factor,
                    trust_level_ord=_TRUST_ORD.get(descriptor.trust_level, 0.0),
                    availability_ord=_AVAILABILITY_ORD.get(descriptor.availability, 0.5),
                )
            )
        return signals
