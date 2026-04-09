"""Feature encoding for the canonical neural policy model."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .agent_descriptor import (
    AgentAvailability,
    AgentCostProfile,
    AgentExecutionKind,
    AgentLatencyProfile,
    AgentSourceType,
    AgentTrustLevel,
)
from .candidate_filter import CandidateAgent
from .performance_history import AgentPerformanceHistory
from .task_intent import TaskIntent

_SOURCE_ORDER = list(AgentSourceType)
_EXECUTION_ORDER = list(AgentExecutionKind)
_TRUST_ORDER = list(AgentTrustLevel)
_AVAILABILITY_ORDER = list(AgentAvailability)
_COST_ORDER = list(AgentCostProfile)
_LATENCY_ORDER = list(AgentLatencyProfile)


class EncodedCandidateFeatures(BaseModel):
    """Encoded feature vector and human-readable feature map."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    feature_names: list[str] = Field(default_factory=list)
    vector: list[float] = Field(default_factory=list)
    feature_map: dict[str, float] = Field(default_factory=dict)


class FeatureEncoder:
    """Deterministic encoder for V1 neural policy features."""

    def __init__(self, embedding_dimensions: int = 8) -> None:
        self.embedding_dimensions = embedding_dimensions

    def encode(self, intent: TaskIntent, candidate: CandidateAgent, history: AgentPerformanceHistory) -> EncodedCandidateFeatures:
        task_embedding = self.encode_task_embedding(intent)
        descriptor = candidate.agent
        feature_map: dict[str, float] = {
            **{
                f"task_embedding_{index}": value
                for index, value in enumerate(task_embedding)
            },
            "capability_match_score": candidate.capability_match_score,
            "success_rate": history.success_rate,
            "avg_latency": self._bounded_inverse(history.avg_latency, scale=10.0),
            "avg_cost": self._bounded_inverse(history.avg_cost, scale=0.01),
            "recent_failures": self._bounded_inverse(float(history.recent_failures), scale=5.0),
            "execution_count": self._bounded(float(history.execution_count), scale=100.0),
            "load_factor": 1.0 - history.load_factor,
            "trust_level": self._enum_ratio(descriptor.trust_level, _TRUST_ORDER),
            "availability": self._enum_ratio(descriptor.availability, _AVAILABILITY_ORDER),
            "cost_profile": self._inverse_enum_ratio(descriptor.cost_profile, _COST_ORDER),
            "latency_profile": self._inverse_enum_ratio(descriptor.latency_profile, _LATENCY_ORDER),
            "source_type": self._enum_ratio(descriptor.source_type, _SOURCE_ORDER),
            "execution_kind": self._enum_ratio(descriptor.execution_kind, _EXECUTION_ORDER),
        }
        feature_names = list(feature_map.keys())
        return EncodedCandidateFeatures(
            agent_id=descriptor.agent_id,
            feature_names=feature_names,
            vector=[feature_map[name] for name in feature_names],
            feature_map=feature_map,
        )

    def encode_task_embedding(self, intent: TaskIntent) -> list[float]:
        tokens = [
            intent.task_type,
            intent.domain,
            *(intent.required_capabilities or []),
        ]
        if intent.description:
            tokens.extend(intent.description.lower().split()[:12])
        if not tokens:
            return [0.0] * self.embedding_dimensions
        embedding = [0.0] * self.embedding_dimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.embedding_dimensions):
                signed = (digest[index] / 255.0) * (1 if digest[index + 8] % 2 == 0 else -1)
                embedding[index] += signed
        token_count = float(len(tokens))
        return [max(min(value / token_count, 1.0), -1.0) for value in embedding]

    def _bounded(self, value: float, *, scale: float) -> float:
        return max(0.0, min(value / scale, 1.0))

    def _bounded_inverse(self, value: float, *, scale: float) -> float:
        return 1.0 - self._bounded(value, scale=scale)

    def _enum_ratio(self, value: Any, ordered_values: list[Any]) -> float:
        index = ordered_values.index(value)
        return self._bounded(float(index), scale=max(len(ordered_values) - 1, 1))

    def _inverse_enum_ratio(self, value: Any, ordered_values: list[Any]) -> float:
        return 1.0 - self._enum_ratio(value, ordered_values)
