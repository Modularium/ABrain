from pathlib import Path

import pytest

from core.decision import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    FeedbackLoop,
    NeuralPolicyModel,
    OnlineUpdater,
    PerformanceHistoryStore,
)
from core.decision.learning.persistence import load_dataset, load_model, save_dataset, save_model
from core.decision.learning.trainer import NeuralTrainer
from core.execution.adapters.base import ExecutionResult

pytestmark = pytest.mark.unit


def build_descriptor() -> AgentDescriptor:
    return AgentDescriptor(
        agent_id="agent-1",
        display_name="Agent 1",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis.code", "code.refactor"],
    )


def test_feedback_loop_creates_samples_and_trains_model(tmp_path: Path):
    dataset_updater = OnlineUpdater(train_every=1)
    policy = NeuralPolicyModel()
    feedback = FeedbackLoop(
        performance_history=PerformanceHistoryStore(),
        online_updater=dataset_updater,
        trainer=NeuralTrainer(batch_size=1, learning_rate=0.1, epochs=4, min_samples=1),
        neural_policy=policy,
    )

    update = feedback.update_performance(
        "agent-1",
        ExecutionResult(
            agent_id="agent-1",
            success=True,
            duration_ms=700,
            cost=0.001,
            output={"status": "ok"},
        ),
        task={"task_type": "code_refactor", "description": "Refactor this worker"},
        agent_descriptor=build_descriptor(),
    )

    dataset_path = save_dataset(dataset_updater.dataset, tmp_path / "dataset.json")
    model_path = save_model(policy, tmp_path / "model.json")
    loaded_dataset = load_dataset(dataset_path)
    loaded_policy = load_model(model_path)

    assert update.dataset_size == 1
    assert update.reward is not None
    assert update.training_metrics is not None
    assert policy.model_source == "trained_runtime"
    assert loaded_dataset.size() == 1
    assert loaded_policy.model_source == "loaded_weights"
