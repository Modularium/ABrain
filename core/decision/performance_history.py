"""Performance history used as an input to neural policy scoring."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .agent_descriptor import AgentDescriptor


class AgentPerformanceHistory(BaseModel):
    """Lightweight performance snapshot for a single agent."""

    model_config = ConfigDict(extra="forbid")

    success_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_latency: float = Field(default=1.0, ge=0.0)
    avg_cost: float = Field(default=0.0, ge=0.0)
    avg_token_count: float = Field(default=0.0, ge=0.0)
    avg_user_rating: float = Field(default=0.0, ge=0.0)
    recent_failures: int = Field(default=0, ge=0)
    execution_count: int = Field(default=0, ge=0)
    load_factor: float = Field(default=0.0, ge=0.0, le=1.0)


class PerformanceHistoryStore:
    """Small in-memory store with optional JSON persistence."""

    def __init__(
        self,
        initial: dict[str, AgentPerformanceHistory] | None = None,
    ) -> None:
        self._history: dict[str, AgentPerformanceHistory] = dict(initial or {})

    def get(self, agent_id: str) -> AgentPerformanceHistory:
        return self._history.get(agent_id, AgentPerformanceHistory())

    def snapshot(self) -> dict[str, AgentPerformanceHistory]:
        """Return a shallow copy of all tracked agent histories.

        Read-only consumers (e.g. reporting surfaces) should prefer this
        over touching ``_history`` directly so the store keeps ownership
        of its internal mapping.
        """
        return dict(self._history)

    def get_for_descriptor(self, descriptor: AgentDescriptor) -> AgentPerformanceHistory:
        if descriptor.agent_id in self._history:
            return self._history[descriptor.agent_id]
        metadata = descriptor.metadata
        return AgentPerformanceHistory(
            success_rate=self._coerce_float(metadata.get("success_rate"), 0.5),
            avg_latency=self._coerce_float(metadata.get("avg_response_time"), 1.0),
            avg_cost=self._coerce_float(metadata.get("estimated_cost_per_token"), 0.0),
            recent_failures=self._coerce_int(metadata.get("recent_failures"), 0),
            execution_count=self._coerce_int(metadata.get("execution_count"), 0),
            load_factor=self._coerce_float(metadata.get("load_factor"), 0.0),
        )

    def set(self, agent_id: str, history: AgentPerformanceHistory) -> AgentPerformanceHistory:
        self._history[agent_id] = history
        return history

    def record_result(
        self,
        agent_id: str,
        *,
        success: bool,
        latency: float | None = None,
        cost: float | None = None,
        token_count: int | None = None,
        user_rating: float | None = None,
    ) -> AgentPerformanceHistory:
        current = self.get(agent_id)
        execution_count = current.execution_count + 1
        success_count = round(current.success_rate * current.execution_count)
        success_count = success_count + (1 if success else 0)
        recent_failures = 0 if success else current.recent_failures + 1
        updated = AgentPerformanceHistory(
            success_rate=success_count / execution_count,
            avg_latency=self._rolling_average(current.avg_latency, latency, execution_count),
            avg_cost=self._rolling_average(current.avg_cost, cost, execution_count),
            avg_token_count=self._rolling_average(
                current.avg_token_count,
                float(token_count) if token_count is not None else None,
                execution_count,
            ),
            avg_user_rating=self._rolling_average(current.avg_user_rating, user_rating, execution_count),
            recent_failures=recent_failures,
            execution_count=execution_count,
            load_factor=current.load_factor,
        )
        self._history[agent_id] = updated
        return updated

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        payload = {
            agent_id: history.model_dump(mode="json")
            for agent_id, history in sorted(self._history.items())
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load_json(cls, path: str | Path) -> "PerformanceHistoryStore":
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls(
            {
                agent_id: AgentPerformanceHistory.model_validate(history)
                for agent_id, history in payload.items()
            }
        )

    def _rolling_average(
        self,
        current: float,
        new_value: float | None,
        execution_count: int,
    ) -> float:
        if new_value is None:
            return current
        previous_count = max(execution_count - 1, 0)
        if previous_count == 0:
            return new_value
        return ((current * previous_count) + new_value) / execution_count

    def _coerce_float(self, value: object, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _coerce_int(self, value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
