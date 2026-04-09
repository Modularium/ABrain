"""Online learning hook for collecting training samples from executions."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from core.execution.adapters.base import ExecutionResult
from core.model_context import ModelContext, TaskContext

from ..agent_descriptor import AgentDescriptor
from ..candidate_filter import CandidateAgent
from ..feature_encoder import FeatureEncoder
from ..performance_history import AgentPerformanceHistory
from ..planner import Planner
from .dataset import TrainingDataset, TrainingSample
from .reward_model import RewardModel


class OnlineUpdater:
    """Create training samples after each execution result."""

    def __init__(
        self,
        *,
        dataset: TrainingDataset | None = None,
        reward_model: RewardModel | None = None,
        encoder: FeatureEncoder | None = None,
        planner: Planner | None = None,
        train_every: int = 5,
    ) -> None:
        self.dataset = dataset or TrainingDataset()
        self.reward_model = reward_model or RewardModel()
        self.encoder = encoder or FeatureEncoder()
        self.planner = planner or Planner()
        self.train_every = train_every

    def record_execution(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        agent_descriptor: AgentDescriptor,
        result: ExecutionResult,
        performance: AgentPerformanceHistory,
    ) -> TrainingSample:
        plan = self.planner.plan(task)
        required_capabilities = plan.intent.required_capabilities
        matched_capabilities = [
            capability_id
            for capability_id in required_capabilities
            if capability_id in agent_descriptor.capabilities
        ]
        capability_match = (
            len(matched_capabilities) / len(required_capabilities)
            if required_capabilities
            else 1.0
        )
        candidate = CandidateAgent(
            agent=agent_descriptor,
            capability_match_score=capability_match,
            matched_capabilities=matched_capabilities,
        )
        encoded = self.encoder.encode(plan.intent, candidate, performance)
        reward = self.reward_model.from_execution_result(result, performance)
        sample = TrainingSample(
            task_embedding=self.encoder.encode_task_embedding(plan.intent),
            capability_match=capability_match,
            success=1.0 if result.success else 0.0,
            cost=result.cost if result.cost is not None else performance.avg_cost,
            latency=(
                (result.duration_ms / 1000.0)
                if result.duration_ms is not None
                else performance.avg_latency
            ),
            agent_id=agent_descriptor.agent_id,
            capability_ids=list(required_capabilities),
            timestamp=time.time(),
            reward=reward,
            feature_names=encoded.feature_names,
            feature_vector=encoded.vector,
        )
        self.dataset.add_sample(sample)
        return sample

    def should_train(self) -> bool:
        return self.dataset.size() > 0 and self.dataset.size() % self.train_every == 0
