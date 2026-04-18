"""Phase 6 – Brain v1 B6-S1: BrainState schema + BrainStateEncoder tests."""

from __future__ import annotations

import pytest

from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
    RoutingEngine,
)
from core.decision.brain.encoder import BrainStateEncoder, _AVAILABILITY_ORD, _TRUST_ORD
from core.decision.brain.state import (
    BrainAgentSignal,
    BrainBudget,
    BrainPolicySignals,
    BrainRecord,
    BrainState,
    BrainTarget,
)
from core.decision.capabilities import CapabilityRisk
from core.decision.performance_history import AgentPerformanceHistory, PerformanceHistoryStore
from core.decision.task_intent import TaskIntent
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _descriptor(
    agent_id: str,
    *,
    capabilities: list[str] | None = None,
    trust_level: AgentTrustLevel = AgentTrustLevel.TRUSTED,
    availability: AgentAvailability = AgentAvailability.ONLINE,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=capabilities or ["analysis.code"],
        trust_level=trust_level,
        availability=availability,
        metadata={"success_rate": 0.9, "estimated_cost_per_token": 0.001, "avg_response_time": 1.0},
    )


def _intent(
    task_type: str = "code_review",
    *,
    domain: str = "engineering",
    capabilities: list[str] | None = None,
    risk: CapabilityRisk = CapabilityRisk.LOW,
) -> TaskIntent:
    return TaskIntent(
        task_type=task_type,
        domain=domain,
        required_capabilities=capabilities or ["analysis.code"],
        risk=risk,
    )


def _make_encoder() -> BrainStateEncoder:
    return BrainStateEncoder()


# ---------------------------------------------------------------------------
# BrainBudget schema
# ---------------------------------------------------------------------------


class TestBrainBudget:
    def test_defaults_are_unconstrained(self):
        b = BrainBudget()
        assert b.budget_usd is None
        assert b.time_budget_ms is None
        assert b.max_agents == 1

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainBudget(unknown="x")  # type: ignore[call-arg]

    def test_budget_usd_non_negative(self):
        with pytest.raises(Exception):
            BrainBudget(budget_usd=-1.0)

    def test_max_agents_at_least_one(self):
        with pytest.raises(Exception):
            BrainBudget(max_agents=0)


# ---------------------------------------------------------------------------
# BrainPolicySignals schema
# ---------------------------------------------------------------------------


class TestBrainPolicySignals:
    def test_defaults_no_policy_effect(self):
        p = BrainPolicySignals()
        assert p.has_policy_effect is False
        assert p.approval_required is False
        assert p.matched_policy_ids == []

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainPolicySignals(unknown="x")  # type: ignore[call-arg]

    def test_policy_ids_stored(self):
        p = BrainPolicySignals(has_policy_effect=True, matched_policy_ids=["p1", "p2"])
        assert p.matched_policy_ids == ["p1", "p2"]


# ---------------------------------------------------------------------------
# BrainAgentSignal schema
# ---------------------------------------------------------------------------


class TestBrainAgentSignal:
    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainAgentSignal(
                agent_id="a",
                capability_match_score=1.0,
                success_rate=0.9,
                avg_latency_s=1.0,
                avg_cost_usd=0.001,
                recent_failures=0,
                execution_count=10,
                load_factor=0.1,
                trust_level_ord=0.67,
                availability_ord=1.0,
                unknown="x",  # type: ignore[call-arg]
            )

    def test_capability_match_clamped(self):
        with pytest.raises(Exception):
            BrainAgentSignal(
                agent_id="a",
                capability_match_score=1.5,  # > 1.0
                success_rate=0.9,
                avg_latency_s=1.0,
                avg_cost_usd=0.0,
                recent_failures=0,
                execution_count=0,
                load_factor=0.0,
                trust_level_ord=0.0,
                availability_ord=0.0,
            )

    def test_valid_signal_roundtrip(self):
        sig = BrainAgentSignal(
            agent_id="test-agent",
            capability_match_score=0.8,
            success_rate=0.95,
            avg_latency_s=2.5,
            avg_cost_usd=0.005,
            recent_failures=1,
            execution_count=50,
            load_factor=0.3,
            trust_level_ord=2 / 3,
            availability_ord=1.0,
        )
        assert sig.agent_id == "test-agent"
        assert sig.success_rate == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# BrainState schema
# ---------------------------------------------------------------------------


class TestBrainState:
    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainState(
                task_type="t",
                domain="d",
                num_required_capabilities=0,
                num_candidates=0,
                unknown="x",  # type: ignore[call-arg]
            )

    def test_defaults_are_sensible(self):
        s = BrainState(
            task_type="analysis",
            domain="engineering",
            num_required_capabilities=0,
            num_candidates=0,
        )
        assert s.risk == CapabilityRisk.MEDIUM
        assert s.candidates == []
        assert s.routing_confidence is None

    def test_task_type_required(self):
        with pytest.raises(Exception):
            BrainState(
                task_type="",
                domain="d",
                num_required_capabilities=0,
                num_candidates=0,
            )


# ---------------------------------------------------------------------------
# BrainTarget schema
# ---------------------------------------------------------------------------


class TestBrainTarget:
    def test_defaults_all_none(self):
        t = BrainTarget()
        assert t.selected_agent_id is None
        assert t.outcome_success is None
        assert t.approval_granted is None

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainTarget(unknown="x")  # type: ignore[call-arg]

    def test_outcome_cost_non_negative(self):
        with pytest.raises(Exception):
            BrainTarget(outcome_cost_usd=-0.01)


# ---------------------------------------------------------------------------
# BrainRecord schema
# ---------------------------------------------------------------------------


class TestBrainRecord:
    def _make_minimal_state(self) -> BrainState:
        return BrainState(
            task_type="t",
            domain="d",
            num_required_capabilities=0,
            num_candidates=0,
        )

    def test_schema_version_default(self):
        r = BrainRecord(
            trace_id="trace-1",
            workflow_name="wf",
            state=self._make_minimal_state(),
            target=BrainTarget(),
        )
        assert r.schema_version == "1.0"

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            BrainRecord(
                trace_id="t",
                workflow_name="w",
                state=self._make_minimal_state(),
                target=BrainTarget(),
                unknown="x",  # type: ignore[call-arg]
            )

    def test_roundtrip_json(self):
        r = BrainRecord(
            trace_id="trace-99",
            workflow_name="test-wf",
            state=self._make_minimal_state(),
            target=BrainTarget(selected_agent_id="agent-A", outcome_success=True),
        )
        dumped = r.model_dump(mode="json")
        restored = BrainRecord.model_validate(dumped)
        assert restored.trace_id == "trace-99"
        assert restored.target.outcome_success is True


# ---------------------------------------------------------------------------
# Ordinal encoding constants
# ---------------------------------------------------------------------------


class TestOrdinalMappings:
    def test_trust_ord_privileged_is_one(self):
        assert _TRUST_ORD[AgentTrustLevel.PRIVILEGED] == pytest.approx(1.0)

    def test_trust_ord_unknown_is_zero(self):
        assert _TRUST_ORD[AgentTrustLevel.UNKNOWN] == pytest.approx(0.0)

    def test_trust_ord_trusted_gt_sandboxed(self):
        assert _TRUST_ORD[AgentTrustLevel.TRUSTED] > _TRUST_ORD[AgentTrustLevel.SANDBOXED]

    def test_availability_ord_online_is_one(self):
        assert _AVAILABILITY_ORD[AgentAvailability.ONLINE] == pytest.approx(1.0)

    def test_availability_ord_offline_is_zero(self):
        assert _AVAILABILITY_ORD[AgentAvailability.OFFLINE] == pytest.approx(0.0)

    def test_availability_ord_online_gt_degraded(self):
        assert _AVAILABILITY_ORD[AgentAvailability.ONLINE] > _AVAILABILITY_ORD[AgentAvailability.DEGRADED]


# ---------------------------------------------------------------------------
# BrainStateEncoder
# ---------------------------------------------------------------------------


class TestBrainStateEncoderBasic:
    def test_returns_brain_state(self):
        encoder = _make_encoder()
        intent = _intent()
        descriptors = [_descriptor("a1")]
        ph = PerformanceHistoryStore()
        state = encoder.encode(intent, descriptors, ph)
        assert isinstance(state, BrainState)

    def test_task_fields_copied(self):
        encoder = _make_encoder()
        intent = _intent(task_type="deploy", domain="ops", capabilities=["infra.deploy"])
        state = encoder.encode(intent, [_descriptor("a1", capabilities=["infra.deploy"])], PerformanceHistoryStore())
        assert state.task_type == "deploy"
        assert state.domain == "ops"
        assert "infra.deploy" in state.required_capabilities

    def test_num_candidates_matches_list_length(self):
        encoder = _make_encoder()
        intent = _intent()
        descriptors = [_descriptor("a1"), _descriptor("a2"), _descriptor("a3")]
        state = encoder.encode(intent, descriptors, PerformanceHistoryStore())
        assert state.num_candidates == len(state.candidates)
        assert state.num_candidates == 3

    def test_num_required_capabilities(self):
        encoder = _make_encoder()
        intent = _intent(capabilities=["cap.a", "cap.b"])
        state = encoder.encode(intent, [_descriptor("a1")], PerformanceHistoryStore())
        assert state.num_required_capabilities == 2

    def test_empty_descriptors_produces_empty_candidates(self):
        encoder = _make_encoder()
        state = encoder.encode(_intent(), [], PerformanceHistoryStore())
        assert state.candidates == []
        assert state.num_candidates == 0

    def test_budget_passed_through(self):
        encoder = _make_encoder()
        budget = BrainBudget(budget_usd=5.0, max_agents=2)
        state = encoder.encode(_intent(), [_descriptor("a1")], PerformanceHistoryStore(), budget=budget)
        assert state.budget.budget_usd == pytest.approx(5.0)
        assert state.budget.max_agents == 2

    def test_policy_passed_through(self):
        encoder = _make_encoder()
        policy = BrainPolicySignals(has_policy_effect=True, approval_required=True, matched_policy_ids=["p1"])
        state = encoder.encode(_intent(), [_descriptor("a1")], PerformanceHistoryStore(), policy=policy)
        assert state.policy.approval_required is True
        assert state.policy.matched_policy_ids == ["p1"]

    def test_routing_confidence_none_without_decision(self):
        encoder = _make_encoder()
        state = encoder.encode(_intent(), [_descriptor("a1")], PerformanceHistoryStore())
        assert state.routing_confidence is None
        assert state.score_gap is None
        assert state.confidence_band is None


class TestBrainStateEncoderWithRoutingDecision:
    def test_routing_confidence_copied_from_decision(self):
        encoder = _make_encoder()
        intent = _intent()
        descriptors = [_descriptor("a1"), _descriptor("a2")]
        ph = PerformanceHistoryStore()
        engine = RoutingEngine()
        decision = engine.route(TaskContext(task_type="code_review", description="test"), descriptors)
        state = encoder.encode(intent, descriptors, ph, routing_decision=decision)
        assert state.routing_confidence == decision.routing_confidence

    def test_candidates_follow_decision_ranking(self):
        encoder = _make_encoder()
        intent = _intent()
        descriptors = [_descriptor("a1"), _descriptor("a2")]
        ph = PerformanceHistoryStore()
        engine = RoutingEngine()
        decision = engine.route(TaskContext(task_type="code_review", description="test"), descriptors)
        state = encoder.encode(intent, descriptors, ph, routing_decision=decision)
        if len(state.candidates) >= 2 and len(decision.ranked_candidates) >= 2:
            assert state.candidates[0].agent_id == decision.ranked_candidates[0].agent_id

    def test_cap_match_from_decision(self):
        encoder = _make_encoder()
        intent = _intent()
        descriptors = [_descriptor("a1")]
        ph = PerformanceHistoryStore()
        engine = RoutingEngine()
        decision = engine.route(TaskContext(task_type="code_review", description="test"), descriptors)
        state = encoder.encode(intent, descriptors, ph, routing_decision=decision)
        if state.candidates and decision.ranked_candidates:
            expected_cap = decision.ranked_candidates[0].capability_match_score
            assert state.candidates[0].capability_match_score == pytest.approx(expected_cap)

    def test_confidence_band_copied(self):
        encoder = _make_encoder()
        intent = _intent()
        descriptors = [_descriptor("a1")]
        ph = PerformanceHistoryStore()
        decision = RoutingEngine().route(TaskContext(task_type="code_review", description="x"), descriptors)
        state = encoder.encode(intent, descriptors, ph, routing_decision=decision)
        assert state.confidence_band == decision.confidence_band


class TestBrainStateEncoderAgentSignals:
    def test_trust_level_ord_privileged(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", trust_level=AgentTrustLevel.PRIVILEGED)
        state = encoder.encode(_intent(), [desc], PerformanceHistoryStore())
        assert state.candidates[0].trust_level_ord == pytest.approx(1.0)

    def test_trust_level_ord_unknown(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", trust_level=AgentTrustLevel.UNKNOWN)
        state = encoder.encode(_intent(), [desc], PerformanceHistoryStore())
        assert state.candidates[0].trust_level_ord == pytest.approx(0.0)

    def test_availability_ord_online(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", availability=AgentAvailability.ONLINE)
        state = encoder.encode(_intent(), [desc], PerformanceHistoryStore())
        assert state.candidates[0].availability_ord == pytest.approx(1.0)

    def test_availability_ord_offline(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", availability=AgentAvailability.OFFLINE)
        state = encoder.encode(_intent(), [desc], PerformanceHistoryStore())
        assert state.candidates[0].availability_ord == pytest.approx(0.0)

    def test_performance_history_used(self):
        encoder = _make_encoder()
        desc = _descriptor("a1")
        ph = PerformanceHistoryStore()
        ph.set("a1", AgentPerformanceHistory(success_rate=0.42, avg_latency=3.5, execution_count=7))
        state = encoder.encode(_intent(), [desc], ph)
        sig = state.candidates[0]
        assert sig.success_rate == pytest.approx(0.42)
        assert sig.avg_latency_s == pytest.approx(3.5)
        assert sig.execution_count == 7

    def test_capability_match_full_overlap(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", capabilities=["analysis.code", "analysis.test"])
        intent = _intent(capabilities=["analysis.code", "analysis.test"])
        state = encoder.encode(intent, [desc], PerformanceHistoryStore())
        assert state.candidates[0].capability_match_score == pytest.approx(1.0)

    def test_capability_match_no_overlap(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", capabilities=["analysis.code"])
        intent = _intent(capabilities=["deploy.infra"])
        state = encoder.encode(intent, [desc], PerformanceHistoryStore())
        assert state.candidates[0].capability_match_score == pytest.approx(0.0)

    def test_capability_match_partial_overlap(self):
        encoder = _make_encoder()
        desc = _descriptor("a1", capabilities=["analysis.code"])
        intent = _intent(capabilities=["analysis.code", "deploy.infra"])
        state = encoder.encode(intent, [desc], PerformanceHistoryStore())
        assert state.candidates[0].capability_match_score == pytest.approx(0.5)

    def test_candidates_sorted_by_cap_match_without_decision(self):
        encoder = _make_encoder()
        intent = _intent(capabilities=["analysis.code"])
        d_full = _descriptor("full", capabilities=["analysis.code"])
        d_none = _descriptor("none", capabilities=["other.cap"])
        # Pass none first, expect full first in state (better match)
        state = encoder.encode(intent, [d_none, d_full], PerformanceHistoryStore())
        assert state.candidates[0].agent_id == "full"
        assert state.candidates[1].agent_id == "none"
