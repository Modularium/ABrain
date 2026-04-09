"""Batch trainer for the neural policy model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..neural_policy import NeuralPolicyModel
from .dataset import TrainingDataset


class TrainingMetrics(BaseModel):
    """Summary of one training run."""

    model_config = ConfigDict(extra="forbid")

    batch_size: int = Field(ge=0)
    average_loss: float = Field(ge=0.0)
    trained_steps: int = Field(ge=0)


class NeuralTrainer:
    """Run small deterministic training batches against the policy model."""

    def __init__(
        self,
        *,
        batch_size: int = 8,
        learning_rate: float = 0.05,
        epochs: int = 1,
        min_samples: int = 2,
    ) -> None:
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.min_samples = min_samples

    def train(
        self,
        dataset: TrainingDataset,
        model: NeuralPolicyModel,
    ) -> TrainingMetrics:
        if dataset.size() < self.min_samples:
            return TrainingMetrics(batch_size=0, average_loss=0.0, trained_steps=0)
        batch = dataset.get_batch(self.batch_size)
        loss_total = 0.0
        trained_steps = 0
        for _ in range(self.epochs):
            loss_total += model.train_step(batch, learning_rate=self.learning_rate)
            trained_steps += 1
        average_loss = loss_total / max(trained_steps, 1)
        return TrainingMetrics(
            batch_size=len(batch),
            average_loss=average_loss,
            trained_steps=trained_steps,
        )

    def compute_loss(self, predicted_score: float, reward: float) -> float:
        return ((predicted_score - reward) ** 2) / 2.0
