"""Phase 5 – LearningOps L3: Offline training job definition.

Closes the full pipeline::

    DatasetExporter.load()
      → DataQualityFilter.filter()
      → _record_to_sample()
      → TrainingDataset
      → NeuralTrainer.train()
      → save_model()

``TrainingJobConfig`` declares all hyperparameters and paths.
``OfflineTrainer`` executes the job and returns ``OfflineTrainingResult``.

No heavy dependencies — uses only existing canonical components from
``core/decision/learning/`` and ``core/decision/neural_policy.py``.
"""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..neural_policy import NeuralPolicyModel
from .dataset import TrainingDataset, TrainingSample
from .exporter import DatasetExporter
from .persistence import save_model
from .quality import DataQualityFilter
from .record import LearningRecord
from .reward_model import RewardModel
from .trainer import NeuralTrainer, TrainingMetrics

# Fixed feature schema for offline-converted samples.  Must stay stable across
# training runs so that saved weights remain loadable.
_OFFLINE_FEATURE_NAMES: list[str] = [
    "success",
    "cost_norm",
    "latency_norm",
    "routing_confidence",
    "score_gap",
    "capability_match",
]

_COST_SCALE = 0.01    # same as RewardModel default
_LATENCY_SCALE = 10.0  # seconds; same as RewardModel default (latency_scale)


class TrainingJobConfig(BaseModel):
    """Declarative configuration for one offline training run."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: Path = Field(description="JSONL file produced by DatasetExporter")
    output_artifact_path: Path = Field(
        description="Where to write the trained model weights (JSON)"
    )

    # NeuralTrainer hyperparameters
    batch_size: int = Field(default=8, ge=1)
    learning_rate: float = Field(default=0.05, gt=0.0, le=1.0)
    epochs: int = Field(default=1, ge=1)
    min_samples: int = Field(default=2, ge=1)

    # DataQualityFilter settings applied before conversion
    require_routing_decision: bool = True
    require_outcome: bool = False

    # RewardModel scale overrides (leave at defaults unless explicitly tuned)
    latency_scale: float = Field(default=10.0, gt=0.0)
    cost_scale: float = Field(default=0.01, gt=0.0)


class OfflineTrainingResult(BaseModel):
    """Summary of one completed offline training run."""

    model_config = ConfigDict(extra="forbid")

    records_loaded: int = Field(ge=0)
    records_accepted: int = Field(ge=0)
    records_rejected: int = Field(ge=0)
    samples_converted: int = Field(ge=0)
    training_metrics: TrainingMetrics
    artifact_path: str
    manifest_schema_version: str
    exported_at: str


class OfflineTrainer:
    """Execute an offline training job defined by ``TrainingJobConfig``.

    Each call to ``run()`` always starts with a **fresh** ``NeuralPolicyModel``
    — it does not continue training from an existing checkpoint.  The resulting
    artefact is written to ``config.output_artifact_path`` and can be loaded
    via ``persistence.load_model()`` in a future run.
    """

    def __init__(self, config: TrainingJobConfig) -> None:
        self.config = config

    def run(self) -> OfflineTrainingResult:
        cfg = self.config

        # 1. Load JSONL dataset produced by DatasetExporter.
        exporter = DatasetExporter(cfg.dataset_path.parent)
        manifest, records = exporter.load(cfg.dataset_path)

        # 2. Filter by quality rules.
        quality_filter = DataQualityFilter(
            require_routing_decision=cfg.require_routing_decision,
            require_outcome=cfg.require_outcome,
        )
        accepted = quality_filter.filter(records)
        rejected_count = len(records) - len(accepted)

        # 3. Convert LearningRecords → TrainingSamples.
        reward_model = RewardModel(
            latency_scale=cfg.latency_scale,
            cost_scale=cfg.cost_scale,
        )
        samples = [_record_to_sample(r, reward_model) for r in accepted]

        # 4. Build TrainingDataset.
        dataset = TrainingDataset(samples)

        # 5. Train a fresh NeuralPolicyModel.
        policy = NeuralPolicyModel()
        trainer = NeuralTrainer(
            batch_size=cfg.batch_size,
            learning_rate=cfg.learning_rate,
            epochs=cfg.epochs,
            min_samples=cfg.min_samples,
        )
        metrics = trainer.train(dataset, policy)

        # 6. Save model artefact.
        cfg.output_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        save_model(policy, cfg.output_artifact_path)

        return OfflineTrainingResult(
            records_loaded=len(records),
            records_accepted=len(accepted),
            records_rejected=rejected_count,
            samples_converted=len(samples),
            training_metrics=metrics,
            artifact_path=str(cfg.output_artifact_path),
            manifest_schema_version=manifest.schema_version,
            exported_at=manifest.exported_at,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _record_to_sample(record: LearningRecord, reward_model: RewardModel) -> TrainingSample:
    """Convert one LearningRecord into a TrainingSample for NeuralTrainer.

    The conversion is intentionally conservative: feature values default to
    neutral (0.5 / 0.0) when the corresponding signal is absent.  This avoids
    introducing bias but means samples without outcome signals contribute little
    gradient.  Callers should prefer filtering with ``require_outcome=True`` for
    high-quality training runs.
    """
    success_f = float(record.success) if record.success is not None else 0.5
    cost_s = record.cost_usd if record.cost_usd is not None else 0.0
    latency_s = (record.latency_ms / 1000.0) if record.latency_ms is not None else 1.0

    reward = reward_model.compute_reward(
        success=success_f,
        latency=latency_s,
        cost=cost_s,
        failure_count=0,
    )

    capability_match = (
        record.selected_score if record.selected_score is not None else 0.5
    )
    routing_confidence = (
        record.routing_confidence if record.routing_confidence is not None else 0.5
    )
    score_gap = record.score_gap if record.score_gap is not None else 0.0

    cost_norm = min(cost_s / _COST_SCALE, 1.0) if _COST_SCALE > 0 else 0.0
    latency_norm = min(latency_s / _LATENCY_SCALE, 1.0) if _LATENCY_SCALE > 0 else 0.0

    feature_vector = [
        success_f,
        cost_norm,
        latency_norm,
        routing_confidence,
        score_gap,
        capability_match,
    ]

    return TrainingSample(
        task_embedding=[],
        capability_match=min(max(capability_match, 0.0), 1.0),
        success=min(max(success_f, 0.0), 1.0),
        cost=cost_s,
        latency=latency_s,
        agent_id=record.selected_agent_id or "unknown",
        capability_ids=list(record.candidate_agent_ids),
        timestamp=time.time(),
        reward=reward,
        feature_names=list(_OFFLINE_FEATURE_NAMES),
        feature_vector=feature_vector,
    )
