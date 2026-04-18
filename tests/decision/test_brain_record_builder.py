"""Phase 6 – Brain v1 B6-S2: BrainRecordBuilder tests."""

from __future__ import annotations

import pytest

from core.decision.brain.record_builder import (
    BrainRecordBuilder,
    _AVAILABILITY_ORD_UNKNOWN,
    _TRUST_ORD_UNKNOWN,
)
from core.decision.brain.state import BrainRecord, BrainState, BrainTarget
from core.decision.learning.record import LearningRecord
from core.decision.performance_history import AgentPerformanceHistory, PerformanceHistoryStore

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rec(**kw) -> LearningRecord:
    defaults = dict(
        trace_id="trace-1",
        workflow_name="test-workflow",
        task_type="code_review",
        selected_agent_id="agent-A",
        selected_score=0.82,
        routing_confidence=0.82,
        score_gap=0.15,
        confidence_band="high",
        candidate_agent_ids=["agent-A", "agent-B"],
        success=True,
        cost_usd=0.003,
        latency_ms=450.0,
        has_routing_decision=True,
        has_outcome=True,
        has_approval_outcome=False,
    )
    defaults.update(kw)
    return LearningRecord(**defaults)


def _builder(**kw) -> BrainRecordBuilder:
    return BrainRecordBuilder(**kw)


# ---------------------------------------------------------------------------
# BrainRecordBuilder.build — basic contract
# ---------------------------------------------------------------------------


class TestBrainRecordBuilderBuild:
    def test_returns_brain_record(self):
        result = _builder().build(_rec())
        assert isinstance(result, BrainRecord)

    def test_trace_id_copied(self):
        result = _builder().build(_rec(trace_id="trace-99"))
        assert result.trace_id == "trace-99"

    def test_workflow_name_copied(self):
        result = _builder().build(_rec(workflow_name="wf-prod"))
        assert result.workflow_name == "wf-prod"

    def test_schema_version_default(self):
        result = _builder().build(_rec())
        assert result.schema_version == "1.0"

    def test_state_is_brain_state(self):
        result = _builder().build(_rec())
        assert isinstance(result.state, BrainState)

    def test_target_is_brain_target(self):
        result = _builder().build(_rec())
        assert isinstance(result.target, BrainTarget)

    def test_requires_routing_decision_by_default(self):
        record = _rec(has_routing_decision=False)
        with pytest.raises(ValueError, match="has no routing decision"):
            _builder().build(record)

    def test_allow_no_routing_decision_when_disabled(self):
        record = _rec(has_routing_decision=False)
        result = _builder(require_routing_decision=False).build(record)
        assert isinstance(result, BrainRecord)


# ---------------------------------------------------------------------------
# BrainState population
# ---------------------------------------------------------------------------


class TestBrainStatePopulation:
    def test_task_type_from_record(self):
        result = _builder().build(_rec(task_type="deploy"))
        assert result.state.task_type == "deploy"

    def test_task_type_defaults_to_unknown_when_none(self):
        result = _builder().build(_rec(task_type=None))
        assert result.state.task_type == "unknown"

    def test_domain_defaults_to_unknown(self):
        result = _builder().build(_rec())
        assert result.state.domain == "unknown"

    def test_required_capabilities_empty(self):
        result = _builder().build(_rec())
        assert result.state.required_capabilities == []
        assert result.state.num_required_capabilities == 0

    def test_routing_confidence_copied(self):
        result = _builder().build(_rec(routing_confidence=0.77))
        assert result.state.routing_confidence == pytest.approx(0.77)

    def test_score_gap_copied(self):
        result = _builder().build(_rec(score_gap=0.12))
        assert result.state.score_gap == pytest.approx(0.12)

    def test_confidence_band_copied(self):
        result = _builder().build(_rec(confidence_band="medium"))
        assert result.state.confidence_band == "medium"

    def test_routing_confidence_none_when_absent(self):
        result = _builder().build(_rec(routing_confidence=None))
        assert result.state.routing_confidence is None

    def test_num_candidates_equals_candidate_list(self):
        result = _builder().build(_rec(candidate_agent_ids=["a1", "a2", "a3"]))
        assert result.state.num_candidates == len(result.state.candidates)

    def test_budget_is_default(self):
        result = _builder().build(_rec())
        assert result.state.budget.budget_usd is None
        assert result.state.budget.max_agents == 1


# ---------------------------------------------------------------------------
# Policy signals
# ---------------------------------------------------------------------------


class TestPolicySignals:
    def test_no_policy_effect_when_policy_effect_none(self):
        result = _builder().build(_rec(policy_effect=None))
        assert result.state.policy.has_policy_effect is False

    def test_policy_effect_when_allow(self):
        result = _builder().build(_rec(policy_effect="allow"))
        assert result.state.policy.has_policy_effect is True

    def test_policy_effect_when_approval_required(self):
        result = _builder().build(_rec(policy_effect="approval_required"))
        assert result.state.policy.has_policy_effect is True

    def test_approval_required_copied(self):
        result = _builder().build(_rec(approval_required=True))
        assert result.state.policy.approval_required is True

    def test_matched_policy_ids_copied(self):
        result = _builder().build(_rec(matched_policy_ids=["p1", "p2"]))
        assert result.state.policy.matched_policy_ids == ["p1", "p2"]

    def test_matched_policy_ids_empty_by_default(self):
        result = _builder().build(_rec(matched_policy_ids=[]))
        assert result.state.policy.matched_policy_ids == []


# ---------------------------------------------------------------------------
# Agent signals
# ---------------------------------------------------------------------------


class TestAgentSignals:
    def test_selected_agent_is_first_candidate(self):
        result = _builder().build(_rec(
            selected_agent_id="agent-A",
            candidate_agent_ids=["agent-B", "agent-A"],
        ))
        assert result.state.candidates[0].agent_id == "agent-A"

    def test_selected_agent_prepended_when_missing_from_candidates(self):
        result = _builder().build(_rec(
            selected_agent_id="agent-X",
            candidate_agent_ids=["agent-A", "agent-B"],
        ))
        assert result.state.candidates[0].agent_id == "agent-X"
        assert result.state.num_candidates == 3

    def test_selected_agent_stays_first_when_already_first(self):
        result = _builder().build(_rec(
            selected_agent_id="agent-A",
            candidate_agent_ids=["agent-A", "agent-B"],
        ))
        assert result.state.candidates[0].agent_id == "agent-A"
        assert result.state.num_candidates == 2

    def test_capability_match_score_is_zero(self):
        result = _builder().build(_rec())
        for sig in result.state.candidates:
            assert sig.capability_match_score == pytest.approx(0.0)

    def test_trust_level_ord_is_unknown_sentinel(self):
        result = _builder().build(_rec())
        for sig in result.state.candidates:
            assert sig.trust_level_ord == pytest.approx(_TRUST_ORD_UNKNOWN)

    def test_availability_ord_is_unknown_sentinel(self):
        result = _builder().build(_rec())
        for sig in result.state.candidates:
            assert sig.availability_ord == pytest.approx(_AVAILABILITY_ORD_UNKNOWN)

    def test_no_candidates_when_list_empty_and_no_selected(self):
        result = _builder().build(_rec(
            selected_agent_id=None,
            candidate_agent_ids=[],
        ))
        assert result.state.candidates == []
        assert result.state.num_candidates == 0

    def test_only_selected_when_candidate_list_empty(self):
        result = _builder().build(_rec(
            selected_agent_id="agent-A",
            candidate_agent_ids=[],
        ))
        assert result.state.num_candidates == 1
        assert result.state.candidates[0].agent_id == "agent-A"

    def test_performance_history_used(self):
        ph = PerformanceHistoryStore()
        ph.set("agent-A", AgentPerformanceHistory(
            success_rate=0.95,
            avg_latency=2.1,
            avg_cost=0.007,
            recent_failures=2,
            execution_count=30,
        ))
        result = _builder(performance_history=ph).build(_rec(
            selected_agent_id="agent-A",
            candidate_agent_ids=["agent-A"],
        ))
        sig = result.state.candidates[0]
        assert sig.success_rate == pytest.approx(0.95)
        assert sig.avg_latency_s == pytest.approx(2.1)
        assert sig.avg_cost_usd == pytest.approx(0.007)
        assert sig.recent_failures == 2
        assert sig.execution_count == 30

    def test_default_history_when_agent_unknown(self):
        result = _builder().build(_rec(
            selected_agent_id="unknown-agent",
            candidate_agent_ids=["unknown-agent"],
        ))
        sig = result.state.candidates[0]
        assert 0.0 <= sig.success_rate <= 1.0
        assert sig.avg_latency_s >= 0.0


# ---------------------------------------------------------------------------
# BrainTarget population
# ---------------------------------------------------------------------------


class TestBrainTargetPopulation:
    def test_selected_agent_id_copied(self):
        result = _builder().build(_rec(selected_agent_id="agent-B"))
        assert result.target.selected_agent_id == "agent-B"

    def test_outcome_success_true(self):
        result = _builder().build(_rec(success=True))
        assert result.target.outcome_success is True

    def test_outcome_success_false(self):
        result = _builder().build(_rec(success=False))
        assert result.target.outcome_success is False

    def test_outcome_success_none_when_absent(self):
        result = _builder().build(_rec(success=None, has_outcome=False))
        assert result.target.outcome_success is None

    def test_outcome_cost_copied(self):
        result = _builder().build(_rec(cost_usd=0.012))
        assert result.target.outcome_cost_usd == pytest.approx(0.012)

    def test_outcome_latency_copied(self):
        result = _builder().build(_rec(latency_ms=800.0))
        assert result.target.outcome_latency_ms == pytest.approx(800.0)

    def test_approval_required_copied(self):
        result = _builder().build(_rec(approval_required=True))
        assert result.target.approval_required is True

    def test_approval_granted_true_when_approved(self):
        result = _builder().build(_rec(
            approval_required=True,
            approval_id="ap-1",
            approval_decision="approved",
            has_approval_outcome=True,
        ))
        assert result.target.approval_granted is True

    def test_approval_granted_false_when_rejected(self):
        result = _builder().build(_rec(
            approval_required=True,
            approval_id="ap-2",
            approval_decision="rejected",
            has_approval_outcome=True,
        ))
        assert result.target.approval_granted is False

    def test_approval_granted_none_when_no_outcome(self):
        result = _builder().build(_rec(
            approval_required=True,
            has_approval_outcome=False,
        ))
        assert result.target.approval_granted is None

    def test_approval_granted_none_when_pending(self):
        # pending is not a resolved outcome
        result = _builder().build(_rec(
            approval_required=True,
            approval_decision="pending",
            has_approval_outcome=False,
        ))
        assert result.target.approval_granted is None


# ---------------------------------------------------------------------------
# build_batch
# ---------------------------------------------------------------------------


class TestBrainRecordBuilderBatch:
    def test_empty_input_returns_empty(self):
        assert _builder().build_batch([]) == []

    def test_valid_batch_converted(self):
        records = [_rec(trace_id=f"t{i}") for i in range(5)]
        result = _builder().build_batch(records)
        assert len(result) == 5

    def test_invalid_skipped_when_skip_invalid_true(self):
        valid = _rec(trace_id="good")
        invalid = _rec(trace_id="bad", has_routing_decision=False)
        result = _builder().build_batch([valid, invalid], skip_invalid=True)
        assert len(result) == 1
        assert result[0].trace_id == "good"

    def test_invalid_raises_when_skip_invalid_false(self):
        records = [_rec(has_routing_decision=False)]
        with pytest.raises(ValueError):
            _builder().build_batch(records, skip_invalid=False)

    def test_trace_ids_preserved_in_order(self):
        records = [_rec(trace_id=f"t{i}") for i in range(3)]
        result = _builder().build_batch(records)
        assert [r.trace_id for r in result] == ["t0", "t1", "t2"]

    def test_batch_with_require_off_converts_all(self):
        records = [_rec(has_routing_decision=False) for _ in range(3)]
        result = _builder(require_routing_decision=False).build_batch(records)
        assert len(result) == 3

    def test_json_roundtrip_for_batch(self):
        records = [_rec(trace_id=f"t{i}") for i in range(2)]
        brain_records = _builder().build_batch(records)
        for br in brain_records:
            dumped = br.model_dump(mode="json")
            restored = BrainRecord.model_validate(dumped)
            assert restored.trace_id == br.trace_id
