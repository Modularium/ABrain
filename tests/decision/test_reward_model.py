import pytest

from core.decision.learning.reward_model import RewardModel
from core.decision.performance_history import AgentPerformanceHistory
from core.execution.adapters.base import ExecutionResult

pytestmark = pytest.mark.unit


def test_reward_model_computes_deterministic_reward():
    model = RewardModel()

    reward = model.compute_reward(success=1.0, latency=1.0, cost=0.001, failure_count=0)

    assert reward == pytest.approx(0.96)


def test_reward_model_maps_execution_result_to_reward():
    model = RewardModel()
    result = ExecutionResult(agent_id="agent-1", success=False, duration_ms=5000, cost=0.004)
    history = AgentPerformanceHistory(
        success_rate=0.5,
        avg_latency=2.0,
        avg_cost=0.003,
        recent_failures=2,
        execution_count=5,
    )

    reward = model.from_execution_result(result, history)

    assert 0.0 <= reward <= 1.0
    assert reward < 0.5
