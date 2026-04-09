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
from core.decision.learning.dataset import TrainingDataset, TrainingSample
from core.decision.learning.trainer import NeuralTrainer

pytestmark = pytest.mark.unit


def build_descriptor(agent_id: str) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis.code", "code.refactor"],
        availability=AgentAvailability.ONLINE,
    )


def test_trainer_changes_neural_policy_scores():
    model = NeuralPolicyModel()
    intent = TaskIntent(
        task_type="code_refactor",
        domain="code",
        required_capabilities=["analysis.code", "code.refactor"],
        description="Refactor this worker",
    )
    candidate_set = CandidateFilter().filter_candidates(intent, [build_descriptor("agent-1")])
    history = PerformanceHistoryStore()
    before = model.score_candidates(intent, candidate_set, history)[0].score
    encoded = model.score_candidates(intent, candidate_set, history)[0].encoded_features

    dataset = TrainingDataset(
        [
            TrainingSample(
                task_embedding=encoded.vector[:8],
                capability_match=1.0,
                success=0.0,
                cost=0.01,
                latency=5.0,
                agent_id="agent-1",
                capability_ids=["analysis.code", "code.refactor"],
                timestamp=1.0,
                reward=0.0,
                feature_names=encoded.feature_names,
                feature_vector=encoded.vector,
            )
        ]
    )
    trainer = NeuralTrainer(batch_size=1, learning_rate=0.2, epochs=12, min_samples=1)

    metrics = trainer.train(dataset, model)
    after = model.score_candidates(intent, candidate_set, history)[0].score

    assert metrics.trained_steps == 12
    assert after != pytest.approx(before)
    assert after < before
