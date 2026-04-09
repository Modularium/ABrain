"""Training dataset for neural policy learning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TrainingSample(BaseModel):
    """Single training example derived from a real execution."""

    model_config = ConfigDict(extra="forbid")

    task_embedding: list[float] = Field(default_factory=list)
    capability_match: float = Field(ge=0.0, le=1.0)
    success: float = Field(ge=0.0, le=1.0)
    cost: float = Field(ge=0.0)
    latency: float = Field(ge=0.0)
    agent_id: str
    capability_ids: list[str] = Field(default_factory=list)
    timestamp: float
    reward: float = Field(ge=0.0, le=1.0)
    feature_names: list[str] = Field(default_factory=list)
    feature_vector: list[float] = Field(default_factory=list)


class TrainingDataset:
    """Append-only in-memory dataset with deterministic batching."""

    def __init__(self, samples: list[TrainingSample] | None = None) -> None:
        self._samples: list[TrainingSample] = list(samples or [])

    def add_sample(self, sample: TrainingSample) -> TrainingSample:
        self._samples.append(sample)
        return sample

    def get_batch(self, batch_size: int) -> list[TrainingSample]:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if batch_size >= len(self._samples):
            return list(self._samples)
        return list(self._samples[-batch_size:])

    def size(self) -> int:
        return len(self._samples)

    def all_samples(self) -> list[TrainingSample]:
        return list(self._samples)
