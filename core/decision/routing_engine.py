"""Canonical routing engine for the ABrain decision layer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.model_context import ModelContext, TaskContext

from .agent_descriptor import AgentDescriptor
from .candidate_filter import CandidateFilter
from .neural_policy import NeuralPolicyModel
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


class RoutingDecision(BaseModel):
    """Structured routing result without triggering execution."""

    model_config = ConfigDict(extra="forbid")

    task_type: str
    required_capabilities: list[str] = Field(default_factory=list)
    ranked_candidates: list[RankedCandidate] = Field(default_factory=list)
    selected_agent_id: str | None = None
    selected_score: float | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class RoutingEngine:
    """Orchestrate planning, filtering and neural ranking."""

    def __init__(
        self,
        *,
        planner: Planner | None = None,
        candidate_filter: CandidateFilter | None = None,
        neural_policy: NeuralPolicyModel | None = None,
        performance_history: PerformanceHistoryStore | None = None,
    ) -> None:
        self.planner = planner or Planner()
        self.candidate_filter = candidate_filter or CandidateFilter()
        self.neural_policy = neural_policy or NeuralPolicyModel()
        self.performance_history = performance_history or PerformanceHistoryStore()

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
