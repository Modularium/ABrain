"""Energy-consumption report per model path — §6.5 Green AI.

Read-only estimator that composes with the canonical
``PerformanceHistoryStore``. For each agent, energy is derived from:

    avg_energy_joules   = avg_power_watts * avg_latency_seconds
    total_energy_joules = avg_energy_joules * execution_count
    total_energy_wh     = total_energy_joules / 3600

``avg_power_watts`` comes from an ``EnergyProfile`` — a per-agent
wattage constant (e.g. GPU active draw during inference). Profiles are
looked up by ``agent_id``; agents without an explicit profile fall back
to the config's ``default_profile`` and are counted in
``report.fallback_agents`` so operators can see which model paths lack
measured constants.

Design invariants
-----------------
- **Single source of truth.** All metrics come from
  ``PerformanceHistoryStore`` via ``store.snapshot()`` / ``store.get()``.
  No second per-agent history, no re-derivation from traces.
- **Read-only.** The estimator never mutates the store or its records.
- **Pure estimation.** Wattage is operator-supplied, not measured — the
  report is explicit about this via ``EnergyProfile.source`` and
  ``report.fallback_agents``.
- **Additive.** One new module; re-exports only. No new dependencies
  (stdlib + pydantic).

Composes with:

- ``AgentPerformanceReporter`` (§6.5 cost reporting) — same store,
  orthogonal axis (cost vs. energy).
- ``PerformanceHistoryStore.record_result(..., latency=...)`` — the
  latency signal the estimator multiplies by wattage.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .performance_history import AgentPerformanceHistory, PerformanceHistoryStore

EnergySortKey = Literal[
    "total_energy_joules",
    "avg_energy_joules",
    "avg_power_watts",
    "execution_count",
    "agent_id",
]

ProfileSource = Literal["measured", "vendor_spec", "estimated"]

_SECONDS_PER_HOUR = 3600.0


class EnergyProfile(BaseModel):
    """Wattage constant attached to a model path.

    ``avg_power_watts`` is the average active power draw during
    inference — typically GPU wattage for hosted models, CPU TDP for
    local ones. The ``source`` field records how the number was
    obtained so the report is honest about its fidelity:

    - ``measured``    — observed from a power meter / provider API;
    - ``vendor_spec`` — from a datasheet (e.g. H100 TDP 700 W);
    - ``estimated``   — best-effort guess, flagged for review.
    """

    model_config = ConfigDict(extra="forbid")

    avg_power_watts: float = Field(
        ge=0.0,
        le=100_000.0,
        description=(
            "Average active power draw in watts while the model path is "
            "serving a request. 0.0 is allowed but produces a zero report."
        ),
    )
    source: ProfileSource = Field(
        default="estimated",
        description=(
            "How the wattage was obtained. 'estimated' entries should be "
            "flagged for operator review before the report is trusted."
        ),
    )


class EnergyEstimatorConfig(BaseModel):
    """Configuration for :class:`EnergyEstimator`.

    ``profiles`` is the per-agent override map. Agents not present in
    ``profiles`` are estimated with ``default_profile`` and counted in
    ``report.fallback_agents``.
    """

    model_config = ConfigDict(extra="forbid")

    default_profile: EnergyProfile
    profiles: dict[str, EnergyProfile] = Field(default_factory=dict)


class AgentEnergyEstimate(BaseModel):
    """Per-agent energy snapshot."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    avg_power_watts: float = Field(ge=0.0)
    profile_source: ProfileSource
    used_default_profile: bool = Field(
        description=(
            "True when the agent was estimated with the default profile "
            "(no explicit override). These agents are surfaced in "
            "report.fallback_agents for operator follow-up."
        ),
    )
    avg_latency_seconds: float = Field(ge=0.0)
    execution_count: int = Field(ge=0)
    avg_energy_joules: float = Field(
        ge=0.0,
        description="avg_power_watts * avg_latency_seconds",
    )
    total_energy_joules: float = Field(
        ge=0.0,
        description="avg_energy_joules * execution_count",
    )
    total_energy_wh: float = Field(
        ge=0.0,
        description="total_energy_joules / 3600",
    )


class EnergyTotals(BaseModel):
    """Aggregate totals across reported agents."""

    model_config = ConfigDict(extra="forbid")

    agents: int = Field(ge=0)
    total_executions: int = Field(ge=0)
    total_energy_joules: float = Field(ge=0.0)
    total_energy_wh: float = Field(ge=0.0)
    weighted_avg_power_watts: float = Field(
        ge=0.0,
        description=(
            "execution_count-weighted avg_power_watts across agents "
            "(0.0 when total_executions == 0)."
        ),
    )


class EnergyReport(BaseModel):
    """Composed per-agent energy report with aggregates.

    ``fallback_agents`` is the subset of entries that were estimated
    using ``config.default_profile`` because no explicit per-agent
    profile was configured. Non-empty means operators should widen their
    wattage coverage before trusting the totals unreservedly.
    """

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    sort_key: EnergySortKey
    descending: bool
    min_executions: int = Field(ge=0)
    entries: list[AgentEnergyEstimate] = Field(default_factory=list)
    totals: EnergyTotals
    fallback_agents: list[str] = Field(default_factory=list)


class EnergyEstimator:
    """Build :class:`EnergyReport` snapshots from a ``PerformanceHistoryStore``.

    Parameters
    ----------
    store:
        Canonical ``PerformanceHistoryStore``. Read-only usage.
    config:
        Wattage profiles — per-agent overrides + default.
    """

    def __init__(
        self,
        *,
        store: PerformanceHistoryStore,
        config: EnergyEstimatorConfig,
    ) -> None:
        self.store = store
        self.config = config

    def generate(
        self,
        *,
        sort_key: EnergySortKey = "total_energy_joules",
        descending: bool = True,
        min_executions: int = 0,
        agent_ids: list[str] | None = None,
    ) -> EnergyReport:
        """Snapshot the store into a sorted, filtered energy report.

        Parameters
        ----------
        sort_key:
            Which entry field to sort by. Default ``total_energy_joules``
            — the most operator-relevant axis for §6.5 Green AI.
        descending:
            Sort direction. ``True`` (default) puts the biggest energy
            consumer first.
        min_executions:
            Drop agents with fewer than ``min_executions`` runs. Default
            ``0`` (include all).
        agent_ids:
            Optional allow-list. When ``None`` (default), every agent
            currently in the store is reported.
        """
        if agent_ids is not None:
            raw: dict[str, AgentPerformanceHistory] = {
                aid: self.store.get(aid) for aid in agent_ids
            }
        else:
            raw = self.store.snapshot()

        entries: list[AgentEnergyEstimate] = []
        fallback: list[str] = []
        for agent_id, history in raw.items():
            if history.execution_count < min_executions:
                continue
            profile, used_default = self._resolve_profile(agent_id)
            if used_default:
                fallback.append(agent_id)
            entries.append(_estimate(agent_id, history, profile, used_default))

        entries.sort(key=_sort_key_fn(sort_key), reverse=descending)
        totals = _compute_totals(entries)
        fallback.sort()

        return EnergyReport(
            generated_at=datetime.now(UTC),
            sort_key=sort_key,
            descending=descending,
            min_executions=min_executions,
            entries=entries,
            totals=totals,
            fallback_agents=fallback,
        )

    def _resolve_profile(self, agent_id: str) -> tuple[EnergyProfile, bool]:
        override = self.config.profiles.get(agent_id)
        if override is not None:
            return override, False
        return self.config.default_profile, True


def _estimate(
    agent_id: str,
    history: AgentPerformanceHistory,
    profile: EnergyProfile,
    used_default: bool,
) -> AgentEnergyEstimate:
    avg_energy = profile.avg_power_watts * history.avg_latency
    total_energy = avg_energy * history.execution_count
    return AgentEnergyEstimate(
        agent_id=agent_id,
        avg_power_watts=profile.avg_power_watts,
        profile_source=profile.source,
        used_default_profile=used_default,
        avg_latency_seconds=history.avg_latency,
        execution_count=history.execution_count,
        avg_energy_joules=avg_energy,
        total_energy_joules=total_energy,
        total_energy_wh=total_energy / _SECONDS_PER_HOUR,
    )


def _sort_key_fn(key: EnergySortKey):
    if key == "agent_id":
        return lambda e: e.agent_id
    return lambda e: getattr(e, key)


def _compute_totals(entries: list[AgentEnergyEstimate]) -> EnergyTotals:
    total_executions = sum(e.execution_count for e in entries)
    total_joules = sum(e.total_energy_joules for e in entries)
    if total_executions == 0:
        weighted_watts = 0.0
    else:
        weighted_watts = (
            sum(e.avg_power_watts * e.execution_count for e in entries)
            / total_executions
        )
    return EnergyTotals(
        agents=len(entries),
        total_executions=total_executions,
        total_energy_joules=total_joules,
        total_energy_wh=total_joules / _SECONDS_PER_HOUR,
        weighted_avg_power_watts=max(0.0, weighted_watts),
    )


__all__ = [
    "AgentEnergyEstimate",
    "EnergyEstimator",
    "EnergyEstimatorConfig",
    "EnergyProfile",
    "EnergyReport",
    "EnergySortKey",
    "EnergyTotals",
    "ProfileSource",
]
