"""Unit tests for :class:`core.decision.StrategyEngine`."""

from __future__ import annotations

import pytest

from core.decision import (
    CapabilityRisk,
    PlanBuilder,
    Planner,
    StrategyChoice,
    StrategyDecision,
    StrategyEngine,
)
from core.governance import PolicyEngine, PolicyRegistry
from core.governance.policy_models import PolicyRule


pytestmark = pytest.mark.unit


def _engine_with_policies(*rules: PolicyRule) -> StrategyEngine:
    registry = PolicyRegistry(list(rules))
    return StrategyEngine(policy_engine=PolicyEngine(policy_registry=registry))


def test_policy_deny_returns_reject() -> None:
    rule = PolicyRule(
        id="deny-system-read",
        description="block read-only system scans for this test",
        capability="system.read",
        effect="deny",
        priority=100,
    )
    engine = _engine_with_policies(rule)

    decision = engine.decide({"task_type": "system_status"}, trace_id="trace-x")

    assert isinstance(decision, StrategyDecision)
    assert decision.selected_strategy is StrategyChoice.REJECT
    assert decision.allowed is False
    assert decision.requires_approval is False
    assert decision.policy_effect == "deny"
    assert "deny-system-read" in decision.matched_policy_rules
    assert decision.trace_id == "trace-x"
    assert decision.confidence == pytest.approx(1.0)


def test_policy_require_approval_returns_request_approval() -> None:
    rule = PolicyRule(
        id="approval-on-system-read",
        description="gate system reads behind human approval",
        capability="system.read",
        effect="require_approval",
        priority=50,
    )
    engine = _engine_with_policies(rule)

    decision = engine.decide({"task_type": "system_status"})

    assert decision.selected_strategy is StrategyChoice.REQUEST_APPROVAL
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.policy_effect == "require_approval"
    assert decision.confidence == pytest.approx(1.0)


def test_high_risk_intent_without_policy_requires_approval() -> None:
    engine = _engine_with_policies()  # no rules → policy effect "allow"

    decision = engine.decide(
        {
            "task_type": "workflow_automation",
            "preferences": {"risk": CapabilityRisk.HIGH},
        }
    )

    assert decision.policy_effect == "allow"
    assert decision.risk is CapabilityRisk.HIGH
    assert decision.requires_approval is True
    assert decision.allowed is True
    assert decision.selected_strategy is StrategyChoice.REQUEST_APPROVAL
    assert decision.confidence == pytest.approx(0.85)


def test_simple_task_chooses_direct_execution() -> None:
    engine = _engine_with_policies()

    decision = engine.decide({"task_type": "system_status"})

    assert decision.policy_effect == "allow"
    assert decision.requires_approval is False
    assert decision.allowed is True
    assert decision.selected_strategy is StrategyChoice.DIRECT_EXECUTION
    assert decision.risk is CapabilityRisk.LOW


def test_multi_step_code_task_chooses_plan_and_execute() -> None:
    engine = _engine_with_policies()

    decision = engine.decide(
        {
            "task_type": "code_refactor",
            "description": "Rework module X for readability",
            "preferences": {
                "risk": CapabilityRisk.MEDIUM,
                "execution_hints": {"multi_step": True, "requires_tests": True},
            },
        }
    )

    assert decision.policy_effect == "allow"
    assert decision.requires_approval is False
    assert decision.allowed is True
    assert decision.selected_strategy is StrategyChoice.PLAN_AND_EXECUTE
    assert decision.confidence == pytest.approx(0.9)


def test_decide_is_deterministic_for_stable_inputs() -> None:
    planner = Planner()
    plan_builder = PlanBuilder(planner=planner)
    policy_engine = PolicyEngine()
    engine = StrategyEngine(
        planner=planner,
        plan_builder=plan_builder,
        policy_engine=policy_engine,
    )
    task = {"task_type": "system_status", "description": "ping"}

    first = engine.decide(task)
    second = engine.decide(task)

    excluded = {"decision_id", "created_at"}
    first_fields = {k: v for k, v in first.model_dump().items() if k not in excluded}
    second_fields = {k: v for k, v in second.model_dump().items() if k not in excluded}
    assert first_fields == second_fields
    assert first.decision_id != second.decision_id
