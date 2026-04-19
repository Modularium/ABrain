"""Phase 6 – Brain v1 B6-S3: Brain offline trainer.

Loads a JSONL dataset of ``BrainRecord`` objects, converts them to
``TrainingSample`` instances using a 13-dim Brain feature schema, runs a
training pass with the existing ``NeuralTrainer``/``NeuralPolicyModel``
stack, and saves the resulting weights as a model artefact for
``ModelRegistry``.

Pipeline::

    load_brain_records(path)
      → [filter by require_outcome]
      → _brain_record_to_sample()
      → TrainingDataset
      → NeuralTrainer.train()
      → save_model(artifact_path)

Module-level helpers ``save_brain_records`` / ``load_brain_records`` provide
the JSONL persistence layer (one ``BrainRecord`` per line, no manifest).

No heavy dependencies — stdlib + existing canonical components only.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..learning.dataset import TrainingDataset, TrainingSample
from ..learning.persistence import save_model
from ..learning.reward_model import RewardModel
from ..learning.trainer import NeuralTrainer, TrainingMetrics
from ..neural_policy import NeuralPolicyModel
from .state import BrainRecord

# ---------------------------------------------------------------------------
# Fixed Brain feature schema — must stay stable across training runs so that
# saved weights remain loadable with the same architecture.
# ---------------------------------------------------------------------------

_BRAIN_FEATURE_NAMES: list[str] = [
    # Routing confidence from the production pass
    "routing_confidence",     # [0,1]  — 0.0 when absent
    "score_gap",              # [0,1]  — 0.0 when absent
    "num_candidates_norm",    # [0,1]  — num_candidates / 10, clamped
    # Governance
    "has_policy_effect",      # {0,1}
    "approval_required",      # {0,1}
    # Top-1 candidate (selected agent, placed first by BrainRecordBuilder)
    "cap_match_score",        # [0,1]
    "success_rate",           # [0,1]
    "avg_latency_norm",       # [0,1]  — avg_latency_s / latency_scale_s
    "avg_cost_norm",          # [0,1]  — avg_cost_usd / cost_scale_usd
    "recent_failures_norm",   # [0,1]  — recent_failures / 5, clamped
    "load_factor",            # [0,1]
    "trust_level_ord",        # [0,1]  — ordinal per BrainAgentSignal
    "availability_ord",       # [0,1]  — ordinal per BrainAgentSignal
]

_NUM_CANDIDATES_SCALE = 10.0
_RECENT_FAILURES_SCALE = 5.0


class BrainTrainingJobConfig(BaseModel):
    """Declarative configuration for one Brain offline training run."""

    model_config = ConfigDict(extra="forbid")

    brain_records_path: Path = Field(
        description="JSONL file produced by save_brain_records — one BrainRecord per line"
    )
    output_artifact_path: Path = Field(
        description="Where to write the trained Brain model weights (JSON)"
    )

    # NeuralTrainer hyperparameters
    batch_size: int = Field(default=8, ge=1)
    learning_rate: float = Field(default=0.05, gt=0.0, le=1.0)
    epochs: int = Field(default=1, ge=1)
    min_samples: int = Field(default=2, ge=1)

    # Quality guard
    require_outcome: bool = Field(
        default=False,
        description=(
            "When True, skip BrainRecords whose target.outcome_success is None. "
            "Recommended for high-quality training runs."
        ),
    )

    # Normalisation scales (seconds / USD) — aligned with RewardModel defaults
    latency_scale_ms: float = Field(
        default=10_000.0,
        gt=0.0,
        description="Divisor for avg_latency_s normalisation (in ms, converted internally)",
    )
    cost_scale_usd: float = Field(
        default=0.01,
        gt=0.0,
        description="Divisor for avg_cost_usd normalisation",
    )


class BrainTrainingResult(BaseModel):
    """Summary of one completed Brain offline training run."""

    model_config = ConfigDict(extra="forbid")

    records_loaded: int = Field(ge=0)
    records_accepted: int = Field(ge=0)
    records_rejected: int = Field(ge=0)
    samples_converted: int = Field(ge=0)
    training_metrics: TrainingMetrics
    artifact_path: str
    feature_names: list[str]


class BrainOfflineTrainer:
    """Execute a Brain offline training job defined by ``BrainTrainingJobConfig``.

    Each call to ``run()`` always starts with a **fresh** ``NeuralPolicyModel``
    initialised with the Brain feature schema.  Weights are saved to
    ``config.output_artifact_path`` and can be registered with
    ``ModelRegistry`` for shadow evaluation via ``ShadowEvaluator``.
    """

    def __init__(self, config: BrainTrainingJobConfig) -> None:
        self.config = config

    def run(self) -> BrainTrainingResult:
        cfg = self.config

        # 1. Load BrainRecords from JSONL.
        records = load_brain_records(cfg.brain_records_path)

        # 2. Optionally filter records that lack outcome signal.
        if cfg.require_outcome:
            accepted = [r for r in records if r.target.outcome_success is not None]
        else:
            accepted = list(records)
        rejected_count = len(records) - len(accepted)

        # 3. Convert BrainRecords → TrainingSamples.
        latency_scale_s = cfg.latency_scale_ms / 1000.0
        reward_model = RewardModel(
            latency_scale=latency_scale_s,
            cost_scale=cfg.cost_scale_usd,
        )
        samples = [
            _brain_record_to_sample(r, latency_scale_s, cfg.cost_scale_usd, reward_model)
            for r in accepted
        ]

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

        return BrainTrainingResult(
            records_loaded=len(records),
            records_accepted=len(accepted),
            records_rejected=rejected_count,
            samples_converted=len(samples),
            training_metrics=metrics,
            artifact_path=str(cfg.output_artifact_path),
            feature_names=list(_BRAIN_FEATURE_NAMES),
        )


# ---------------------------------------------------------------------------
# JSONL persistence helpers
# ---------------------------------------------------------------------------


def save_brain_records(records: list[BrainRecord], path: Path) -> Path:
    """Persist a list of ``BrainRecord`` objects as JSONL (one per line).

    The file is overwritten if it already exists.  No manifest line is written —
    the file is a plain sequence of JSON objects for simplicity.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [r.model_dump_json() for r in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def load_brain_records(path: Path) -> list[BrainRecord]:
    """Load ``BrainRecord`` objects from a JSONL file written by ``save_brain_records``.

    Empty lines are ignored.  Raises ``ValueError`` if the file is empty or
    contains no valid records.
    """
    text = path.read_text(encoding="utf-8")
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError(f"Brain records file is empty: {path}")
    return [BrainRecord.model_validate(json.loads(line)) for line in raw_lines]


# ---------------------------------------------------------------------------
# Internal conversion helpers
# ---------------------------------------------------------------------------


def _brain_record_to_sample(
    record: BrainRecord,
    latency_scale_s: float,
    cost_scale_usd: float,
    reward_model: RewardModel,
) -> TrainingSample:
    """Convert one ``BrainRecord`` into a ``TrainingSample`` for ``NeuralTrainer``.

    Feature extraction strategy:
    - Task/routing features come from ``BrainState``.
    - Per-agent features are taken from the **first candidate** in
      ``state.candidates`` (the selected agent, placed first by
      ``BrainRecordBuilder``).  Neutral defaults apply when the list is empty.
    - The reward is derived from ``BrainTarget`` via ``RewardModel``.
    """
    state = record.state
    target = record.target

    # Routing confidence signals
    routing_confidence = state.routing_confidence if state.routing_confidence is not None else 0.0
    score_gap = state.score_gap if state.score_gap is not None else 0.0
    num_candidates_norm = min(state.num_candidates / _NUM_CANDIDATES_SCALE, 1.0)

    # Policy signals
    has_policy_effect = 1.0 if state.policy.has_policy_effect else 0.0
    approval_required = 1.0 if state.policy.approval_required else 0.0

    # Top-1 candidate signals (selected agent)
    if state.candidates:
        top = state.candidates[0]
        cap_match_score = top.capability_match_score
        success_rate = top.success_rate
        avg_latency_norm = min(top.avg_latency_s / max(latency_scale_s, 1e-9), 1.0)
        avg_cost_norm = min(top.avg_cost_usd / max(cost_scale_usd, 1e-9), 1.0)
        recent_failures_norm = min(top.recent_failures / _RECENT_FAILURES_SCALE, 1.0)
        load_factor = top.load_factor
        trust_level_ord = top.trust_level_ord
        availability_ord = top.availability_ord
    else:
        cap_match_score = 0.0
        success_rate = 0.5
        avg_latency_norm = 1.0
        avg_cost_norm = 0.0
        recent_failures_norm = 0.0
        load_factor = 0.0
        trust_level_ord = 0.0
        availability_ord = 0.5

    feature_vector = [
        routing_confidence,
        score_gap,
        num_candidates_norm,
        has_policy_effect,
        approval_required,
        cap_match_score,
        success_rate,
        avg_latency_norm,
        avg_cost_norm,
        recent_failures_norm,
        load_factor,
        trust_level_ord,
        availability_ord,
    ]

    # Reward from outcome
    success_f = float(target.outcome_success) if target.outcome_success is not None else 0.5
    cost_usd = target.outcome_cost_usd if target.outcome_cost_usd is not None else 0.0
    latency_s = (
        (target.outcome_latency_ms / 1000.0)
        if target.outcome_latency_ms is not None
        else latency_scale_s
    )
    reward = reward_model.compute_reward(
        success=success_f,
        latency=latency_s,
        cost=cost_usd,
        failure_count=0,
    )

    return TrainingSample(
        task_embedding=[],
        capability_match=cap_match_score,
        success=min(max(success_f, 0.0), 1.0),
        cost=cost_usd,
        latency=latency_s,
        agent_id=target.selected_agent_id or "unknown",
        capability_ids=[],
        timestamp=time.time(),
        reward=reward,
        feature_names=list(_BRAIN_FEATURE_NAMES),
        feature_vector=feature_vector,
    )
