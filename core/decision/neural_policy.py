"""Mandatory neural policy model for the canonical decision layer."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .candidate_filter import CandidateAgentSet
from .feature_encoder import EncodedCandidateFeatures, FeatureEncoder
from .learning.dataset import TrainingSample
from .performance_history import PerformanceHistoryStore
from .scoring_models import MLPScoringModel
from .task_intent import TaskIntent


class ScoredCandidate(BaseModel):
    """Candidate plus neural score and encoded features."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    display_name: str
    score: float = Field(ge=0.0, le=1.0)
    encoded_features: EncodedCandidateFeatures
    model_source: str


class NeuralPolicyModel:
    """Always-on neural scoring model for safe candidates."""

    def __init__(
        self,
        *,
        encoder: FeatureEncoder | None = None,
        model_path: str | Path | None = None,
    ) -> None:
        self.encoder = encoder or FeatureEncoder()
        self.model_path = Path(model_path) if model_path else None
        self._model: MLPScoringModel | None = None
        self.model_source = "deterministic_init"

    def score_candidates(
        self,
        intent: TaskIntent,
        candidate_set: CandidateAgentSet,
        performance_history: PerformanceHistoryStore,
    ) -> list[ScoredCandidate]:
        if not candidate_set.candidates:
            self._ensure_model([])
            return []
        encoded_candidates = [
            self.encoder.encode(
                intent,
                candidate,
                performance_history.get_for_descriptor(candidate.agent),
            )
            for candidate in candidate_set.candidates
        ]
        self._ensure_model(encoded_candidates[0].feature_names)
        assert self._model is not None
        scored = [
            ScoredCandidate(
                agent_id=candidate.agent.agent_id,
                display_name=candidate.agent.display_name,
                score=self._model.forward(encoded.vector),
                encoded_features=encoded,
                model_source=self.model_source,
            )
            for candidate, encoded in zip(candidate_set.candidates, encoded_candidates)
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)

    def train_step(
        self,
        batch: list[TrainingSample],
        *,
        learning_rate: float = 0.05,
    ) -> float:
        if not batch:
            return 0.0
        feature_names = batch[0].feature_names
        self._ensure_model(feature_names)
        assert self._model is not None
        loss = self._model.train_batch(
            [sample.feature_vector for sample in batch],
            [sample.reward for sample in batch],
            learning_rate=learning_rate,
        )
        self.model_source = "trained_runtime"
        return loss

    def save_model(self, path: str | Path) -> Path:
        self._ensure_model([])
        assert self._model is not None
        return self._model.save_json(path)

    def load_model(self, path: str | Path) -> None:
        self.model_path = Path(path)
        self._model = MLPScoringModel.load_json(path)
        self.model_source = "loaded_weights"

    def _ensure_model(self, feature_names: list[str]) -> None:
        if self._model is not None:
            current_feature_names = self._model.weights.feature_names
            if current_feature_names == feature_names or not feature_names:
                return
            if self.model_source == "deterministic_init":
                self._model = MLPScoringModel.build_default(feature_names)
                return
            raise ValueError("loaded neural policy weights do not match encoded feature set")
        if self.model_path and self.model_path.exists():
            self._model = MLPScoringModel.load_json(self.model_path)
            self.model_source = "loaded_weights"
            return
        self._model = MLPScoringModel.build_default(feature_names)
        self.model_source = "deterministic_init"
