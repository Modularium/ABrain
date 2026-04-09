"""Deterministic reward model for execution outcomes."""

from __future__ import annotations

from core.execution.adapters.base import ExecutionResult

from ..performance_history import AgentPerformanceHistory


class RewardModel:
    """Map execution outcomes to a stable scalar reward."""

    def __init__(
        self,
        *,
        latency_scale: float = 10.0,
        cost_scale: float = 0.01,
        failure_scale: float = 5.0,
    ) -> None:
        self.latency_scale = latency_scale
        self.cost_scale = cost_scale
        self.failure_scale = failure_scale

    def compute_reward(
        self,
        *,
        success: float,
        latency: float,
        cost: float,
        failure_count: int,
    ) -> float:
        normalized_latency = self._bounded(latency, self.latency_scale)
        normalized_cost = self._bounded(cost, self.cost_scale)
        failure_penalty = self._bounded(float(failure_count), self.failure_scale)
        reward = (
            0.6 * success
            + 0.2 * (1.0 - normalized_latency)
            + 0.2 * (1.0 - normalized_cost)
            - 0.1 * failure_penalty
        )
        return max(0.0, min(reward, 1.0))

    def from_execution_result(
        self,
        result: ExecutionResult,
        performance: AgentPerformanceHistory,
    ) -> float:
        success = 1.0 if result.success else 0.0
        latency = (
            (result.duration_ms / 1000.0)
            if result.duration_ms is not None
            else performance.avg_latency
        )
        cost = result.cost if result.cost is not None else performance.avg_cost
        return self.compute_reward(
            success=success,
            latency=latency,
            cost=cost,
            failure_count=performance.recent_failures,
        )

    def _bounded(self, value: float, scale: float) -> float:
        if scale <= 0:
            return 0.0
        return max(0.0, min(value / scale, 1.0))
