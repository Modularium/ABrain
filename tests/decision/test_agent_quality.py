"""Tests for the canonical agent quality/trust scoring module (S8)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from core.decision.agent_descriptor import AgentAvailability, AgentTrustLevel
from core.decision.agent_quality import (
    MIN_EXECUTIONS,
    AgentQualitySummary,
    compute_agent_quality,
)
from core.decision.performance_history import AgentPerformanceHistory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _history(**kwargs) -> AgentPerformanceHistory:
    defaults = {
        "success_rate": 0.9,
        "avg_latency": 1.0,
        "avg_cost": 0.0,
        "avg_token_count": 0.0,
        "avg_user_rating": 0.0,
        "recent_failures": 0,
        "execution_count": MIN_EXECUTIONS,
        "load_factor": 0.0,
    }
    defaults.update(kwargs)
    return AgentPerformanceHistory(**defaults)


def _quality(
    availability: AgentAvailability = AgentAvailability.ONLINE,
    trust_level: AgentTrustLevel = AgentTrustLevel.TRUSTED,
    **history_kwargs,
) -> AgentQualitySummary:
    return compute_agent_quality(
        agent_id="test-agent",
        availability=availability,
        trust_level=trust_level,
        history=_history(**history_kwargs),
    )


# ---------------------------------------------------------------------------
# 1. Return type and basic structure
# ---------------------------------------------------------------------------

def test_returns_agent_quality_summary():
    result = _quality()
    assert isinstance(result, AgentQualitySummary)


def test_agent_id_preserved():
    result = compute_agent_quality(
        agent_id="my-agent-42",
        availability=AgentAvailability.ONLINE,
        trust_level=AgentTrustLevel.TRUSTED,
        history=_history(),
    )
    assert result.agent_id == "my-agent-42"


def test_quality_score_bounded():
    for avail in AgentAvailability:
        for trust in AgentTrustLevel:
            result = _quality(availability=avail, trust_level=trust)
            assert 0.0 <= result.quality_score <= 1.0


def test_quality_band_valid_literal():
    result = _quality()
    assert result.quality_band in {"good", "fair", "poor"}


def test_score_components_present():
    result = _quality()
    assert "success_component" in result.score_components
    assert "reliability_component" in result.score_components
    assert "availability_component" in result.score_components
    assert "rating_component" in result.score_components
    assert "trust_modifier" in result.score_components


# ---------------------------------------------------------------------------
# 2. Determinism
# ---------------------------------------------------------------------------

def test_deterministic_same_inputs():
    h = _history(success_rate=0.8, recent_failures=2, execution_count=10)
    r1 = compute_agent_quality("a", AgentAvailability.ONLINE, AgentTrustLevel.TRUSTED, h)
    r2 = compute_agent_quality("a", AgentAvailability.ONLINE, AgentTrustLevel.TRUSTED, h)
    assert r1.quality_score == r2.quality_score
    assert r1.quality_band == r2.quality_band
    assert r1.attention_flags == r2.attention_flags


# ---------------------------------------------------------------------------
# 3. data_sufficient protection (no unfair early penalisation)
# ---------------------------------------------------------------------------

def test_data_sufficient_false_when_low_execution_count():
    result = _quality(execution_count=0)
    assert result.data_sufficient is False


def test_data_sufficient_false_below_min():
    result = _quality(execution_count=MIN_EXECUTIONS - 1)
    assert result.data_sufficient is False


def test_data_sufficient_true_at_min():
    result = _quality(execution_count=MIN_EXECUTIONS)
    assert result.data_sufficient is True


def test_new_agent_not_penalised_for_zero_success_rate():
    """A new agent (execution_count=0) with success_rate=0 should get a neutral score."""
    result = _quality(execution_count=0, success_rate=0.0, recent_failures=0)
    assert result.data_sufficient is False
    # success_component neutral=0.5, reliability=1.0 → score should be reasonable
    assert result.quality_score >= 0.4, "new agents should not be labelled 'poor'"


def test_new_agent_gets_insufficient_data_flag():
    result = _quality(execution_count=0)
    assert "insufficient_data" in result.attention_flags


def test_established_agent_no_insufficient_data_flag():
    result = _quality(execution_count=MIN_EXECUTIONS)
    assert "insufficient_data" not in result.attention_flags


# ---------------------------------------------------------------------------
# 4. Attention flags
# ---------------------------------------------------------------------------

def test_offline_flag():
    result = _quality(availability=AgentAvailability.OFFLINE, execution_count=10)
    assert "offline" in result.attention_flags
    assert "degraded" not in result.attention_flags


def test_degraded_flag():
    result = _quality(availability=AgentAvailability.DEGRADED, execution_count=10)
    assert "degraded" in result.attention_flags
    assert "offline" not in result.attention_flags


def test_online_no_availability_flag():
    result = _quality(availability=AgentAvailability.ONLINE, execution_count=10)
    assert "offline" not in result.attention_flags
    assert "degraded" not in result.attention_flags


def test_high_recent_failures_flag():
    result = _quality(recent_failures=3, execution_count=10)
    assert "high_recent_failures" in result.attention_flags


def test_below_threshold_failures_no_flag():
    result = _quality(recent_failures=2, execution_count=10)
    assert "high_recent_failures" not in result.attention_flags


def test_low_success_rate_flag():
    result = _quality(success_rate=0.50, execution_count=10)
    assert "low_success_rate" in result.attention_flags


def test_adequate_success_rate_no_flag():
    result = _quality(success_rate=0.70, execution_count=10)
    assert "low_success_rate" not in result.attention_flags


def test_poor_user_rating_flag():
    result = _quality(avg_user_rating=2.0, execution_count=10)
    assert "poor_user_rating" in result.attention_flags


def test_good_user_rating_no_flag():
    result = _quality(avg_user_rating=4.0, execution_count=10)
    assert "poor_user_rating" not in result.attention_flags


def test_no_rating_no_poor_flag():
    result = _quality(avg_user_rating=0.0, execution_count=10)
    assert "poor_user_rating" not in result.attention_flags


def test_low_success_rate_not_flagged_when_insufficient_data():
    """low_success_rate flag must not fire when data is insufficient."""
    result = _quality(success_rate=0.1, execution_count=0)
    assert "low_success_rate" not in result.attention_flags


def test_poor_user_rating_not_flagged_when_insufficient_data():
    """poor_user_rating flag must not fire when data is insufficient."""
    result = _quality(avg_user_rating=1.0, execution_count=0)
    assert "poor_user_rating" not in result.attention_flags


# ---------------------------------------------------------------------------
# 5. Quality band thresholds
# ---------------------------------------------------------------------------

def test_good_band_high_quality():
    """Perfect agent: online, trusted, high success, no failures."""
    result = _quality(
        availability=AgentAvailability.ONLINE,
        trust_level=AgentTrustLevel.PRIVILEGED,
        success_rate=1.0,
        recent_failures=0,
        avg_user_rating=5.0,
        execution_count=20,
    )
    assert result.quality_band == "good"
    assert result.quality_score >= 0.70


def test_poor_band_offline_agent():
    """Offline agent with frequent failures should be 'poor'."""
    result = _quality(
        availability=AgentAvailability.OFFLINE,
        trust_level=AgentTrustLevel.SANDBOXED,
        success_rate=0.2,
        recent_failures=5,
        avg_user_rating=1.0,
        execution_count=20,
    )
    assert result.quality_band == "poor"
    assert result.quality_score < 0.40


def test_fair_band_degraded_moderate_success():
    result = _quality(
        availability=AgentAvailability.DEGRADED,
        trust_level=AgentTrustLevel.TRUSTED,
        success_rate=0.75,
        recent_failures=1,
        avg_user_rating=3.0,
        execution_count=15,
    )
    assert result.quality_band in {"good", "fair"}


# ---------------------------------------------------------------------------
# 6. Availability component values
# ---------------------------------------------------------------------------

def test_online_better_than_degraded():
    online = _quality(availability=AgentAvailability.ONLINE, execution_count=10)
    degraded = _quality(availability=AgentAvailability.DEGRADED, execution_count=10)
    assert online.quality_score > degraded.quality_score


def test_degraded_better_than_offline():
    degraded = _quality(availability=AgentAvailability.DEGRADED, execution_count=10)
    offline = _quality(availability=AgentAvailability.OFFLINE, execution_count=10)
    assert degraded.quality_score > offline.quality_score


def test_offline_component_is_zero():
    result = _quality(availability=AgentAvailability.OFFLINE, execution_count=10)
    assert result.score_components["availability_component"] == 0.0


def test_online_component_is_one():
    result = _quality(availability=AgentAvailability.ONLINE, execution_count=10)
    assert result.score_components["availability_component"] == 1.0


# ---------------------------------------------------------------------------
# 7. Trust modifier
# ---------------------------------------------------------------------------

def test_privileged_modifier_positive():
    result = _quality(trust_level=AgentTrustLevel.PRIVILEGED, execution_count=10)
    assert result.score_components["trust_modifier"] > 0.0


def test_trusted_modifier_zero():
    result = _quality(trust_level=AgentTrustLevel.TRUSTED, execution_count=10)
    assert result.score_components["trust_modifier"] == 0.0


def test_sandboxed_modifier_negative():
    result = _quality(trust_level=AgentTrustLevel.SANDBOXED, execution_count=10)
    assert result.score_components["trust_modifier"] < 0.0


def test_unknown_trust_modifier_zero():
    result = _quality(trust_level=AgentTrustLevel.UNKNOWN, execution_count=10)
    assert result.score_components["trust_modifier"] == 0.0


def test_privileged_beats_sandboxed_same_history():
    privileged = _quality(trust_level=AgentTrustLevel.PRIVILEGED, execution_count=10)
    sandboxed = _quality(trust_level=AgentTrustLevel.SANDBOXED, execution_count=10)
    assert privileged.quality_score > sandboxed.quality_score


# ---------------------------------------------------------------------------
# 8. Recent failures impact
# ---------------------------------------------------------------------------

def test_more_failures_lower_score():
    low = _quality(recent_failures=0, execution_count=10)
    high = _quality(recent_failures=4, execution_count=10)
    assert low.quality_score > high.quality_score


def test_many_failures_reliability_floored_at_zero():
    result = _quality(recent_failures=100, execution_count=20)
    assert result.score_components["reliability_component"] == 0.0


# ---------------------------------------------------------------------------
# 9. Rating impact
# ---------------------------------------------------------------------------

def test_high_rating_better_than_low():
    high = _quality(avg_user_rating=5.0, execution_count=10)
    low = _quality(avg_user_rating=1.0, execution_count=10)
    assert high.quality_score > low.quality_score


def test_rating_component_capped_at_one():
    result = _quality(avg_user_rating=10.0, execution_count=10)
    assert result.score_components["rating_component"] <= 1.0


# ---------------------------------------------------------------------------
# 10. Score clamping — never outside [0, 1]
# ---------------------------------------------------------------------------

def test_score_never_below_zero():
    result = _quality(
        availability=AgentAvailability.OFFLINE,
        trust_level=AgentTrustLevel.SANDBOXED,
        success_rate=0.0,
        recent_failures=100,
        avg_user_rating=0.0,
        execution_count=50,
    )
    assert result.quality_score >= 0.0


def test_score_never_above_one():
    result = _quality(
        availability=AgentAvailability.ONLINE,
        trust_level=AgentTrustLevel.PRIVILEGED,
        success_rate=1.0,
        recent_failures=0,
        avg_user_rating=5.0,
        execution_count=100,
    )
    assert result.quality_score <= 1.0


# ---------------------------------------------------------------------------
# 11. Pydantic model validation
# ---------------------------------------------------------------------------

def test_quality_summary_extra_fields_forbidden():
    with pytest.raises(Exception):
        AgentQualitySummary(
            agent_id="x",
            quality_score=0.8,
            quality_band="good",
            data_sufficient=True,
            execution_count=5,
            unexpected_field=True,
        )


def test_quality_score_must_be_in_bounds():
    with pytest.raises(Exception):
        AgentQualitySummary(
            agent_id="x",
            quality_score=1.5,
            quality_band="good",
            data_sufficient=True,
            execution_count=5,
        )


def test_execution_count_must_be_non_negative():
    with pytest.raises(Exception):
        AgentQualitySummary(
            agent_id="x",
            quality_score=0.8,
            quality_band="good",
            data_sufficient=True,
            execution_count=-1,
        )
