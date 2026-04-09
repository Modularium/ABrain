"""Feedback loop that updates performance history from execution outcomes."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.execution.adapters.base import ExecutionResult
from core.model_context import ModelContext, TaskContext

from .agent_descriptor import AgentDescriptor
from .learning.online_updater import OnlineUpdater
from .learning.trainer import NeuralTrainer, TrainingMetrics
from .neural_policy import NeuralPolicyModel
from .performance_history import AgentPerformanceHistory, PerformanceHistoryStore

logger = logging.getLogger(__name__)


class FeedbackUpdate(BaseModel):
    """Structured result of a feedback update."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    performance: AgentPerformanceHistory
    score_delta: int
    reward: float | None = None
    dataset_size: int | None = None
    training_metrics: TrainingMetrics | None = None
    warnings: list[str] = Field(default_factory=list)


class FeedbackLoop:
    """Collect execution outcomes and update performance history."""

    def __init__(
        self,
        *,
        performance_history: PerformanceHistoryStore | None = None,
        online_updater: OnlineUpdater | None = None,
        trainer: NeuralTrainer | None = None,
        neural_policy: NeuralPolicyModel | None = None,
    ) -> None:
        self.performance_history = performance_history or PerformanceHistoryStore()
        self.online_updater = online_updater
        self.trainer = trainer
        self.neural_policy = neural_policy

    def update_performance(
        self,
        agent_id: str,
        result: ExecutionResult,
        *,
        task: TaskContext | ModelContext | Mapping[str, Any] | None = None,
        agent_descriptor: AgentDescriptor | None = None,
    ) -> FeedbackUpdate:
        updated = self.performance_history.record_result(
            agent_id,
            success=result.success,
            latency=(result.duration_ms / 1000.0) if result.duration_ms is not None else None,
            cost=result.cost,
        )
        reward = None
        dataset_size = None
        training_metrics = None
        warnings: list[str] = []
        if self.online_updater is not None and task is not None and agent_descriptor is not None:
            try:
                sample = self.online_updater.record_execution(task, agent_descriptor, result, updated)
                reward = sample.reward
                dataset_size = self.online_updater.dataset.size()
                if (
                    self.trainer is not None
                    and self.neural_policy is not None
                    and self.online_updater.should_train()
                ):
                    training_metrics = self.trainer.train(
                        self.online_updater.dataset,
                        self.neural_policy,
                    )
            except Exception as exc:  # pragma: no cover - defensive containment
                warning = f"learning_pipeline_failed:{exc.__class__.__name__}"
                warnings.append(warning)
                logger.warning(
                    json.dumps(
                        {
                            "event": "learning_pipeline_failed",
                            "agent_id": agent_id,
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                        },
                        sort_keys=True,
                    )
                )
        return FeedbackUpdate(
            agent_id=agent_id,
            performance=updated,
            score_delta=1 if result.success else -1,
            reward=reward,
            dataset_size=dataset_size,
            training_metrics=training_metrics,
            warnings=warnings,
        )
