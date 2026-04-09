import pytest

from core.decision.learning.dataset import TrainingDataset, TrainingSample

pytestmark = pytest.mark.unit


def test_learning_dataset_grows_and_batches_deterministically():
    dataset = TrainingDataset()
    first = TrainingSample(
        task_embedding=[0.1, 0.2],
        capability_match=1.0,
        success=1.0,
        cost=0.001,
        latency=0.8,
        agent_id="agent-1",
        capability_ids=["analysis.code"],
        timestamp=1.0,
        reward=0.9,
        feature_names=["f1", "f2"],
        feature_vector=[0.1, 0.2],
    )
    second = first.model_copy(update={"timestamp": 2.0, "agent_id": "agent-2"})

    dataset.add_sample(first)
    dataset.add_sample(second)

    assert dataset.size() == 2
    assert [sample.agent_id for sample in dataset.get_batch(1)] == ["agent-2"]
    assert [sample.agent_id for sample in dataset.get_batch(5)] == ["agent-1", "agent-2"]
