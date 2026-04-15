"""S16 — Adapter policy binding contracts.

Phase 2, Step 2: jedem Tool/Adapter Policy-Regeln zuordnen.

These tests verify:
1. build_default_rules_for_manifest() — correct rules per risk tier
2. Per-adapter rule generation (all 6 adapters)
3. get_all_adapter_default_rules() — aggregation and id uniqueness
4. PolicyRegistry integration — generated rules are loadable and evaluable
5. Rule invariants — effect tiers, source_type binding, no empty descriptions
"""

from __future__ import annotations

import pytest

from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
from core.execution.adapters.codex_adapter import CodexExecutionAdapter
from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
from core.execution.adapters.policy_bindings import (
    build_default_rules_for_manifest,
    get_all_adapter_default_rules,
)
from core.execution.provider_capabilities import ExecutionCapabilities
from core.governance.policy_models import PolicyEvaluationContext, PolicyRule
from core.governance.policy_registry import PolicyRegistry

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_manifest(adapter_name: str, risk_tier: RiskTier) -> AdapterManifest:
    return AdapterManifest(
        adapter_name=adapter_name,
        description=f"Test manifest for {adapter_name}",
        capabilities=ExecutionCapabilities(
            execution_protocol="http_api",
            requires_network=False,
            requires_local_process=False,
            supports_cost_reporting=False,
            supports_token_reporting=False,
        ),
        risk_tier=risk_tier,
        recommended_policy_scope="test_scope",
    )


# ---------------------------------------------------------------------------
# Section 1: build_default_rules_for_manifest() — per risk tier
# ---------------------------------------------------------------------------


class TestBuildDefaultRulesLow:
    def test_low_returns_one_rule(self):
        manifest = _minimal_manifest("my_tool", RiskTier.LOW)
        rules = build_default_rules_for_manifest(manifest)
        assert len(rules) == 1

    def test_low_rule_is_allow(self):
        manifest = _minimal_manifest("my_tool", RiskTier.LOW)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].effect == "allow"

    def test_low_rule_source_type_matches_adapter_name(self):
        manifest = _minimal_manifest("my_tool", RiskTier.LOW)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].source_type == "my_tool"

    def test_low_rule_no_side_effect_constraint(self):
        """LOW adapters get one blanket allow — no external_side_effect filter."""
        manifest = _minimal_manifest("my_tool", RiskTier.LOW)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].external_side_effect is None

    def test_low_rule_non_empty_description(self):
        manifest = _minimal_manifest("my_tool", RiskTier.LOW)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].description.strip()


class TestBuildDefaultRulesMedium:
    def test_medium_returns_two_rules(self):
        manifest = _minimal_manifest("wf_tool", RiskTier.MEDIUM)
        rules = build_default_rules_for_manifest(manifest)
        assert len(rules) == 2

    def test_medium_first_rule_is_require_approval_for_side_effect(self):
        manifest = _minimal_manifest("wf_tool", RiskTier.MEDIUM)
        rules = build_default_rules_for_manifest(manifest)
        approval_rule = next(r for r in rules if r.external_side_effect is True)
        assert approval_rule.effect == "require_approval"

    def test_medium_second_rule_is_allow_baseline(self):
        manifest = _minimal_manifest("wf_tool", RiskTier.MEDIUM)
        rules = build_default_rules_for_manifest(manifest)
        allow_rule = next(r for r in rules if r.external_side_effect is None)
        assert allow_rule.effect == "allow"

    def test_medium_side_effect_rule_has_higher_priority(self):
        """The require_approval rule must out-prioritize the allow baseline."""
        manifest = _minimal_manifest("wf_tool", RiskTier.MEDIUM)
        rules = build_default_rules_for_manifest(manifest)
        approval_rule = next(r for r in rules if r.external_side_effect is True)
        allow_rule = next(r for r in rules if r.external_side_effect is None)
        assert approval_rule.priority > allow_rule.priority

    def test_medium_both_rules_bound_to_source_type(self):
        manifest = _minimal_manifest("wf_tool", RiskTier.MEDIUM)
        rules = build_default_rules_for_manifest(manifest)
        for rule in rules:
            assert rule.source_type == "wf_tool"

    def test_medium_rules_non_empty_descriptions(self):
        manifest = _minimal_manifest("wf_tool", RiskTier.MEDIUM)
        rules = build_default_rules_for_manifest(manifest)
        for rule in rules:
            assert rule.description.strip()


class TestBuildDefaultRulesHigh:
    def test_high_returns_one_rule(self):
        manifest = _minimal_manifest("exec_tool", RiskTier.HIGH)
        rules = build_default_rules_for_manifest(manifest)
        assert len(rules) == 1

    def test_high_rule_is_require_approval(self):
        manifest = _minimal_manifest("exec_tool", RiskTier.HIGH)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].effect == "require_approval"

    def test_high_rule_source_type_matches_adapter_name(self):
        manifest = _minimal_manifest("exec_tool", RiskTier.HIGH)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].source_type == "exec_tool"

    def test_high_rule_non_empty_description(self):
        manifest = _minimal_manifest("exec_tool", RiskTier.HIGH)
        rules = build_default_rules_for_manifest(manifest)
        assert rules[0].description.strip()


# ---------------------------------------------------------------------------
# Section 2: Per-adapter rule generation
# ---------------------------------------------------------------------------


def test_adminbot_rules_allow():
    """AdminBot (LOW) → one allow rule."""
    rules = build_default_rules_for_manifest(AdminBotExecutionAdapter.manifest)
    assert len(rules) == 1
    assert rules[0].effect == "allow"
    assert rules[0].source_type == "adminbot"


def test_flowise_rules_two_entries():
    """Flowise (MEDIUM) → two rules."""
    rules = build_default_rules_for_manifest(FlowiseExecutionAdapter.manifest)
    assert len(rules) == 2
    effects = {r.effect for r in rules}
    assert "allow" in effects
    assert "require_approval" in effects


def test_n8n_rules_two_entries():
    """n8n (MEDIUM) → two rules."""
    rules = build_default_rules_for_manifest(N8NExecutionAdapter.manifest)
    assert len(rules) == 2
    effects = {r.effect for r in rules}
    assert "allow" in effects
    assert "require_approval" in effects


def test_claude_code_rules_require_approval():
    """ClaudeCode (HIGH) → one require_approval rule."""
    rules = build_default_rules_for_manifest(ClaudeCodeExecutionAdapter.manifest)
    assert len(rules) == 1
    assert rules[0].effect == "require_approval"
    assert rules[0].source_type == "claude_code"


def test_codex_rules_require_approval():
    """Codex (HIGH) → one require_approval rule."""
    rules = build_default_rules_for_manifest(CodexExecutionAdapter.manifest)
    assert len(rules) == 1
    assert rules[0].effect == "require_approval"
    assert rules[0].source_type == "codex"


def test_openhands_rules_require_approval():
    """OpenHands (HIGH) → one require_approval rule."""
    rules = build_default_rules_for_manifest(OpenHandsExecutionAdapter.manifest)
    assert len(rules) == 1
    assert rules[0].effect == "require_approval"
    assert rules[0].source_type == "openhands"


# ---------------------------------------------------------------------------
# Section 3: get_all_adapter_default_rules() — aggregation
# ---------------------------------------------------------------------------


def test_get_all_rules_returns_list():
    rules = get_all_adapter_default_rules()
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_get_all_rules_count():
    """LOW=1, MEDIUM=2 each, HIGH=1 each → 1 + 2+2 + 1+1+1 = 8 rules."""
    rules = get_all_adapter_default_rules()
    assert len(rules) == 8


def test_get_all_rules_ids_unique():
    """Rule ids must be globally unique across all adapters."""
    rules = get_all_adapter_default_rules()
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)), f"Duplicate rule ids: {ids}"


def test_get_all_rules_covers_all_source_types():
    """Every canonical adapter source_type appears in the combined rule set."""
    expected_source_types = {
        "adminbot", "openhands", "claude_code", "codex", "flowise", "n8n"
    }
    rules = get_all_adapter_default_rules()
    found = {r.source_type for r in rules if r.source_type}
    assert expected_source_types == found


def test_get_all_rules_all_are_policy_rule_instances():
    rules = get_all_adapter_default_rules()
    for rule in rules:
        assert isinstance(rule, PolicyRule)


def test_get_all_rules_no_empty_descriptions():
    rules = get_all_adapter_default_rules()
    for rule in rules:
        assert rule.description.strip(), f"Rule {rule.id} has empty description"


def test_get_all_rules_effects_are_valid():
    valid_effects = {"allow", "require_approval", "deny"}
    rules = get_all_adapter_default_rules()
    for rule in rules:
        assert rule.effect in valid_effects


# ---------------------------------------------------------------------------
# Section 4: PolicyRegistry integration
# ---------------------------------------------------------------------------


def test_generated_rules_loadable_into_registry():
    """get_all_adapter_default_rules() output is directly usable by PolicyRegistry."""
    rules = get_all_adapter_default_rules()
    registry = PolicyRegistry(rules=rules)
    assert len(registry.list_rules()) == 8


def test_registry_matches_adminbot_context():
    """AdminBot context matches the allow rule."""
    rules = get_all_adapter_default_rules()
    registry = PolicyRegistry(rules=rules)
    context = PolicyEvaluationContext(
        task_type="system_status",
        source_type="adminbot",
        execution_kind="system_executor",
    )
    matched = registry.get_applicable_policies(context)
    assert len(matched) >= 1
    assert matched[0].effect == "allow"


def test_registry_matches_claude_code_context():
    """ClaudeCode context matches the require_approval rule."""
    rules = get_all_adapter_default_rules()
    registry = PolicyRegistry(rules=rules)
    context = PolicyEvaluationContext(
        task_type="code_generation",
        source_type="claude_code",
        execution_kind="local_process",
    )
    matched = registry.get_applicable_policies(context)
    assert len(matched) >= 1
    assert matched[0].effect == "require_approval"


def test_registry_matches_flowise_no_side_effect():
    """Flowise without external side effect → allow."""
    rules = get_all_adapter_default_rules()
    registry = PolicyRegistry(rules=rules)
    context = PolicyEvaluationContext(
        task_type="workflow",
        source_type="flowise",
        execution_kind="workflow_engine",
        external_side_effect=False,
    )
    matched = registry.get_applicable_policies(context)
    # The external_side_effect=True rule does NOT match here
    allow_rules = [r for r in matched if r.effect == "allow"]
    assert allow_rules, "Expected at least one allow rule for Flowise without side effects"


def test_registry_matches_flowise_with_side_effect():
    """Flowise with external side effect → require_approval wins (higher priority)."""
    rules = get_all_adapter_default_rules()
    registry = PolicyRegistry(rules=rules)
    context = PolicyEvaluationContext(
        task_type="workflow",
        source_type="flowise",
        execution_kind="workflow_engine",
        external_side_effect=True,
    )
    matched = registry.get_applicable_policies(context)
    assert matched[0].effect == "require_approval"


def test_registry_no_match_unknown_source_type():
    """Context with no matching source_type returns no rules."""
    rules = get_all_adapter_default_rules()
    registry = PolicyRegistry(rules=rules)
    context = PolicyEvaluationContext(
        task_type="unknown",
        source_type="nonexistent_adapter",
    )
    matched = registry.get_applicable_policies(context)
    assert matched == []


# ---------------------------------------------------------------------------
# Section 5: Rule invariants
# ---------------------------------------------------------------------------


def test_high_risk_adapters_never_produce_allow_rules():
    """No HIGH risk adapter should produce an allow rule."""
    for cls in (ClaudeCodeExecutionAdapter, CodexExecutionAdapter, OpenHandsExecutionAdapter):
        rules = build_default_rules_for_manifest(cls.manifest)
        for rule in rules:
            assert rule.effect != "allow", (
                f"{cls.adapter_name} (HIGH risk) produced an allow rule: {rule.id}"
            )


def test_low_risk_adapter_produces_only_allow():
    """AdminBot (LOW) must produce only allow rules."""
    rules = build_default_rules_for_manifest(AdminBotExecutionAdapter.manifest)
    for rule in rules:
        assert rule.effect == "allow"


def test_medium_adapters_have_both_effects():
    """Each MEDIUM adapter must produce both allow and require_approval."""
    for cls in (FlowiseExecutionAdapter, N8NExecutionAdapter):
        rules = build_default_rules_for_manifest(cls.manifest)
        effects = {r.effect for r in rules}
        assert "allow" in effects, f"{cls.adapter_name} missing allow rule"
        assert "require_approval" in effects, f"{cls.adapter_name} missing require_approval rule"


def test_all_rules_have_valid_source_type():
    """Every generated rule specifies a non-empty source_type."""
    rules = get_all_adapter_default_rules()
    for rule in rules:
        assert rule.source_type is not None
        assert rule.source_type.strip()
