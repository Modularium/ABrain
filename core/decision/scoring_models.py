"""Small neural scoring model used by the canonical decision layer."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ScoringModelWeights(BaseModel):
    """Serializable weights for the small MLP scorer."""

    model_config = ConfigDict(extra="forbid")

    feature_names: list[str] = Field(default_factory=list)
    input_hidden: list[list[float]] = Field(default_factory=list)
    hidden_bias: list[float] = Field(default_factory=list)
    hidden_output: list[float] = Field(default_factory=list)
    output_bias: float = 0.0


class MLPScoringModel:
    """Tiny deterministic MLP for agent scoring."""

    def __init__(self, weights: ScoringModelWeights) -> None:
        self.weights = weights

    @classmethod
    def build_default(cls, feature_names: list[str]) -> "MLPScoringModel":
        hidden_units = 6
        input_hidden = [[0.0 for _ in feature_names] for _ in range(hidden_units)]
        hidden_bias = [0.0, -0.5, -0.3, -0.3, -0.2, 0.0]
        hidden_output = [1.4, 0.9, 0.8, 0.7, 0.6, 0.4]
        output_bias = -1.2
        name_to_index = {name: index for index, name in enumerate(feature_names)}

        def add(hidden_index: int, feature_name: str, weight: float) -> None:
            if feature_name in name_to_index:
                input_hidden[hidden_index][name_to_index[feature_name]] = weight

        for name in feature_names:
            if name.startswith("task_embedding_"):
                add(5, name, 0.2)

        add(0, "capability_match_score", 2.5)
        add(0, "success_rate", 1.8)
        add(0, "trust_level", 1.0)
        add(0, "availability", 0.8)
        add(0, "recent_failures", -1.4)

        add(1, "avg_latency", 1.4)
        add(1, "latency_profile", 0.8)
        add(1, "load_factor", 0.6)

        add(2, "avg_cost", 1.2)
        add(2, "cost_profile", 0.9)

        add(3, "execution_count", 1.0)
        add(3, "recent_failures", -0.8)
        add(3, "success_rate", 0.6)

        add(4, "source_type", 0.3)
        add(4, "execution_kind", 0.5)
        add(4, "trust_level", 0.5)
        add(4, "availability", 0.4)

        weights = ScoringModelWeights(
            feature_names=feature_names,
            input_hidden=input_hidden,
            hidden_bias=hidden_bias,
            hidden_output=hidden_output,
            output_bias=output_bias,
        )
        return cls(weights)

    @classmethod
    def load_json(cls, path: str | Path) -> "MLPScoringModel":
        weights = ScoringModelWeights.model_validate_json(Path(path).read_text(encoding="utf-8"))
        return cls(weights)

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(self.weights.model_dump_json(indent=2), encoding="utf-8")
        return target

    def forward(self, feature_vector: list[float]) -> float:
        if len(feature_vector) != len(self.weights.feature_names):
            raise ValueError("feature vector size does not match model input size")
        hidden_values: list[float] = []
        for row, bias in zip(self.weights.input_hidden, self.weights.hidden_bias):
            activation = sum(weight * value for weight, value in zip(row, feature_vector)) + bias
            hidden_values.append(max(0.0, activation))
        output = (
            sum(weight * value for weight, value in zip(self.weights.hidden_output, hidden_values))
            + self.weights.output_bias
        )
        return 1.0 / (1.0 + math.exp(-output))

    def train_batch(
        self,
        feature_vectors: list[list[float]],
        rewards: list[float],
        *,
        learning_rate: float,
    ) -> float:
        if len(feature_vectors) != len(rewards):
            raise ValueError("feature_vectors and rewards must have the same length")
        if not feature_vectors:
            return 0.0
        total_loss = 0.0
        for feature_vector, reward in zip(feature_vectors, rewards):
            total_loss += self._train_single(feature_vector, reward, learning_rate=learning_rate)
        return total_loss / len(feature_vectors)

    def _train_single(self, feature_vector: list[float], reward: float, *, learning_rate: float) -> float:
        if len(feature_vector) != len(self.weights.feature_names):
            raise ValueError("feature vector size does not match model input size")

        hidden_pre: list[float] = []
        hidden_values: list[float] = []
        for row, bias in zip(self.weights.input_hidden, self.weights.hidden_bias):
            activation = sum(weight * value for weight, value in zip(row, feature_vector)) + bias
            hidden_pre.append(activation)
            hidden_values.append(max(0.0, activation))
        output_pre = (
            sum(weight * value for weight, value in zip(self.weights.hidden_output, hidden_values))
            + self.weights.output_bias
        )
        prediction = 1.0 / (1.0 + math.exp(-output_pre))
        loss = ((prediction - reward) ** 2) / 2.0

        d_loss_d_prediction = prediction - reward
        d_prediction_d_output = prediction * (1.0 - prediction)
        d_loss_d_output = d_loss_d_prediction * d_prediction_d_output

        previous_hidden_output = list(self.weights.hidden_output)
        for index, hidden_value in enumerate(hidden_values):
            grad = d_loss_d_output * hidden_value
            self.weights.hidden_output[index] -= learning_rate * grad
        self.weights.output_bias -= learning_rate * d_loss_d_output

        for hidden_index, (row, hidden_pre_value) in enumerate(
            zip(self.weights.input_hidden, hidden_pre)
        ):
            relu_grad = 1.0 if hidden_pre_value > 0 else 0.0
            d_hidden = d_loss_d_output * previous_hidden_output[hidden_index] * relu_grad
            if d_hidden == 0.0:
                continue
            for feature_index, feature_value in enumerate(feature_vector):
                row[feature_index] -= learning_rate * d_hidden * feature_value
            self.weights.hidden_bias[hidden_index] -= learning_rate * d_hidden
        return loss
