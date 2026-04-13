"""Canonical per-agent quality and trust summary for ABrain.

This module provides a single, deterministic, auditable quality summary for
each agent based on already-collected signals.  No new data store, no ML
model, no external dependency.

Formula
-------
quality_score = (
    success_component    * 0.50
  + reliability_component * 0.25
  + availability_component * 0.15
  + rating_component    * 0.10
) + trust_modifier        (clamped to [0.0, 1.0])

Components
----------
success_component     : ``history.success_rate``
                        Neutral 0.5 when ``data_sufficient`` is False.
reliability_component : ``max(0, 1 - recent_failures * RECENT_FAILURE_PENALTY)``
                        Neutral 1.0 when ``data_sufficient`` is False.
availability_component: ONLINE=1.0, UNKNOWN=0.7, DEGRADED=0.4, OFFLINE=0.0
rating_component      : ``avg_user_rating / 5.0``
                        Neutral 0.5 when no ratings present or data insufficient.

trust_modifier        : PRIVILEGED=+0.05, TRUSTED=0.0, SANDBOXED=-0.05, UNKNOWN=0.0

Bands
-----
"good" : quality_score >= 0.70
"fair" : quality_score >= 0.40
"poor" : quality_score <  0.40

``data_sufficient`` is True when ``execution_count >= MIN_EXECUTIONS`` (3).
New agents are protected from unfair penalisation via neutral component defaults
until enough samples have been collected.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .agent_descriptor import AgentAvailability, AgentTrustLevel
from .performance_history import AgentPerformanceHistory

# Minimum executions required before history data is considered reliable.
MIN_EXECUTIONS: int = 3

# Per-failure penalty applied to the reliability component.
_RECENT_FAILURE_PENALTY: float = 0.15

# Component weights — must sum to 1.0.
_W_SUCCESS: float = 0.50
_W_RELIABILITY: float = 0.25
_W_AVAILABILITY: float = 0.15
_W_RATING: float = 0.10

_AVAILABILITY_SCORE: dict[AgentAvailability, float] = {
    AgentAvailability.ONLINE: 1.0,
    AgentAvailability.UNKNOWN: 0.7,
    AgentAvailability.DEGRADED: 0.4,
    AgentAvailability.OFFLINE: 0.0,
}

_TRUST_MODIFIER: dict[AgentTrustLevel, float] = {
    AgentTrustLevel.PRIVILEGED: 0.05,
    AgentTrustLevel.TRUSTED: 0.0,
    AgentTrustLevel.SANDBOXED: -0.05,
    AgentTrustLevel.UNKNOWN: 0.0,
}


class AgentQualitySummary(BaseModel):
    """Auditable quality and trust summary for a single agent.

    All fields are deterministically derived from the agent descriptor and
    performance history.  ``score_components`` gives the full breakdown so
    operators can understand and verify the result.
    """

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    quality_score: float = Field(ge=0.0, le=1.0)
    quality_band: Literal["good", "fair", "poor"]
    score_components: dict[str, float] = Field(default_factory=dict)
    attention_flags: list[str] = Field(default_factory=list)
    data_sufficient: bool
    execution_count: int = Field(ge=0)


def compute_agent_quality(
    agent_id: str,
    availability: AgentAvailability,
    trust_level: AgentTrustLevel,
    history: AgentPerformanceHistory,
) -> AgentQualitySummary:
    """Compute a deterministic, auditable quality summary for a single agent.

    Parameters
    ----------
    agent_id:
        Canonical agent identifier (used verbatim in the result).
    availability:
        Current availability enum from the agent descriptor.
    trust_level:
        Trust level enum from the agent descriptor.
    history:
        Performance history from ``PerformanceHistoryStore.get()`` or
        ``get_for_descriptor()``.  Safe to call with an empty default.

    Returns
    -------
    AgentQualitySummary
        Fully populated summary with score, band, components, flags.
    """
    data_sufficient = history.execution_count >= MIN_EXECUTIONS

    # -- Component 1: success --------------------------------------------------
    success_component = history.success_rate if data_sufficient else 0.5

    # -- Component 2: reliability (recent failure streak) ----------------------
    if data_sufficient:
        reliability_component = max(
            0.0, 1.0 - history.recent_failures * _RECENT_FAILURE_PENALTY
        )
    else:
        reliability_component = 1.0  # neutral — no data yet

    # -- Component 3: availability ---------------------------------------------
    availability_component = _AVAILABILITY_SCORE.get(availability, 0.7)

    # -- Component 4: user rating (0–5 → 0–1) ----------------------------------
    if data_sufficient and history.avg_user_rating > 0.0:
        rating_component = min(history.avg_user_rating / 5.0, 1.0)
    else:
        rating_component = 0.5  # neutral when no ratings or insufficient data

    # -- Trust modifier (small additive, applied after weighted sum) -----------
    trust_modifier = _TRUST_MODIFIER.get(trust_level, 0.0)

    # -- Weighted sum + modifier, clamped to [0, 1] ----------------------------
    raw_score = (
        success_component * _W_SUCCESS
        + reliability_component * _W_RELIABILITY
        + availability_component * _W_AVAILABILITY
        + rating_component * _W_RATING
    )
    quality_score = max(0.0, min(1.0, raw_score + trust_modifier))

    # -- Band ------------------------------------------------------------------
    if quality_score >= 0.70:
        quality_band: Literal["good", "fair", "poor"] = "good"
    elif quality_score >= 0.40:
        quality_band = "fair"
    else:
        quality_band = "poor"

    # -- Attention flags -------------------------------------------------------
    attention_flags: list[str] = []
    if not data_sufficient:
        attention_flags.append("insufficient_data")
    if availability is AgentAvailability.OFFLINE:
        attention_flags.append("offline")
    elif availability is AgentAvailability.DEGRADED:
        attention_flags.append("degraded")
    if data_sufficient and history.recent_failures >= 3:
        attention_flags.append("high_recent_failures")
    if data_sufficient and history.success_rate < 0.60:
        attention_flags.append("low_success_rate")
    if (
        data_sufficient
        and history.avg_user_rating > 0.0
        and history.avg_user_rating < 2.5
    ):
        attention_flags.append("poor_user_rating")

    return AgentQualitySummary(
        agent_id=agent_id,
        quality_score=round(quality_score, 4),
        quality_band=quality_band,
        score_components={
            "success_component": round(success_component, 4),
            "reliability_component": round(reliability_component, 4),
            "availability_component": round(availability_component, 4),
            "rating_component": round(rating_component, 4),
            "trust_modifier": round(trust_modifier, 4),
        },
        attention_flags=attention_flags,
        data_sufficient=data_sufficient,
        execution_count=history.execution_count,
    )
