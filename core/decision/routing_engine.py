"""Canonical routing engine for the ABrain decision layer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core.model_context import ModelContext, TaskContext

from .agent_descriptor import AgentAvailability, AgentCostProfile, AgentDescriptor
from .candidate_filter import CandidateFilter
from .neural_policy import NeuralPolicyModel, ScoredCandidate
from .performance_history import PerformanceHistoryStore
from .plan_models import PlanStep
from .planner import Planner
from .task_intent import TaskIntent


class RankedCandidate(BaseModel):
    """Ranked candidate returned by the routing engine."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    display_name: str
    score: float = Field(ge=0.0, le=1.0)
    capability_match_score: float = Field(ge=0.0, le=1.0)
    model_source: str
    feature_summary: dict[str, float] = Field(default_factory=dict)


class RoutingPreferences(BaseModel):
    """Routing configuration for health, cost, and confidence signals.

    These preferences are instance-level settings on RoutingEngine and are
    applied *after* neural scoring in route_intent(). They do not alter the
    MLP model, the CandidateFilter hard policy, or S4 hard-fallback behaviour.
    """

    model_config = ConfigDict(extra="forbid")

    # DEGRADED agents' scores are multiplied by this value after neural scoring.
    # Default 0.85 = 15 % penalty; use 1.0 to disable.
    degraded_availability_penalty: float = Field(default=0.85, ge=0.0, le=1.0)

    # Within this score band around the top candidate, prefer the lower-cost
    # agent.  Default 0.05 = 5 % band; use 0.0 to disable tie-breaking.
    cost_tie_band: float = Field(default=0.05, ge=0.0, le=1.0)

    # Unused in v1 (reserved for future caller-level override).
    low_confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class RoutingDecision(BaseModel):
    """Structured routing result without triggering execution."""

    model_config = ConfigDict(extra="forbid")

    task_type: str
    required_capabilities: list[str] = Field(default_factory=list)
    ranked_candidates: list[RankedCandidate] = Field(default_factory=list)
    selected_agent_id: str | None = None
    selected_score: float | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    # S4.2 confidence metrics — None when there are no candidates
    routing_confidence: float | None = None
    score_gap: float | None = None
    confidence_band: Literal["high", "medium", "low"] | None = None


# ---------------------------------------------------------------------------
# S4.2 helper functions (module-level, not methods — no hidden state needed)
# ---------------------------------------------------------------------------

# Cost preference order: lower index = cheaper.
_COST_PREFERENCE_ORDER: dict[AgentCostProfile, int] = {
    AgentCostProfile.LOW: 0,
    AgentCostProfile.MEDIUM: 1,
    AgentCostProfile.UNKNOWN: 2,
    AgentCostProfile.VARIABLE: 3,
    AgentCostProfile.HIGH: 4,
}


def _apply_degraded_penalty(
    scored: list[ScoredCandidate],
    descriptors_by_id: dict[str, AgentDescriptor],
    multiplier: float,
) -> list[ScoredCandidate]:
    """Return scored list re-sorted after applying a penalty to DEGRADED agents.

    Agents whose availability is DEGRADED have their score multiplied by
    *multiplier* (< 1.0 = penalty).  The list is then re-sorted descending.
    Only the in-memory score representation is changed; descriptor state is
    not mutated.

    If *multiplier* is 1.0 (or no candidates are DEGRADED) the original order
    is preserved.
    """
    if multiplier >= 1.0:
        return scored

    penalised: list[ScoredCandidate] = []
    changed = False
    for candidate in scored:
        descriptor = descriptors_by_id.get(candidate.agent_id)
        if descriptor is not None and descriptor.availability is AgentAvailability.DEGRADED:
            # ScoredCandidate is a Pydantic model; create a new instance with
            # the adjusted score to avoid mutating the original.
            candidate = candidate.model_copy(update={"score": candidate.score * multiplier})
            changed = True
        penalised.append(candidate)

    if not changed:
        return scored

    penalised.sort(key=lambda c: c.score, reverse=True)
    return penalised


def _apply_cost_tiebreak(
    scored: list[ScoredCandidate],
    descriptors_by_id: dict[str, AgentDescriptor],
    band: float,
) -> list[ScoredCandidate]:
    """Within *band* of the top score prefer the cheaper agent.

    Candidates whose score is within *band* of the top candidate's score are
    sorted by cost profile (LOW < MEDIUM < UNKNOWN < VARIABLE < HIGH).
    Candidates outside the band keep their original order relative to each
    other.

    If *band* is 0.0 or there is only one candidate, the list is returned
    unchanged.
    """
    if band <= 0.0 or len(scored) <= 1:
        return scored

    if not scored:
        return scored

    top_score = scored[0].score
    threshold = top_score - band

    in_band: list[ScoredCandidate] = []
    out_of_band: list[ScoredCandidate] = []
    for candidate in scored:
        if candidate.score >= threshold:
            in_band.append(candidate)
        else:
            out_of_band.append(candidate)

    if len(in_band) <= 1:
        return scored

    in_band.sort(
        key=lambda c: (
            _COST_PREFERENCE_ORDER.get(
                descriptors_by_id[c.agent_id].cost_profile
                if c.agent_id in descriptors_by_id
                else AgentCostProfile.UNKNOWN,
                _COST_PREFERENCE_ORDER[AgentCostProfile.UNKNOWN],
            ),
            # Secondary: higher score wins within same cost tier
            -c.score,
        )
    )
    return in_band + out_of_band


def _compute_routing_metrics(
    scored: list[ScoredCandidate],
) -> tuple[float | None, float | None, Literal["high", "medium", "low"] | None]:
    """Compute (routing_confidence, score_gap, confidence_band) from scored list.

    - ``routing_confidence``: top candidate's score (honest proxy for certainty)
    - ``score_gap``: difference between #1 and #2 score (0.0 if only one)
    - ``confidence_band``: "high" ≥ 0.65, "medium" ≥ 0.35, "low" < 0.35

    Returns (None, None, None) when there are no candidates.
    """
    if not scored:
        return None, None, None

    top_score = scored[0].score
    second_score = scored[1].score if len(scored) > 1 else top_score
    score_gap = top_score - second_score

    if top_score >= 0.65:
        confidence_band: Literal["high", "medium", "low"] = "high"
    elif top_score >= 0.35:
        confidence_band = "medium"
    else:
        confidence_band = "low"

    return top_score, score_gap, confidence_band


class RoutingEngine:
    """Orchestrate planning, filtering and neural ranking."""

    def __init__(
        self,
        *,
        planner: Planner | None = None,
        candidate_filter: CandidateFilter | None = None,
        neural_policy: NeuralPolicyModel | None = None,
        performance_history: PerformanceHistoryStore | None = None,
        preferences: RoutingPreferences | None = None,
    ) -> None:
        self.planner = planner or Planner()
        self.candidate_filter = candidate_filter or CandidateFilter()
        self.neural_policy = neural_policy or NeuralPolicyModel()
        self.performance_history = performance_history or PerformanceHistoryStore()
        self.preferences = preferences or RoutingPreferences()

    def route(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        descriptors: Sequence[AgentDescriptor],
    ) -> RoutingDecision:
        plan = self.planner.plan(task)
        return self.route_intent(
            plan.intent,
            descriptors,
            diagnostics={"planner": plan.diagnostics},
        )

    def route_step(
        self,
        step: PlanStep,
        task: TaskContext | ModelContext | Mapping[str, Any],
        descriptors: Sequence[AgentDescriptor],
        *,
        exclude_agent_ids: set[str] | None = None,
    ) -> RoutingDecision:
        if exclude_agent_ids:
            descriptors = [d for d in descriptors if d.agent_id not in exclude_agent_ids]
        preferences = {}
        if isinstance(task, TaskContext):
            preferences = dict(task.preferences or {})
        elif isinstance(task, Mapping):
            raw_preferences = task.get("preferences")
            preferences = dict(raw_preferences) if isinstance(raw_preferences, Mapping) else {}
        execution_hints = dict(preferences.get("execution_hints") or {})
        if step.preferred_source_types:
            execution_hints["allowed_source_types"] = [item.value for item in step.preferred_source_types]
        if step.preferred_execution_kinds:
            execution_hints["allowed_execution_kinds"] = [item.value for item in step.preferred_execution_kinds]
        intent = TaskIntent(
            task_type=str(step.metadata.get("task_type") or step.step_id),
            domain=str(step.metadata.get("domain") or preferences.get("domain") or "analysis"),
            risk=step.risk,
            required_capabilities=list(step.required_capabilities),
            execution_hints=execution_hints,
            description=step.description,
        )
        return self.route_intent(
            intent,
            descriptors,
            diagnostics={
                "step_id": step.step_id,
                "inputs_from_steps": list(step.inputs_from_steps),
                "allow_parallel_group": step.allow_parallel_group,
            },
        )

    def route_intent(
        self,
        intent: TaskIntent,
        descriptors: Sequence[AgentDescriptor],
        *,
        diagnostics: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        candidate_set = self.candidate_filter.filter_candidates(
            intent,
            list(descriptors),
        )
        scored_candidates = self.neural_policy.score_candidates(
            intent,
            candidate_set,
            self.performance_history,
        )

        # S4.2 — build a descriptor lookup for post-scoring adjustments
        descriptors_by_id: dict[str, AgentDescriptor] = {
            d.agent_id: d for d in descriptors
        }

        # S4.2 — apply DEGRADED availability penalty (post-MLP, pre-selection)
        scored_candidates = _apply_degraded_penalty(
            scored_candidates,
            descriptors_by_id,
            self.preferences.degraded_availability_penalty,
        )

        # S4.2 — apply cost tie-breaking within the top score band
        scored_candidates = _apply_cost_tiebreak(
            scored_candidates,
            descriptors_by_id,
            self.preferences.cost_tie_band,
        )

        # S4.2 — compute confidence metrics for audit / trace
        routing_confidence, score_gap, confidence_band = _compute_routing_metrics(scored_candidates)

        capability_match_by_agent = {
            candidate.agent.agent_id: candidate.capability_match_score
            for candidate in candidate_set.candidates
        }
        ranked_candidates = [
            RankedCandidate(
                agent_id=item.agent_id,
                display_name=item.display_name,
                score=item.score,
                capability_match_score=capability_match_by_agent[item.agent_id],
                model_source=item.model_source,
                feature_summary={
                    key: value
                    for key, value in item.encoded_features.feature_map.items()
                    if key
                    in {
                        "capability_match_score",
                        "success_rate",
                        "avg_latency",
                        "avg_cost",
                        "trust_level",
                        "availability",
                    }
                },
            )
            for item in scored_candidates
        ]
        selected = ranked_candidates[0] if ranked_candidates else None
        return RoutingDecision(
            task_type=intent.task_type,
            required_capabilities=list(intent.required_capabilities),
            ranked_candidates=ranked_candidates,
            selected_agent_id=selected.agent_id if selected else None,
            selected_score=selected.score if selected else None,
            routing_confidence=routing_confidence,
            score_gap=score_gap,
            confidence_band=confidence_band,
            diagnostics={
                **(diagnostics or {}),
                "candidate_filter": candidate_set.diagnostics,
                "candidate_agent_ids": [candidate.agent_id for candidate in ranked_candidates],
                "selected_candidate": selected.model_dump(mode="json") if selected else None,
                "rejected_agents": [
                    rejected.model_dump(mode="json") for rejected in candidate_set.rejected
                ],
                "neural_policy_source": self.neural_policy.model_source,
            },
        )
