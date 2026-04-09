from pathlib import Path

import pytest

from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    CandidateFilter,
    NeuralPolicyModel,
    PerformanceHistoryStore,
    TaskIntent,
)

pytestmark = pytest.mark.unit


def build_descriptor(agent_id: str, *, success_rate: float, cost: float, latency: float) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["analysis.code", "code.refactor"],
        availability=AgentAvailability.ONLINE,
        metadata={
            "success_rate": success_rate,
            "estimated_cost_per_token": cost,
            "avg_response_time": latency,
        },
    )


def test_neural_policy_scores_candidates_with_deterministic_default_model(tmp_path: Path):
    intent = TaskIntent(
        task_type="code_refactor",
        domain="code",
        required_capabilities=["analysis.code", "code.refactor"],
        description="Refactor the worker routing logic",
    )
    candidate_set = CandidateFilter().filter_candidates(
        intent,
        [
            build_descriptor("strong-agent", success_rate=0.95, cost=0.001, latency=1.0),
            build_descriptor("weak-agent", success_rate=0.55, cost=0.009, latency=4.0),
        ],
    )
    model = NeuralPolicyModel(model_path=tmp_path / "missing-weights.json")

    scored = model.score_candidates(intent, candidate_set, PerformanceHistoryStore())

    assert model.model_source == "deterministic_init"
    assert [item.agent_id for item in scored] == ["strong-agent", "weak-agent"]
    assert 0.0 <= scored[0].score <= 1.0


def test_neural_policy_remains_active_after_empty_candidate_run(tmp_path: Path):
    intent = TaskIntent(
        task_type="code_refactor",
        domain="code",
        required_capabilities=["analysis.code", "code.refactor"],
    )
    model = NeuralPolicyModel(model_path=tmp_path / "missing-weights.json")

    assert model.score_candidates(
        intent,
        CandidateFilter().filter_candidates(intent, []),
        PerformanceHistoryStore(),
    ) == []

    candidate_set = CandidateFilter().filter_candidates(
        intent,
        [build_descriptor("agent-1", success_rate=0.9, cost=0.001, latency=1.5)],
    )
    scored = model.score_candidates(intent, candidate_set, PerformanceHistoryStore())

    assert len(scored) == 1
    assert scored[0].model_source == "deterministic_init"
