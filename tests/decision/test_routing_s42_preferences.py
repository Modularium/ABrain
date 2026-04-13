"""Tests for Phase S4.2 — Routing Preferences: health penalty, cost tie-breaking, confidence metrics.

Coverage:
 - _apply_degraded_penalty: DEGRADED agents re-sorted; ONLINE agents untouched; multiplier=1.0 no-op
 - _apply_cost_tiebreak: cheaper agent wins within band; out-of-band order preserved; band=0 no-op
 - _compute_routing_metrics: confidence, gap, band classification (high/medium/low)
 - RoutingPreferences defaults; field constraints
 - RoutingEngine.route_intent: new fields populated on RoutingDecision
 - RoutingDecision: new optional fields (routing_confidence, score_gap, confidence_band)
 - RoutingEngine.__init__: preferences kwarg; defaults to RoutingPreferences()
 - No governance bypass, no S4 fallback interference
"""

from __future__ import annotations

import pytest

from core.decision import (
    AgentAvailability,
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
    RoutingEngine,
    RoutingPreferences,
)
from core.decision.routing_engine import (
    _apply_cost_tiebreak,
    _apply_degraded_penalty,
    _compute_routing_metrics,
)
from core.decision.neural_policy import ScoredCandidate
from core.decision.feature_encoder import EncodedCandidateFeatures
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_scored(agent_id: str, score: float) -> ScoredCandidate:
    ef = EncodedCandidateFeatures(agent_id=agent_id, feature_map={}, vector=[])
    return ScoredCandidate(
        agent_id=agent_id,
        display_name=agent_id,
        score=score,
        encoded_features=ef,
        model_source="heuristic",
    )


def build_descriptor(
    agent_id: str,
    *,
    availability: AgentAvailability = AgentAvailability.ONLINE,
    cost_profile: AgentCostProfile = AgentCostProfile.MEDIUM,
    capabilities: list[str] | None = None,
    trust_level: AgentTrustLevel = AgentTrustLevel.SANDBOXED,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=capabilities or ["analysis"],
        trust_level=trust_level,
        availability=availability,
        cost_profile=cost_profile,
    )


# ---------------------------------------------------------------------------
# _apply_degraded_penalty
# ---------------------------------------------------------------------------


def test_degraded_penalty_reorders_degraded_agent_behind_online():
    """DEGRADED agent with higher raw score should drop behind ONLINE after penalty."""
    scored = [make_scored("degraded-top", 0.9), make_scored("online-second", 0.8)]
    descriptors_by_id = {
        "degraded-top": build_descriptor("degraded-top", availability=AgentAvailability.DEGRADED),
        "online-second": build_descriptor("online-second", availability=AgentAvailability.ONLINE),
    }
    result = _apply_degraded_penalty(scored, descriptors_by_id, multiplier=0.85)
    # 0.9 * 0.85 = 0.765 < 0.8 → online-second should now be first
    assert result[0].agent_id == "online-second"
    assert result[1].agent_id == "degraded-top"
    assert abs(result[1].score - 0.765) < 1e-9


def test_degraded_penalty_multiplier_one_is_noop():
    """multiplier=1.0 must return the list unchanged (same objects)."""
    scored = [make_scored("degraded", 0.9), make_scored("online", 0.8)]
    descriptors_by_id = {
        "degraded": build_descriptor("degraded", availability=AgentAvailability.DEGRADED),
        "online": build_descriptor("online", availability=AgentAvailability.ONLINE),
    }
    result = _apply_degraded_penalty(scored, descriptors_by_id, multiplier=1.0)
    assert result is scored  # same object — no copy made


def test_degraded_penalty_online_agents_score_untouched():
    """ONLINE agents must NOT have their scores altered."""
    scored = [make_scored("a", 0.8), make_scored("b", 0.7)]
    descriptors_by_id = {
        "a": build_descriptor("a", availability=AgentAvailability.ONLINE),
        "b": build_descriptor("b", availability=AgentAvailability.ONLINE),
    }
    result = _apply_degraded_penalty(scored, descriptors_by_id, multiplier=0.85)
    assert result[0].score == 0.8
    assert result[1].score == 0.7


def test_degraded_penalty_empty_list():
    assert _apply_degraded_penalty([], {}, multiplier=0.85) == []


def test_degraded_penalty_missing_descriptor_skips_penalty():
    """Agent not in descriptors_by_id must not receive a penalty (safe default)."""
    scored = [make_scored("unknown", 0.9)]
    result = _apply_degraded_penalty(scored, {}, multiplier=0.85)
    assert result[0].score == 0.9


def test_degraded_penalty_does_not_mutate_input():
    """Original ScoredCandidate objects must not be mutated."""
    original_score = 0.9
    scored = [make_scored("degraded", original_score)]
    descriptors_by_id = {
        "degraded": build_descriptor("degraded", availability=AgentAvailability.DEGRADED),
    }
    _apply_degraded_penalty(scored, descriptors_by_id, multiplier=0.85)
    assert scored[0].score == original_score  # original unchanged


# ---------------------------------------------------------------------------
# _apply_cost_tiebreak
# ---------------------------------------------------------------------------


def test_cost_tiebreak_prefers_low_over_medium_in_band():
    """Within the score band LOW-cost agent should win over MEDIUM-cost agent."""
    scored = [make_scored("medium-cost", 0.80), make_scored("low-cost", 0.78)]
    descriptors_by_id = {
        "medium-cost": build_descriptor("medium-cost", cost_profile=AgentCostProfile.MEDIUM),
        "low-cost": build_descriptor("low-cost", cost_profile=AgentCostProfile.LOW),
    }
    result = _apply_cost_tiebreak(scored, descriptors_by_id, band=0.05)
    assert result[0].agent_id == "low-cost"


def test_cost_tiebreak_out_of_band_agent_stays_behind():
    """Agent outside the score band must not be promoted even if cheapest."""
    scored = [
        make_scored("top", 0.90),
        make_scored("mid", 0.86),
        make_scored("cheap-far", 0.70),  # 0.90 - 0.70 = 0.20 > band 0.05
    ]
    descriptors_by_id = {
        "top": build_descriptor("top", cost_profile=AgentCostProfile.HIGH),
        "mid": build_descriptor("mid", cost_profile=AgentCostProfile.MEDIUM),
        "cheap-far": build_descriptor("cheap-far", cost_profile=AgentCostProfile.LOW),
    }
    result = _apply_cost_tiebreak(scored, descriptors_by_id, band=0.05)
    # cheap-far is out of band; only top vs mid are re-ordered
    assert result[-1].agent_id == "cheap-far"


def test_cost_tiebreak_band_zero_is_noop():
    """band=0.0 must not change any order (only one candidate 'in band' at most)."""
    scored = [make_scored("high-cost", 0.9), make_scored("low-cost", 0.88)]
    descriptors_by_id = {
        "high-cost": build_descriptor("high-cost", cost_profile=AgentCostProfile.HIGH),
        "low-cost": build_descriptor("low-cost", cost_profile=AgentCostProfile.LOW),
    }
    result = _apply_cost_tiebreak(scored, descriptors_by_id, band=0.0)
    assert result[0].agent_id == "high-cost"


def test_cost_tiebreak_single_candidate():
    scored = [make_scored("only", 0.8)]
    descriptors_by_id = {"only": build_descriptor("only")}
    result = _apply_cost_tiebreak(scored, descriptors_by_id, band=0.05)
    assert result is scored


def test_cost_tiebreak_cost_order_low_medium_unknown_variable_high():
    """Full cost order: LOW < MEDIUM < UNKNOWN < VARIABLE < HIGH."""
    scores = [0.80, 0.79, 0.78, 0.77, 0.76]
    cost_order = [
        AgentCostProfile.HIGH,
        AgentCostProfile.VARIABLE,
        AgentCostProfile.UNKNOWN,
        AgentCostProfile.MEDIUM,
        AgentCostProfile.LOW,
    ]
    scored = [make_scored(f"agent-{i}", s) for i, s in enumerate(scores)]
    descriptors_by_id = {
        f"agent-{i}": build_descriptor(f"agent-{i}", cost_profile=cp)
        for i, cp in enumerate(cost_order)
    }
    result = _apply_cost_tiebreak(scored, descriptors_by_id, band=0.10)
    result_ids = [c.agent_id for c in result]
    # Expect LOW first, then MEDIUM, UNKNOWN, VARIABLE, HIGH last
    expected_first = "agent-4"  # AgentCostProfile.LOW
    expected_last = "agent-0"   # AgentCostProfile.HIGH
    assert result_ids[0] == expected_first
    assert result_ids[-1] == expected_last


# ---------------------------------------------------------------------------
# _compute_routing_metrics
# ---------------------------------------------------------------------------


def test_compute_metrics_empty_returns_nones():
    confidence, gap, band = _compute_routing_metrics([])
    assert confidence is None
    assert gap is None
    assert band is None


def test_compute_metrics_single_candidate_gap_is_zero():
    scored = [make_scored("a", 0.8)]
    confidence, gap, band = _compute_routing_metrics(scored)
    assert confidence == pytest.approx(0.8)
    assert gap == pytest.approx(0.0)
    assert band == "high"  # 0.8 >= 0.65 → high


def test_compute_metrics_high_band_at_or_above_065():
    scored = [make_scored("a", 0.70), make_scored("b", 0.60)]
    confidence, gap, band = _compute_routing_metrics(scored)
    assert confidence == pytest.approx(0.70)
    assert gap == pytest.approx(0.10)
    assert band == "high"


def test_compute_metrics_medium_band_035_to_065():
    scored = [make_scored("a", 0.50), make_scored("b", 0.40)]
    confidence, gap, band = _compute_routing_metrics(scored)
    assert band == "medium"


def test_compute_metrics_low_band_below_035():
    scored = [make_scored("a", 0.20), make_scored("b", 0.10)]
    confidence, gap, band = _compute_routing_metrics(scored)
    assert confidence == pytest.approx(0.20)
    assert band == "low"


def test_compute_metrics_exactly_065_is_high():
    scored = [make_scored("a", 0.65)]
    _, _, band = _compute_routing_metrics(scored)
    assert band == "high"


def test_compute_metrics_exactly_035_is_medium():
    scored = [make_scored("a", 0.35)]
    _, _, band = _compute_routing_metrics(scored)
    assert band == "medium"


# ---------------------------------------------------------------------------
# RoutingPreferences model
# ---------------------------------------------------------------------------


def test_routing_preferences_defaults():
    prefs = RoutingPreferences()
    assert prefs.degraded_availability_penalty == pytest.approx(0.85)
    assert prefs.cost_tie_band == pytest.approx(0.05)
    assert prefs.low_confidence_threshold == pytest.approx(0.0)


def test_routing_preferences_custom_values():
    prefs = RoutingPreferences(degraded_availability_penalty=0.5, cost_tie_band=0.10)
    assert prefs.degraded_availability_penalty == pytest.approx(0.5)
    assert prefs.cost_tie_band == pytest.approx(0.10)


def test_routing_preferences_penalty_out_of_range():
    with pytest.raises(Exception):
        RoutingPreferences(degraded_availability_penalty=1.5)


def test_routing_preferences_no_extra_fields():
    with pytest.raises(Exception):
        RoutingPreferences(unknown_field=True)


# ---------------------------------------------------------------------------
# RoutingEngine.__init__ preferences kwarg
# ---------------------------------------------------------------------------


def test_routing_engine_default_preferences():
    engine = RoutingEngine()
    assert isinstance(engine.preferences, RoutingPreferences)
    assert engine.preferences.degraded_availability_penalty == pytest.approx(0.85)


def test_routing_engine_accepts_custom_preferences():
    prefs = RoutingPreferences(degraded_availability_penalty=0.5, cost_tie_band=0.0)
    engine = RoutingEngine(preferences=prefs)
    assert engine.preferences is prefs


# ---------------------------------------------------------------------------
# RoutingDecision new fields
# ---------------------------------------------------------------------------


def test_routing_decision_confidence_fields_populated():
    """End-to-end: route_intent should populate confidence metrics."""
    engine = RoutingEngine(preferences=RoutingPreferences(degraded_availability_penalty=1.0, cost_tie_band=0.0))
    # Planner maps task_type="analysis" → requires "analysis.general" capability
    task = TaskContext(task_type="analysis", description="Analyse something")
    descriptors = [
        build_descriptor(
            "alpha",
            capabilities=["analysis.general"],
            trust_level=AgentTrustLevel.TRUSTED,
            availability=AgentAvailability.ONLINE,
        ),
        build_descriptor(
            "beta",
            capabilities=["analysis.general"],
            trust_level=AgentTrustLevel.TRUSTED,
            availability=AgentAvailability.ONLINE,
        ),
    ]
    decision = engine.route(task, descriptors)
    assert decision.routing_confidence is not None
    assert decision.score_gap is not None
    assert decision.confidence_band in {"high", "medium", "low"}
    assert 0.0 <= decision.routing_confidence <= 1.0
    assert decision.score_gap >= 0.0


def test_routing_decision_no_candidates_fields_are_none():
    """When all candidates are rejected, confidence fields must be None."""
    engine = RoutingEngine()
    task = TaskContext(task_type="analysis", description="Analyse")
    # No descriptors → no candidates
    decision = engine.route(task, [])
    assert decision.routing_confidence is None
    assert decision.score_gap is None
    assert decision.confidence_band is None


# ---------------------------------------------------------------------------
# End-to-end: DEGRADED penalty applied via RoutingEngine
# ---------------------------------------------------------------------------


def test_engine_demotes_degraded_agent_end_to_end():
    """DEGRADED agent with higher raw capability score should be demoted by penalty."""
    prefs = RoutingPreferences(degraded_availability_penalty=0.50, cost_tie_band=0.0)
    engine = RoutingEngine(preferences=prefs)
    # Planner maps code_review → requires ["analysis.code", "review.code"]
    task = TaskContext(task_type="code_review", description="Review this code")
    descriptors = [
        # Both agents are capable; degraded-high has better history but is DEGRADED
        AgentDescriptor(
            agent_id="degraded-high",
            display_name="Degraded High",
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=["analysis.code", "review.code"],
            trust_level=AgentTrustLevel.TRUSTED,
            availability=AgentAvailability.DEGRADED,
            metadata={"success_rate": 0.98, "estimated_cost_per_token": 0.001, "avg_response_time": 1.0},
        ),
        AgentDescriptor(
            agent_id="online-lower",
            display_name="Online Lower",
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=["analysis.code", "review.code"],
            trust_level=AgentTrustLevel.TRUSTED,
            availability=AgentAvailability.ONLINE,
            metadata={"success_rate": 0.80, "estimated_cost_per_token": 0.001, "avg_response_time": 1.0},
        ),
    ]
    decision = engine.route(task, descriptors)
    # With 50% penalty, even a high-scoring DEGRADED agent should lose to ONLINE
    assert decision.selected_agent_id == "online-lower"


# ---------------------------------------------------------------------------
# End-to-end: cost tie-breaking applied via RoutingEngine
# ---------------------------------------------------------------------------


def test_engine_applies_cost_tiebreak_end_to_end():
    """Within the tie band, the lower-cost agent should be preferred."""
    prefs = RoutingPreferences(degraded_availability_penalty=1.0, cost_tie_band=0.15)
    engine = RoutingEngine(preferences=prefs)
    # Planner maps task_type="analysis" → requires "analysis.general"
    task = TaskContext(task_type="analysis", description="Analyse something")
    # Two equally capable ONLINE agents; low-cost has slightly lower raw score
    descriptors = [
        AgentDescriptor(
            agent_id="high-cost-leader",
            display_name="High Cost Leader",
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=["analysis.general"],
            trust_level=AgentTrustLevel.TRUSTED,
            availability=AgentAvailability.ONLINE,
            cost_profile=AgentCostProfile.HIGH,
            metadata={"success_rate": 0.92, "estimated_cost_per_token": 0.05, "avg_response_time": 1.0},
        ),
        AgentDescriptor(
            agent_id="low-cost-runner-up",
            display_name="Low Cost Runner-up",
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=["analysis.general"],
            trust_level=AgentTrustLevel.TRUSTED,
            availability=AgentAvailability.ONLINE,
            cost_profile=AgentCostProfile.LOW,
            metadata={"success_rate": 0.88, "estimated_cost_per_token": 0.001, "avg_response_time": 1.2},
        ),
    ]
    decision = engine.route(task, descriptors)
    # LOW-cost agent should win the tie-break if scores are within 15%
    assert decision.selected_agent_id == "low-cost-runner-up"
