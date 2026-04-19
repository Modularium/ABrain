"""Agent performance report — read-only cost/latency/success snapshot.

Closes §6.5 Efficiency task *"Kosten pro Task und pro Modellpfad reporten"*
and extends §6.3 Observability *"Erfolgs-, Kosten-, Latenz-,
Sicherheitsmetriken"* with a per-agent surface.

This is a **read-only consumer** of the canonical
``PerformanceHistoryStore`` — the single source of truth for live per-agent
metrics on this repo.  It does not:

- write to or mutate the store;
- maintain a second history (no parallel truth);
- re-derive metrics from traces (that is ``core/evaluation/``'s job and
  scoped to stored traces, not live per-agent state).

It bundles the per-agent views into a structured ``AgentPerformanceReport``
with optional cost-/latency-/success-based sorting and aggregate totals, so
operators have a one-call "what is each agent path currently costing us"
snapshot.

Stdlib + pydantic only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .performance_history import AgentPerformanceHistory, PerformanceHistoryStore

SortKey = Literal[
    "avg_cost",
    "avg_latency",
    "success_rate",
    "execution_count",
    "agent_id",
]


class AgentPerformanceEntry(BaseModel):
    """Flat per-agent performance snapshot."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    success_rate: float = Field(ge=0.0, le=1.0)
    avg_latency: float = Field(ge=0.0)
    avg_cost: float = Field(ge=0.0)
    avg_token_count: float = Field(ge=0.0)
    avg_user_rating: float = Field(ge=0.0)
    recent_failures: int = Field(ge=0)
    execution_count: int = Field(ge=0)
    load_factor: float = Field(ge=0.0, le=1.0)


class AgentPerformanceTotals(BaseModel):
    """Aggregate totals across reported agents."""

    model_config = ConfigDict(extra="forbid")

    agents: int = Field(ge=0)
    total_executions: int = Field(ge=0)
    total_recent_failures: int = Field(ge=0)
    weighted_success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="execution_count-weighted success_rate across agents (0.0 when total_executions == 0)",
    )
    weighted_avg_latency: float = Field(
        ge=0.0,
        description="execution_count-weighted avg_latency (0.0 when total_executions == 0)",
    )
    weighted_avg_cost: float = Field(
        ge=0.0,
        description="execution_count-weighted avg_cost (0.0 when total_executions == 0)",
    )


class AgentPerformanceReport(BaseModel):
    """Composed per-agent performance report with aggregates."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    sort_key: SortKey
    descending: bool
    min_executions: int = Field(ge=0)
    entries: list[AgentPerformanceEntry] = Field(default_factory=list)
    totals: AgentPerformanceTotals


class AgentPerformanceReporter:
    """Build ``AgentPerformanceReport`` snapshots from a ``PerformanceHistoryStore``.

    Parameters
    ----------
    store:
        Canonical ``PerformanceHistoryStore``.  Read-only usage.
    """

    def __init__(self, *, store: PerformanceHistoryStore) -> None:
        self.store = store

    def generate(
        self,
        *,
        sort_key: SortKey = "avg_cost",
        descending: bool = True,
        min_executions: int = 0,
        agent_ids: list[str] | None = None,
    ) -> AgentPerformanceReport:
        """Snapshot the store into a sorted, filtered report.

        Parameters
        ----------
        sort_key:
            Which entry field to sort by.  Defaults to ``avg_cost`` — the
            most operator-relevant axis for §6.5 Efficiency.
        descending:
            Direction of the sort.  ``True`` (default) puts the largest
            cost / latency / highest-activity agent first.
        min_executions:
            Filter out agents with fewer than ``min_executions`` recorded
            runs.  Default ``0`` (include all).  Useful to ignore
            bootstrap entries with no real data yet.
        agent_ids:
            Optional explicit allow-list.  When ``None`` (default), every
            agent in the store is included.  Agents in the list but missing
            from the store are surfaced with their store default values (via
            ``store.get``) so operators see the full requested slice.
        """
        if agent_ids is not None:
            raw: dict[str, AgentPerformanceHistory] = {
                aid: self.store.get(aid) for aid in agent_ids
            }
        else:
            raw = self.store.snapshot()

        entries = [
            _entry_from_history(agent_id, history)
            for agent_id, history in raw.items()
            if history.execution_count >= min_executions
        ]
        entries.sort(key=_sort_key_fn(sort_key), reverse=descending)

        totals = _compute_totals(entries)

        return AgentPerformanceReport(
            generated_at=datetime.now(UTC),
            sort_key=sort_key,
            descending=descending,
            min_executions=min_executions,
            entries=entries,
            totals=totals,
        )


def _entry_from_history(
    agent_id: str, history: AgentPerformanceHistory
) -> AgentPerformanceEntry:
    return AgentPerformanceEntry(
        agent_id=agent_id,
        success_rate=history.success_rate,
        avg_latency=history.avg_latency,
        avg_cost=history.avg_cost,
        avg_token_count=history.avg_token_count,
        avg_user_rating=history.avg_user_rating,
        recent_failures=history.recent_failures,
        execution_count=history.execution_count,
        load_factor=history.load_factor,
    )


def _sort_key_fn(key: SortKey):
    if key == "agent_id":
        return lambda e: e.agent_id
    return lambda e: getattr(e, key)


def _compute_totals(entries: list[AgentPerformanceEntry]) -> AgentPerformanceTotals:
    total_executions = sum(e.execution_count for e in entries)
    total_recent_failures = sum(e.recent_failures for e in entries)
    if total_executions == 0:
        return AgentPerformanceTotals(
            agents=len(entries),
            total_executions=0,
            total_recent_failures=total_recent_failures,
            weighted_success_rate=0.0,
            weighted_avg_latency=0.0,
            weighted_avg_cost=0.0,
        )
    weighted_success = sum(e.success_rate * e.execution_count for e in entries) / total_executions
    weighted_latency = sum(e.avg_latency * e.execution_count for e in entries) / total_executions
    weighted_cost = sum(e.avg_cost * e.execution_count for e in entries) / total_executions
    return AgentPerformanceTotals(
        agents=len(entries),
        total_executions=total_executions,
        total_recent_failures=total_recent_failures,
        weighted_success_rate=min(1.0, max(0.0, weighted_success)),
        weighted_avg_latency=max(0.0, weighted_latency),
        weighted_avg_cost=max(0.0, weighted_cost),
    )


__all__ = [
    "AgentPerformanceEntry",
    "AgentPerformanceReport",
    "AgentPerformanceReporter",
    "AgentPerformanceTotals",
    "SortKey",
]
