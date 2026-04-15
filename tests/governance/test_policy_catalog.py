"""Parametrized policy catalog tests covering all 9 PolicyRule matching conditions,
all 3 effects, priority ordering, multi-rule resolution, and PolicyEngine integration.

These tests verify the deterministic governance layer without touching execution,
approvals, or trace storage.
"""

from __future__ import annotations

import json

import pytest

from core.decision.agent_descriptor import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)
from core.decision.task_intent import TaskIntent
from core.governance.policy_engine import PolicyEngine
from core.governance.policy_models import PolicyEvaluationContext, PolicyRule
from core.governance.policy_registry import PolicyRegistry

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(**kwargs) -> PolicyRule:
    """Build a PolicyRule with required fields and arbitrary overrides."""
    defaults = {
        "id": "test-rule",
        "description": "Test rule",
        "effect": "allow",
        "priority": 0,
    }
    defaults.update(kwargs)
    return PolicyRule.model_validate(defaults)


def _make_context(**kwargs) -> PolicyEvaluationContext:
    """Build a PolicyEvaluationContext with required fields and arbitrary overrides."""
    defaults = {
        "task_type": "analysis",
        "required_capabilities": [],
    }
    defaults.update(kwargs)
    return PolicyEvaluationContext.model_validate(defaults)


def _make_registry(*rules: PolicyRule) -> PolicyRegistry:
    return PolicyRegistry(rules=list(rules))


# ---------------------------------------------------------------------------
# 1. All 9 matching conditions — parametrized positive and negative cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rule_extra,context_extra,expected_match",
    [
        # ── condition 1: capability ──
        # rule fires when required capability IS in context
        pytest.param(
            {"capability": "deploy"},
            {"required_capabilities": ["deploy"]},
            True,
            id="capability_present",
        ),
        pytest.param(
            {"capability": "deploy"},
            {"required_capabilities": ["analysis"]},
            False,
            id="capability_absent",
        ),
        pytest.param(
            {"capability": "deploy"},
            {"required_capabilities": []},
            False,
            id="capability_empty_list",
        ),
        # capability=None → condition is skipped (matches anything)
        pytest.param(
            {"capability": None},
            {"required_capabilities": []},
            True,
            id="capability_none_skipped",
        ),
        # ── condition 2: agent_id ──
        pytest.param(
            {"agent_id": "agent-a"},
            {"agent_id": "agent-a"},
            True,
            id="agent_id_exact_match",
        ),
        pytest.param(
            {"agent_id": "agent-a"},
            {"agent_id": "agent-b"},
            False,
            id="agent_id_mismatch",
        ),
        pytest.param(
            {"agent_id": "agent-a"},
            {"agent_id": None},
            False,
            id="agent_id_none_context",
        ),
        # ── condition 3: source_type ──
        pytest.param(
            {"source_type": "n8n"},
            {"source_type": "n8n"},
            True,
            id="source_type_match",
        ),
        pytest.param(
            {"source_type": "n8n"},
            {"source_type": "native"},
            False,
            id="source_type_mismatch",
        ),
        pytest.param(
            {"source_type": "n8n"},
            {"source_type": None},
            False,
            id="source_type_none_context",
        ),
        # ── condition 4: execution_kind ──
        pytest.param(
            {"execution_kind": "cloud_agent"},
            {"execution_kind": "cloud_agent"},
            True,
            id="execution_kind_match",
        ),
        pytest.param(
            {"execution_kind": "cloud_agent"},
            {"execution_kind": "local_process"},
            False,
            id="execution_kind_mismatch",
        ),
        # ── condition 5: risk_level ──
        pytest.param(
            {"risk_level": "high"},
            {"risk_level": "high"},
            True,
            id="risk_level_match",
        ),
        pytest.param(
            {"risk_level": "high"},
            {"risk_level": "medium"},
            False,
            id="risk_level_mismatch",
        ),
        pytest.param(
            {"risk_level": "high"},
            {"risk_level": None},
            False,
            id="risk_level_none_context",
        ),
        # ── condition 6: external_side_effect ──
        pytest.param(
            {"external_side_effect": True},
            {"external_side_effect": True},
            True,
            id="external_side_effect_true_match",
        ),
        pytest.param(
            {"external_side_effect": True},
            {"external_side_effect": False},
            False,
            id="external_side_effect_false_no_match",
        ),
        pytest.param(
            {"external_side_effect": True},
            {"external_side_effect": None},
            False,
            id="external_side_effect_none_no_match",
        ),
        pytest.param(
            {"external_side_effect": False},
            {"external_side_effect": False},
            True,
            id="external_side_effect_false_match",
        ),
        # ── condition 7: max_cost (rule fires when cost EXCEEDS limit) ──
        pytest.param(
            {"max_cost": 1.0},
            {"estimated_cost": 2.0},
            True,
            id="max_cost_exceeded",
        ),
        pytest.param(
            {"max_cost": 1.0},
            {"estimated_cost": 1.0},
            False,
            id="max_cost_at_limit_not_exceeded",
        ),
        pytest.param(
            {"max_cost": 1.0},
            {"estimated_cost": 0.5},
            False,
            id="max_cost_under_limit",
        ),
        pytest.param(
            {"max_cost": 1.0},
            {"estimated_cost": None},
            False,
            id="max_cost_unknown_cost",
        ),
        # ── condition 8: max_latency (rule fires when latency EXCEEDS limit) ──
        pytest.param(
            {"max_latency": 500},
            {"estimated_latency": 1000},
            True,
            id="max_latency_exceeded",
        ),
        pytest.param(
            {"max_latency": 500},
            {"estimated_latency": 500},
            False,
            id="max_latency_at_limit_not_exceeded",
        ),
        pytest.param(
            {"max_latency": 500},
            {"estimated_latency": 200},
            False,
            id="max_latency_under_limit",
        ),
        pytest.param(
            {"max_latency": 500},
            {"estimated_latency": None},
            False,
            id="max_latency_unknown_latency",
        ),
        # ── condition 9: requires_local (rule fires when locality DIFFERS) ──
        # requires_local=True fires when agent is NOT local (is_local=False)
        pytest.param(
            {"requires_local": True},
            {"is_local": False},
            True,
            id="requires_local_true_non_local_agent_fires",
        ),
        pytest.param(
            {"requires_local": True},
            {"is_local": True},
            False,
            id="requires_local_true_local_agent_no_fire",
        ),
        pytest.param(
            {"requires_local": True},
            {"is_local": None},
            False,
            id="requires_local_true_unknown_locality_no_fire",
        ),
        # requires_local=False fires when agent IS local (is_local=True)
        pytest.param(
            {"requires_local": False},
            {"is_local": True},
            True,
            id="requires_local_false_local_agent_fires",
        ),
        pytest.param(
            {"requires_local": False},
            {"is_local": False},
            False,
            id="requires_local_false_non_local_no_fire",
        ),
    ],
)
def test_policy_rule_matching_conditions(rule_extra, context_extra, expected_match):
    """Each of the 9 PolicyRule matching conditions fires or stays silent correctly."""
    rule = _make_rule(id="test-rule", description="Test", effect="deny", **rule_extra)
    context = _make_context(**context_extra)
    registry = _make_registry(rule)

    matched = registry.get_applicable_policies(context)

    if expected_match:
        assert len(matched) == 1
        assert matched[0].id == "test-rule"
    else:
        assert matched == []


# ---------------------------------------------------------------------------
# 2. All 3 effects
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("effect", ["allow", "require_approval", "deny"])
def test_all_three_effects_returned_by_engine(effect):
    rule = _make_rule(
        id=f"rule-{effect}",
        description=f"Effect {effect}",
        effect=effect,
        capability="x",
    )
    registry = _make_registry(rule)
    engine = PolicyEngine(policy_registry=registry)
    intent = TaskIntent(
        task_type="test",
        domain="analysis",
        required_capabilities=["x"],
    )
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert decision.effect == effect
    assert f"rule-{effect}" in decision.matched_rules


# ---------------------------------------------------------------------------
# 3. Default allow when no rules match
# ---------------------------------------------------------------------------


def test_default_allow_when_no_rules_match():
    registry = _make_registry()  # empty
    engine = PolicyEngine(policy_registry=registry)
    intent = TaskIntent(task_type="analysis", domain="analysis")
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert decision.effect == "allow"
    assert decision.matched_rules == []
    assert decision.reason == "no_policy_matched"


def test_default_allow_when_rule_conditions_not_met():
    rule = _make_rule(
        id="deny-cloud",
        description="Deny cloud agents",
        effect="deny",
        execution_kind="cloud_agent",
    )
    registry = _make_registry(rule)
    engine = PolicyEngine(policy_registry=registry)
    intent = TaskIntent(task_type="analysis", domain="analysis")
    descriptor = AgentDescriptor(
        agent_id="local-agent",
        display_name="Local Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis"],
    )
    context = PolicyEngine.build_execution_context(intent, descriptor)
    decision = engine.evaluate(intent, descriptor, context)

    assert decision.effect == "allow"
    assert decision.reason == "no_policy_matched"


# ---------------------------------------------------------------------------
# 4. Priority ordering — higher priority wins
# ---------------------------------------------------------------------------


def test_higher_priority_rule_wins_over_lower():
    low_priority = _make_rule(
        id="low-allow",
        description="Low priority allow",
        effect="allow",
        priority=1,
        capability="deploy",
    )
    high_priority = _make_rule(
        id="high-deny",
        description="High priority deny",
        effect="deny",
        priority=10,
        capability="deploy",
    )
    registry = _make_registry(low_priority, high_priority)
    matched = registry.get_applicable_policies(_make_context(required_capabilities=["deploy"]))

    assert len(matched) == 2
    assert matched[0].id == "high-deny"  # highest priority first
    assert matched[1].id == "low-allow"


def test_engine_uses_highest_priority_rule():
    low = _make_rule(id="low-allow", description="Allow", effect="allow", priority=1, capability="x")
    high = _make_rule(id="high-deny", description="Deny", effect="deny", priority=5, capability="x")
    engine = PolicyEngine(policy_registry=_make_registry(low, high))
    intent = TaskIntent(task_type="test", domain="analysis", required_capabilities=["x"])
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert decision.effect == "deny"
    assert decision.winning_rule_id == "high-deny"
    assert decision.winning_priority == 5


# ---------------------------------------------------------------------------
# 5. Effect ordering within same priority
# ---------------------------------------------------------------------------


def test_effect_ordering_tiebreak_within_same_priority():
    """Within the same priority, deny > require_approval > allow."""
    allow_rule = _make_rule(
        id="same-allow",
        description="Allow",
        effect="allow",
        priority=0,
        capability="x",
    )
    require_rule = _make_rule(
        id="same-require",
        description="Require approval",
        effect="require_approval",
        priority=0,
        capability="x",
    )
    deny_rule = _make_rule(
        id="same-deny",
        description="Deny",
        effect="deny",
        priority=0,
        capability="x",
    )
    registry = _make_registry(allow_rule, require_rule, deny_rule)
    matched = registry.get_applicable_policies(_make_context(required_capabilities=["x"]))

    assert len(matched) == 3
    assert matched[0].id == "same-deny"
    assert matched[1].id == "same-require"
    assert matched[2].id == "same-allow"


def test_engine_picks_most_restrictive_when_priority_tied():
    allow_rule = _make_rule(id="allow", description="Allow", effect="allow", priority=0, capability="x")
    deny_rule = _make_rule(id="deny", description="Deny", effect="deny", priority=0, capability="x")
    engine = PolicyEngine(policy_registry=_make_registry(allow_rule, deny_rule))
    intent = TaskIntent(task_type="test", domain="analysis", required_capabilities=["x"])
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert decision.effect == "deny"
    assert decision.winning_rule_id == "deny"


# ---------------------------------------------------------------------------
# 6. Multi-rule resolution — all matched rules returned, winner is first
# ---------------------------------------------------------------------------


def test_all_matched_rules_listed_in_decision():
    r1 = _make_rule(id="rule-a", description="A", effect="allow", priority=5, capability="x")
    r2 = _make_rule(id="rule-b", description="B", effect="require_approval", priority=3, capability="x")
    r3 = _make_rule(id="rule-c", description="C", effect="deny", priority=3, capability="x")
    engine = PolicyEngine(policy_registry=_make_registry(r1, r2, r3))
    intent = TaskIntent(task_type="test", domain="analysis", required_capabilities=["x"])
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert decision.winning_rule_id == "rule-a"  # highest priority
    assert set(decision.matched_rules) == {"rule-a", "rule-b", "rule-c"}


def test_non_matching_rules_not_included_in_decision():
    r_match = _make_rule(id="match", description="Match", effect="deny", capability="deploy")
    r_nomatch = _make_rule(id="no-match", description="No match", effect="deny", capability="other")
    engine = PolicyEngine(policy_registry=_make_registry(r_match, r_nomatch))
    intent = TaskIntent(
        task_type="test",
        domain="analysis",
        required_capabilities=["deploy"],
    )
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert "no-match" not in decision.matched_rules
    assert "match" in decision.matched_rules


# ---------------------------------------------------------------------------
# 7. Compound rule (multiple conditions must ALL be met)
# ---------------------------------------------------------------------------


def test_compound_rule_requires_all_conditions_met():
    rule = _make_rule(
        id="compound",
        description="Cloud + high risk + side effect",
        effect="deny",
        execution_kind="cloud_agent",
        risk_level="high",
        external_side_effect=True,
    )
    registry = _make_registry(rule)

    # All conditions met → match
    full_context = _make_context(
        execution_kind="cloud_agent",
        risk_level="high",
        external_side_effect=True,
    )
    assert len(registry.get_applicable_policies(full_context)) == 1

    # Missing one condition → no match
    partial_context = _make_context(
        execution_kind="cloud_agent",
        risk_level="high",
        external_side_effect=False,  # mismatch
    )
    assert registry.get_applicable_policies(partial_context) == []


# ---------------------------------------------------------------------------
# 8. PolicyRegistry JSON load/reload
# ---------------------------------------------------------------------------


def test_registry_loads_from_json_file(tmp_path):
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "policies": [
                    {
                        "id": "deny-cloud",
                        "description": "Deny cloud agents",
                        "execution_kind": "cloud_agent",
                        "effect": "deny",
                        "priority": 5,
                    },
                    {
                        "id": "require-high-risk",
                        "description": "Require approval for high risk",
                        "risk_level": "high",
                        "effect": "require_approval",
                        "priority": 3,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    registry = PolicyRegistry(path=policy_file)
    rules = registry.list_rules()

    assert len(rules) == 2
    ids = {r.id for r in rules}
    assert ids == {"deny-cloud", "require-high-risk"}


def test_registry_load_returns_rules_list(tmp_path):
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps(
            [
                {
                    "id": "allow-all",
                    "description": "Catch-all allow",
                    "effect": "allow",
                }
            ]
        ),
        encoding="utf-8",
    )

    registry = PolicyRegistry()
    rules = registry.load_policies(policy_file)

    assert len(rules) == 1
    assert rules[0].id == "allow-all"


def test_registry_missing_file_returns_empty_rules(tmp_path):
    missing = tmp_path / "nonexistent.json"
    registry = PolicyRegistry(path=missing)
    assert registry.list_rules() == []


# ---------------------------------------------------------------------------
# 9. PolicyEngine with real AgentDescriptor
# ---------------------------------------------------------------------------


def test_engine_reason_includes_agent_display_name():
    rule = _make_rule(
        id="block-cloud",
        description="Block cloud",
        effect="deny",
        execution_kind="cloud_agent",
    )
    engine = PolicyEngine(policy_registry=_make_registry(rule))
    descriptor = AgentDescriptor(
        agent_id="cloud-agent-1",
        display_name="Cloud Executor",
        source_type=AgentSourceType.CODEX,
        execution_kind=AgentExecutionKind.CLOUD_AGENT,
        capabilities=["analysis"],
    )
    intent = TaskIntent(task_type="analysis", domain="analysis")
    context = PolicyEngine.build_execution_context(intent, descriptor)
    decision = engine.evaluate(intent, descriptor, context)

    assert decision.effect == "deny"
    assert "Cloud Executor" in decision.reason


def test_engine_reason_uses_fallback_for_no_agent():
    rule = _make_rule(
        id="deny-anon",
        description="Deny anonymous",
        effect="deny",
        source_type=None,  # matches anything
        execution_kind=None,
    )
    # Engine with no agent should still return a decision
    engine = PolicyEngine(policy_registry=_make_registry(rule))
    intent = TaskIntent(task_type="analysis", domain="analysis")
    context = PolicyEngine.build_execution_context(intent, None)
    decision = engine.evaluate(intent, None, context)

    assert "unselected-agent" in decision.reason


# ---------------------------------------------------------------------------
# 10. build_execution_context field mapping
# ---------------------------------------------------------------------------


def test_build_execution_context_maps_agent_fields():
    descriptor = AgentDescriptor(
        agent_id="native-1",
        display_name="Native Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis"],
    )
    intent = TaskIntent(
        task_type="analysis",
        domain="ops",
        risk="high",
        required_capabilities=["analysis"],
    )
    ctx = PolicyEngine.build_execution_context(intent, descriptor)

    assert ctx.agent_id == "native-1"
    assert ctx.source_type == "native"
    assert ctx.execution_kind == "local_process"
    assert ctx.risk_level == "high"
    assert "analysis" in ctx.required_capabilities
    assert ctx.is_local is True  # LOCAL_PROCESS → inferred as local


def test_build_execution_context_cloud_agent_inferred_non_local():
    descriptor = AgentDescriptor(
        agent_id="cloud-1",
        display_name="Cloud Agent",
        source_type=AgentSourceType.CODEX,
        execution_kind=AgentExecutionKind.CLOUD_AGENT,
        capabilities=["analysis"],
    )
    intent = TaskIntent(task_type="analysis", domain="analysis")
    ctx = PolicyEngine.build_execution_context(intent, descriptor)

    assert ctx.is_local is False


def test_build_execution_context_no_agent_is_local_none():
    intent = TaskIntent(task_type="analysis", domain="analysis")
    ctx = PolicyEngine.build_execution_context(intent, None)

    assert ctx.agent_id is None
    assert ctx.is_local is None


# ---------------------------------------------------------------------------
# 11. PolicyRule model validation
# ---------------------------------------------------------------------------


def test_policy_rule_rejects_blank_id():
    with pytest.raises(Exception):
        PolicyRule(id="  ", description="Valid", effect="allow")


def test_policy_rule_rejects_blank_description():
    with pytest.raises(Exception):
        PolicyRule(id="valid", description="  ", effect="allow")


def test_policy_rule_rejects_invalid_effect():
    with pytest.raises(Exception):
        PolicyRule(id="valid", description="Valid", effect="approve")  # not a valid effect


def test_policy_rule_normalizes_whitespace():
    rule = PolicyRule(id="  my-rule  ", description="  A rule  ", effect="deny")
    assert rule.id == "my-rule"
    assert rule.description == "A rule"
