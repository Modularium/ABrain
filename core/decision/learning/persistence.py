"""Persistence helpers for learning dataset and model weights."""

from __future__ import annotations

import json
from pathlib import Path

from ..neural_policy import NeuralPolicyModel
from .dataset import TrainingDataset, TrainingSample


def save_dataset(dataset: TrainingDataset, path: str | Path) -> Path:
    target = Path(path)
    payload = [sample.model_dump(mode="json") for sample in dataset.all_samples()]
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_dataset(path: str | Path) -> TrainingDataset:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return TrainingDataset([TrainingSample.model_validate(item) for item in payload])


def save_model(model: NeuralPolicyModel, path: str | Path) -> Path:
    return model.save_model(path)


def load_model(path: str | Path, *, model: NeuralPolicyModel | None = None) -> NeuralPolicyModel:
    policy = model or NeuralPolicyModel()
    policy.load_model(path)
    return policy
