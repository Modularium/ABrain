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
from .planner import Planner


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
        candidate_set = self.candidate_filter.filter_candidates(
            plan.intent,
            list(descriptors),
        )
        scored_candidates = self.neural_policy.score_candidates(
            plan.intent,
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
            task_type=plan.intent.task_type,
            required_capabilities=list(plan.intent.required_capabilities),
            ranked_candidates=ranked_candidates,
            selected_agent_id=selected.agent_id if selected else None,
            selected_score=selected.score if selected else None,
            diagnostics={
                "planner": plan.diagnostics,
                "candidate_filter": candidate_set.diagnostics,
                "rejected_agents": [
                    rejected.model_dump(mode="json") for rejected in candidate_set.rejected
                ],
                "neural_policy_source": self.neural_policy.model_source,
            },
        )
