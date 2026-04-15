"""S11 — unit tests for the evaluation harness (replay and compliance).

Covers:
- RoutingReplayVerdict classification: exact_match, acceptable_variation,
  regression, non_replayable
- PolicyReplayVerdict classification via classify_policy_delta
- TraceEvaluator.evaluate_trace() — full snapshot evaluation
- TraceEvaluator.compute_baselines() — batch metrics
- No execution during replay (dry-run only)
- No approval bypass
- Non-replayable cases: missing agent catalog, missing task_type
- Old traces without S10 fields handled gracefully
- BatchEvaluationReport rate calculations
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.audit.trace_models import ExplainabilityRecord, ReplayDescriptor, TraceSnapshot
from core.audit.trace_store import TraceStore
from core.decision.agent_descriptor import (
    AgentAvailability,
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
)
from core.decision.routing_engine import RoutingDecision, RoutingEngine
from core.evaluation.harness import (
    TraceEvaluator,
    _classify_routing_verdict,
    _build_policy_reason,
)
from core.evaluation.models import (
    BatchEvaluationReport,
    PolicyReplayResult,
    PolicyReplayVerdict,
    RoutingReplayResult,
    RoutingReplayVerdict,
    StepEvaluationResult,
    TraceEvaluationResult,
    classify_policy_delta,
)
from core.governance.policy_engine import PolicyEngine
from core.governance.policy_models import PolicyDecision

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_descriptor(
    agent_id: str = "agent-alpha",
    capabilities: list[str] | None = None,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        availability=AgentAvailability.ONLINE,
        trust_level=AgentTrustLevel.TRUSTED,
        cost_profile=AgentCostProfile.LOW,
        capabilities=capabilities or ["analysis"],
    )


def _make_trace_store(tmp_path: Path) -> TraceStore:
    return TraceStore(tmp_path / "trace.db")


def _make_routing_engine_stub(
    selected_agent_id: str | None = "agent-alpha",
    routing_confidence: float | None = 0.9,
    confidence_band: str | None = "high",
    score_gap: float | None = 0.2,
) -> RoutingEngine:
    """Build a RoutingEngine whose route_intent returns a controlled decision."""
    engine = MagicMock(spec=RoutingEngine)
    engine.route_intent.return_value = RoutingDecision(
        task_type="analysis",
        required_capabilities=[],
        ranked_candidates=[],
        selected_agent_id=selected_agent_id,
        selected_score=routing_confidence,
        routing_confidence=routing_confidence,
        score_gap=score_gap,
        confidence_band=confidence_band,
    )
    return engine


def _make_policy_engine_stub(
    effect: str = "allow",
    matched_rules: list[str] | None = None,
) -> PolicyEngine:
    engine = MagicMock(spec=PolicyEngine)
    engine.evaluate.return_value = PolicyDecision(
        effect=effect,
        matched_rules=matched_rules or [],
        winning_rule_id=None,
        winning_priority=None,
        reason="stub policy",
    )
    engine.build_execution_context.return_value = MagicMock()
    return engine


def _store_trace_with_explainability(
    store: TraceStore,
    *,
    task_type: str = "analysis",
    selected_agent_id: str = "agent-alpha",
    candidate_agent_ids: list[str] | None = None,
    routing_confidence: float | None = 0.85,
    confidence_band: str | None = "high",
    score_gap: float | None = 0.15,
    policy_effect: str | None = "allow",
    approval_required: bool = False,
    approval_id: str | None = None,
    matched_policy_ids: list[str] | None = None,
    status: str = "completed",
) -> str:
    """Store a minimal trace with one explainability record, return trace_id."""
    trace = store.create_trace("test-workflow", metadata={"task_type": task_type})
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="execute",
            selected_agent_id=selected_agent_id,
            candidate_agent_ids=candidate_agent_ids or [selected_agent_id, "agent-beta"],
            selected_score=routing_confidence,
            routing_reason_summary=f"selected {selected_agent_id}",
            matched_policy_ids=matched_policy_ids or [],
            approval_required=approval_required,
            approval_id=approval_id,
            routing_confidence=routing_confidence,
            score_gap=score_gap,
            confidence_band=confidence_band,
            policy_effect=policy_effect,
            # Use the flat metadata format that matches services/core.py production output
            metadata={
                "task_type": task_type,
                "required_capabilities": ["analysis"],
                "rejected_agents": [],
                "candidate_filter": {},
                "created_agent": None,
                "winning_policy_rule": None,
            },
        )
    )
    store.finish_trace(trace.trace_id, status=status)
    return trace.trace_id


# ---------------------------------------------------------------------------
# classify_policy_delta — pure function
# ---------------------------------------------------------------------------


def test_classify_policy_delta_compliant():
    assert classify_policy_delta("allow", "allow") is PolicyReplayVerdict.COMPLIANT
    assert classify_policy_delta("deny", "deny") is PolicyReplayVerdict.COMPLIANT
    assert classify_policy_delta("require_approval", "require_approval") is PolicyReplayVerdict.COMPLIANT


def test_classify_policy_delta_tightened():
    assert classify_policy_delta("allow", "require_approval") is PolicyReplayVerdict.TIGHTENED
    assert classify_policy_delta("allow", "deny") is PolicyReplayVerdict.TIGHTENED
    assert classify_policy_delta("require_approval", "deny") is PolicyReplayVerdict.TIGHTENED


def test_classify_policy_delta_regression():
    assert classify_policy_delta("deny", "allow") is PolicyReplayVerdict.REGRESSION
    assert classify_policy_delta("deny", "require_approval") is PolicyReplayVerdict.REGRESSION
    assert classify_policy_delta("require_approval", "allow") is PolicyReplayVerdict.REGRESSION


def test_classify_policy_delta_non_evaluable():
    assert classify_policy_delta(None, "allow") is PolicyReplayVerdict.NON_EVALUABLE
    assert classify_policy_delta("allow", None) is PolicyReplayVerdict.NON_EVALUABLE
    assert classify_policy_delta(None, None) is PolicyReplayVerdict.NON_EVALUABLE
    assert classify_policy_delta("unknown_effect", "allow") is PolicyReplayVerdict.NON_EVALUABLE


# ---------------------------------------------------------------------------
# _classify_routing_verdict — pure function
# ---------------------------------------------------------------------------


def test_classify_routing_verdict_exact_match():
    verdict, reason = _classify_routing_verdict(
        stored_agent_id="agent-a",
        current_agent_id="agent-a",
        stored_band="high",
        current_band="high",
        stored_confidence=0.9,
        current_confidence=0.9,
    )
    assert verdict is RoutingReplayVerdict.EXACT_MATCH
    assert "agent-a" in reason


def test_classify_routing_verdict_exact_match_none_agent():
    verdict, _ = _classify_routing_verdict(
        stored_agent_id=None,
        current_agent_id=None,
        stored_band=None,
        current_band=None,
        stored_confidence=None,
        current_confidence=None,
    )
    assert verdict is RoutingReplayVerdict.EXACT_MATCH


def test_classify_routing_verdict_acceptable_variation_same_band():
    verdict, reason = _classify_routing_verdict(
        stored_agent_id="agent-a",
        current_agent_id="agent-b",
        stored_band="high",
        current_band="high",
        stored_confidence=0.9,
        current_confidence=0.85,
    )
    assert verdict is RoutingReplayVerdict.ACCEPTABLE_VARIATION
    assert "high" in reason


def test_classify_routing_verdict_acceptable_variation_small_delta():
    verdict, _ = _classify_routing_verdict(
        stored_agent_id="agent-a",
        current_agent_id="agent-b",
        stored_band="high",
        current_band="medium",
        stored_confidence=0.9,
        current_confidence=0.82,  # delta=0.08 < threshold 0.15
    )
    assert verdict is RoutingReplayVerdict.ACCEPTABLE_VARIATION


def test_classify_routing_verdict_regression_band_change():
    verdict, reason = _classify_routing_verdict(
        stored_agent_id="agent-a",
        current_agent_id="agent-b",
        stored_band="high",
        current_band="low",
        stored_confidence=0.9,
        current_confidence=0.3,  # delta=0.6 > threshold
    )
    assert verdict is RoutingReplayVerdict.REGRESSION
    assert "low" in reason or "high" in reason


def test_classify_routing_verdict_regression_large_confidence_delta():
    verdict, _ = _classify_routing_verdict(
        stored_agent_id="agent-a",
        current_agent_id="agent-b",
        stored_band=None,
        current_band=None,
        stored_confidence=0.95,
        current_confidence=0.3,  # delta=0.65 > threshold
    )
    assert verdict is RoutingReplayVerdict.REGRESSION


# ---------------------------------------------------------------------------
# TraceEvaluator.evaluate_trace — core scenarios
# ---------------------------------------------------------------------------


def test_evaluate_trace_returns_none_for_unknown_id(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        _make_policy_engine_stub(),
    )
    assert evaluator.evaluate_trace("no-such-trace") is None


def test_evaluate_trace_exact_match(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(
        store,
        selected_agent_id="agent-alpha",
        routing_confidence=0.9,
        confidence_band="high",
    )
    routing_stub = _make_routing_engine_stub(
        selected_agent_id="agent-alpha",
        routing_confidence=0.88,
        confidence_band="high",
    )
    policy_stub = _make_policy_engine_stub(effect="allow")

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor("agent-alpha")],
    )
    result = evaluator.evaluate_trace(trace_id)

    assert result is not None
    assert result.trace_id == trace_id
    assert not result.has_any_regression
    assert len(result.step_results) == 1
    step = result.step_results[0]
    assert step.routing.verdict is RoutingReplayVerdict.EXACT_MATCH
    assert step.policy is not None
    assert step.policy.verdict is PolicyReplayVerdict.COMPLIANT


def test_evaluate_trace_routing_regression(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(
        store,
        selected_agent_id="agent-alpha",
        routing_confidence=0.95,
        confidence_band="high",
    )
    routing_stub = _make_routing_engine_stub(
        selected_agent_id="agent-beta",
        routing_confidence=0.25,
        confidence_band="low",
    )
    policy_stub = _make_policy_engine_stub(effect="allow")

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor("agent-beta")],
    )
    result = evaluator.evaluate_trace(trace_id)

    assert result is not None
    assert result.has_routing_regression
    assert result.has_any_regression
    assert result.step_results[0].routing.verdict is RoutingReplayVerdict.REGRESSION


def test_evaluate_trace_policy_regression(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(
        store,
        policy_effect="deny",
        routing_confidence=0.8,
        confidence_band="high",
    )
    routing_stub = _make_routing_engine_stub()
    policy_stub = _make_policy_engine_stub(effect="allow")  # loosened!

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor()],
    )
    result = evaluator.evaluate_trace(trace_id)

    assert result is not None
    assert result.has_policy_regression
    assert result.step_results[0].policy is not None
    assert result.step_results[0].policy.verdict is PolicyReplayVerdict.REGRESSION


def test_evaluate_trace_policy_tightened(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(
        store,
        policy_effect="allow",
        routing_confidence=0.8,
        confidence_band="high",
    )
    routing_stub = _make_routing_engine_stub()
    policy_stub = _make_policy_engine_stub(effect="require_approval")

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor()],
    )
    result = evaluator.evaluate_trace(trace_id)

    assert result is not None
    assert not result.has_policy_regression  # tightened is not a regression
    assert result.step_results[0].policy is not None
    assert result.step_results[0].policy.verdict is PolicyReplayVerdict.TIGHTENED


def test_evaluate_trace_non_replayable_no_agents(tmp_path: Path):
    """With no agent descriptors, routing dry-run is non-replayable."""
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(store)

    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        _make_policy_engine_stub(),
        agent_descriptors=[],  # empty catalog
    )
    result = evaluator.evaluate_trace(trace_id)

    assert result is not None
    assert result.non_replayable_count == 1
    assert result.step_results[0].routing.verdict is RoutingReplayVerdict.NON_REPLAYABLE
    assert "no agent descriptors" in (result.step_results[0].routing.non_replayable_reason or "")


def test_evaluate_trace_no_execution_called(tmp_path: Path):
    """Verify that evaluate_trace never calls execution-path methods."""
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(store)

    routing_stub = _make_routing_engine_stub()
    policy_stub = _make_policy_engine_stub()

    # Track what methods were called — we should see route_intent but nothing that
    # triggers execution (e.g. no .execute(), no .dispatch(), no .run())
    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor()],
    )
    evaluator.evaluate_trace(trace_id)

    # route_intent was called (dry-run routing) but NOT anything execution-related
    routing_stub.route_intent.assert_called_once()
    assert not hasattr(routing_stub, "execute") or not getattr(routing_stub, "execute", MagicMock()).called


def test_evaluate_trace_old_record_without_s10_fields(tmp_path: Path):
    """Old traces without S10 fields (routing_confidence=None) are handled gracefully."""
    store = _make_trace_store(tmp_path)
    trace = store.create_trace("test-workflow", metadata={"task_type": "analysis"})
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="execute",
            selected_agent_id="agent-alpha",
            candidate_agent_ids=["agent-alpha"],
            selected_score=None,
            routing_reason_summary="legacy record",
            # no S10 fields: routing_confidence=None, confidence_band=None, policy_effect=None
            metadata={
                "task_type": "analysis",
                "required_capabilities": [],
            },
        )
    )
    store.finish_trace(trace.trace_id, status="completed")

    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(selected_agent_id="agent-alpha"),
        _make_policy_engine_stub(),
        agent_descriptors=[_make_descriptor()],
    )
    result = evaluator.evaluate_trace(trace.trace_id)

    # Should complete without errors; routing should produce EXACT_MATCH
    assert result is not None
    assert len(result.step_results) == 1
    step = result.step_results[0]
    assert step.routing.verdict in {
        RoutingReplayVerdict.EXACT_MATCH,
        RoutingReplayVerdict.ACCEPTABLE_VARIATION,
        RoutingReplayVerdict.NON_REPLAYABLE,
    }


def test_evaluate_trace_no_policy_signal_skips_policy(tmp_path: Path):
    """Steps without policy_effect and no matched_policy_ids skip policy evaluation."""
    store = _make_trace_store(tmp_path)
    trace = store.create_trace("test-workflow", metadata={"task_type": "analysis"})
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="execute",
            selected_agent_id="agent-alpha",
            candidate_agent_ids=["agent-alpha"],
            selected_score=0.8,
            routing_reason_summary="selected agent-alpha",
            # No policy_effect, no matched_policy_ids
            policy_effect=None,
            matched_policy_ids=[],
            metadata={
                "task_type": "analysis",
                "required_capabilities": [],
            },
        )
    )
    store.finish_trace(trace.trace_id, status="completed")

    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        _make_policy_engine_stub(),
        agent_descriptors=[_make_descriptor()],
    )
    result = evaluator.evaluate_trace(trace.trace_id)

    assert result is not None
    step = result.step_results[0]
    assert step.policy is None  # skipped — no stored policy signal


def test_evaluate_trace_approval_consistency(tmp_path: Path):
    """Approval consistency is detected when approval_required changes."""
    store = _make_trace_store(tmp_path)
    trace_id = _store_trace_with_explainability(
        store,
        approval_required=True,
        policy_effect="require_approval",
    )
    # Current policy engine returns "allow" — approval no longer required
    policy_stub = _make_policy_engine_stub(effect="allow")

    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        policy_stub,
        agent_descriptors=[_make_descriptor()],
    )
    result = evaluator.evaluate_trace(trace_id)

    assert result is not None
    step = result.step_results[0]
    assert step.policy is not None
    assert step.policy.verdict is PolicyReplayVerdict.REGRESSION  # require_approval → allow
    assert not step.policy.approval_consistency  # stored=True, current=False


# ---------------------------------------------------------------------------
# TraceEvaluator.compute_baselines
# ---------------------------------------------------------------------------


def test_compute_baselines_empty_store(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        _make_policy_engine_stub(),
    )
    report = evaluator.compute_baselines(limit=10)
    assert isinstance(report, BatchEvaluationReport)
    assert report.trace_count == 0
    assert report.routing_match_rate is None
    assert report.policy_compliance_rate is None


def test_compute_baselines_single_trace_exact_match(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    _store_trace_with_explainability(
        store,
        selected_agent_id="agent-alpha",
        routing_confidence=0.9,
        confidence_band="high",
        policy_effect="allow",
    )
    routing_stub = _make_routing_engine_stub(
        selected_agent_id="agent-alpha",
        routing_confidence=0.88,
        confidence_band="high",
    )
    policy_stub = _make_policy_engine_stub(effect="allow")

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor("agent-alpha")],
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_count == 1
    assert report.routing_exact_match_count == 1
    assert report.routing_regression_count == 0
    assert report.routing_match_rate == 1.0
    assert report.policy_compliant_count == 1
    assert report.policy_compliance_rate == 1.0
    assert report.traces_with_regression == 0


def test_compute_baselines_mixed_results(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    # Trace 1: will be an exact match
    _store_trace_with_explainability(
        store,
        selected_agent_id="agent-alpha",
        routing_confidence=0.9,
        confidence_band="high",
        policy_effect="allow",
    )
    # Trace 2: will produce a regression (different agent, low confidence, policy denial loosened)
    _store_trace_with_explainability(
        store,
        selected_agent_id="agent-beta",
        routing_confidence=0.8,
        confidence_band="high",
        policy_effect="deny",
    )

    routing_stub = _make_routing_engine_stub(
        selected_agent_id="agent-alpha",
        routing_confidence=0.88,
        confidence_band="high",
    )
    policy_stub = _make_policy_engine_stub(effect="allow")  # loosened for trace 2

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor("agent-alpha")],
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_count == 2
    assert report.evaluated_step_count == 2
    # Trace 1: exact match, trace 2: acceptable (same band high→high)
    assert report.routing_exact_match_count + report.routing_acceptable_variation_count == 2
    # Policy: trace 1 compliant, trace 2 regression (deny → allow)
    assert report.policy_regression_count == 1
    assert report.traces_with_regression >= 1


def test_compute_baselines_rates_calculation(tmp_path: Path):
    """Rates are correctly derived from raw counts."""
    store = _make_trace_store(tmp_path)
    # 2 exact matches + 1 regression
    for _ in range(2):
        _store_trace_with_explainability(
            store,
            selected_agent_id="agent-alpha",
            confidence_band="high",
            routing_confidence=0.9,
            policy_effect="allow",
        )
    _store_trace_with_explainability(
        store,
        selected_agent_id="agent-beta",
        confidence_band="low",
        routing_confidence=0.3,
        policy_effect="allow",
    )

    routing_stub = _make_routing_engine_stub(
        selected_agent_id="agent-alpha",
        routing_confidence=0.85,
        confidence_band="high",
    )
    policy_stub = _make_policy_engine_stub(effect="allow")

    evaluator = TraceEvaluator(
        store,
        routing_stub,
        policy_stub,
        agent_descriptors=[_make_descriptor("agent-alpha")],
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_count == 3
    assert report.routing_match_rate is not None
    assert 0.0 <= report.routing_match_rate <= 1.0
    assert report.policy_compliance_rate == 1.0  # all allow → allow


def test_compute_baselines_avg_confidence(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    _store_trace_with_explainability(store, routing_confidence=0.8)
    _store_trace_with_explainability(store, routing_confidence=0.6)

    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        _make_policy_engine_stub(),
        agent_descriptors=[_make_descriptor()],
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.avg_routing_confidence is not None
    assert abs(report.avg_routing_confidence - 0.7) < 0.01


def test_compute_baselines_no_side_effects(tmp_path: Path):
    """compute_baselines does not write any new records."""
    store = _make_trace_store(tmp_path)
    _store_trace_with_explainability(store)

    traces_before = store.list_recent_traces(limit=100)

    evaluator = TraceEvaluator(
        store,
        _make_routing_engine_stub(),
        _make_policy_engine_stub(),
        agent_descriptors=[_make_descriptor()],
    )
    evaluator.compute_baselines(limit=10)

    traces_after = store.list_recent_traces(limit=100)
    # No new traces written
    assert len(traces_after) == len(traces_before)


# ---------------------------------------------------------------------------
# model / __init__ exports
# ---------------------------------------------------------------------------


def test_evaluation_module_exports():
    from core.evaluation import (
        BatchEvaluationReport,
        PolicyReplayResult,
        PolicyReplayVerdict,
        RoutingReplayResult,
        RoutingReplayVerdict,
        StepEvaluationResult,
        TraceEvaluationResult,
        TraceEvaluator,
    )
    assert BatchEvaluationReport is not None
    assert TraceEvaluator is not None


def test_trace_evaluation_result_model():
    result = TraceEvaluationResult(
        trace_id="t1",
        workflow_name="wf",
        can_replay=True,
    )
    assert result.has_any_regression is False
    assert result.step_results == []


def test_batch_evaluation_report_model():
    report = BatchEvaluationReport()
    assert report.trace_count == 0
    assert report.routing_match_rate is None
    assert report.confidence_band_distribution == {}


# ---------------------------------------------------------------------------
# S14 — Safety Metrics + Routing KPIs
# ---------------------------------------------------------------------------


def test_batch_report_new_safety_and_kpi_fields_default():
    """New S14 fields have correct zero/None defaults."""
    report = BatchEvaluationReport()
    assert report.trace_success_count == 0
    assert report.trace_failed_count == 0
    assert report.trace_success_rate is None
    assert report.avg_duration_ms is None
    assert report.p95_duration_ms is None
    assert report.approval_bypass_count == 0


def test_compute_baselines_trace_success_rate_all_completed(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    for _ in range(3):
        _store_trace_with_explainability(store, status="completed")

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_success_count == 3
    assert report.trace_failed_count == 0
    assert report.trace_success_rate == pytest.approx(1.0)


def test_compute_baselines_trace_success_rate_all_failed(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    for _ in range(2):
        _store_trace_with_explainability(store, status="failed")

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_success_count == 0
    assert report.trace_failed_count == 2
    assert report.trace_success_rate == pytest.approx(0.0)


def test_compute_baselines_trace_success_rate_mixed(tmp_path: Path):
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    _store_trace_with_explainability(store, status="completed")
    _store_trace_with_explainability(store, status="completed")
    _store_trace_with_explainability(store, status="failed")

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_success_count == 2
    assert report.trace_failed_count == 1
    assert report.trace_success_rate == pytest.approx(2 / 3)


def test_compute_baselines_running_traces_excluded_from_success_rate(tmp_path: Path):
    """Traces still in 'running' state are not terminal — not counted in success_rate."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    # Create a completed trace
    _store_trace_with_explainability(store, status="completed")
    # Create a trace that never gets finished (status stays "running")
    trace = store.create_trace("test-workflow", metadata={"task_type": "analysis"})
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="execute",
            selected_agent_id="agent-alpha",
            candidate_agent_ids=["agent-alpha"],
            selected_score=0.9,
            routing_reason_summary="still running",
            metadata={"task_type": "analysis", "required_capabilities": []},
        )
    )
    # NOTE: trace is NOT finished — status remains "running"

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_count == 2
    assert report.trace_success_count == 1
    assert report.trace_failed_count == 0
    # success_rate = 1 / (1+0) = 1.0 (only terminal traces counted)
    assert report.trace_success_rate == pytest.approx(1.0)


def test_compute_baselines_duration_computed_for_completed_traces(tmp_path: Path):
    """avg_duration_ms and p95_duration_ms are computed for completed traces."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    for _ in range(3):
        _store_trace_with_explainability(store, status="completed")

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.avg_duration_ms is not None
    assert report.p95_duration_ms is not None
    assert report.avg_duration_ms >= 0.0
    assert report.p95_duration_ms >= 0.0


def test_compute_baselines_duration_none_when_no_completed_traces(tmp_path: Path):
    """Duration metrics are None when there are no completed traces."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    # Only failed traces — finish_trace with "failed" still sets ended_at but
    # we skip non-completed traces in duration tracking
    _store_trace_with_explainability(store, status="failed")

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.avg_duration_ms is None
    assert report.p95_duration_ms is None


def test_compute_baselines_empty_store_duration_none(tmp_path: Path):
    """Empty store produces None for all optional metrics."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub()
    policy_stub = _make_policy_engine_stub()

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.trace_success_rate is None
    assert report.avg_duration_ms is None
    assert report.p95_duration_ms is None
    assert report.approval_bypass_count == 0


def test_compute_baselines_approval_bypass_counted(tmp_path: Path):
    """Steps with approval_required=True and no approval_id are counted as bypasses."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="require_approval")

    # This step required approval but has no approval_id → bypass
    _store_trace_with_explainability(
        store,
        approval_required=True,
        approval_id=None,
        policy_effect="require_approval",
    )

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.approval_bypass_count == 1


def test_compute_baselines_approval_no_bypass_when_id_present(tmp_path: Path):
    """Steps with approval_required=True AND an approval_id are NOT bypasses."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="require_approval")

    _store_trace_with_explainability(
        store,
        approval_required=True,
        approval_id="approval-abc123",
        policy_effect="require_approval",
    )

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.approval_bypass_count == 0


def test_compute_baselines_approval_no_bypass_when_not_required(tmp_path: Path):
    """Steps that don't require approval are never bypass candidates."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="allow")

    _store_trace_with_explainability(
        store,
        approval_required=False,
        approval_id=None,
    )

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.approval_bypass_count == 0


def test_compute_baselines_approval_bypass_count_accumulates(tmp_path: Path):
    """Bypass count accumulates across multiple steps across multiple traces."""
    store = _make_trace_store(tmp_path)
    routing_stub = _make_routing_engine_stub(selected_agent_id="agent-alpha")
    policy_stub = _make_policy_engine_stub(effect="require_approval")

    # 2 traces with bypass, 1 without
    _store_trace_with_explainability(
        store, approval_required=True, approval_id=None, policy_effect="require_approval"
    )
    _store_trace_with_explainability(
        store, approval_required=True, approval_id=None, policy_effect="require_approval"
    )
    _store_trace_with_explainability(
        store, approval_required=True, approval_id="approval-xyz", policy_effect="require_approval"
    )

    evaluator = TraceEvaluator(
        store, routing_stub, policy_stub, agent_descriptors=[_make_descriptor()]
    )
    report = evaluator.compute_baselines(limit=10)

    assert report.approval_bypass_count == 2
