"""Phase 2 S21 — Security enforcement tests for the governance layer.

Tests the policy enforcement chain built across S12–S16:

1. PolicyViolationError raised on "deny" — execution is hard-blocked
2. require_approval returns "approval_required" — execution is gated
3. allow returns "allowed" — execution proceeds
4. Deny at high priority overrides allow at low priority
5. All HIGH-tier adapters get require_approval from default rules
6. All LOW-tier adapters get allow from default rules
7. MEDIUM-tier: external side-effect → require_approval; otherwise → allow
8. PolicyRule structural validation — invalid rules rejected at construction
9. PolicyEvaluationContext normalization — whitespace-only strings become None
"""

from __future__ import annotations

import pytest

from core.governance.enforcement import PolicyViolationError, enforce_policy
from core.governance.policy_engine import PolicyEngine
from core.governance.policy_models import PolicyDecision, PolicyEvaluationContext, PolicyRule
from core.governance.policy_registry import PolicyRegistry

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decision(effect: str, reason: str = "test") -> PolicyDecision:
    return PolicyDecision(effect=effect, reason=reason)


def _rule(**kwargs) -> PolicyRule:
    defaults = {"id": "r", "description": "test rule", "effect": "allow", "priority": 0}
    defaults.update(kwargs)
    return PolicyRule.model_validate(defaults)


def _context(**kwargs) -> PolicyEvaluationContext:
    defaults = {"task_type": "analysis"}
    defaults.update(kwargs)
    return PolicyEvaluationContext.model_validate(defaults)


def _engine(*rules: PolicyRule) -> PolicyEngine:
    return PolicyEngine(policy_registry=PolicyRegistry(rules=list(rules)))


# ---------------------------------------------------------------------------
# 1. enforce_policy — the hard enforcement gate
# ---------------------------------------------------------------------------


class TestEnforcePolicy:
    def test_deny_raises_policy_violation_error(self):
        with pytest.raises(PolicyViolationError):
            enforce_policy(_decision("deny", "forbidden action"))

    def test_policy_violation_error_carries_decision(self):
        decision = _decision("deny", "forbidden")
        with pytest.raises(PolicyViolationError) as exc_info:
            enforce_policy(decision)
        assert exc_info.value.decision is decision

    def test_policy_violation_error_message_is_reason(self):
        decision = _decision("deny", "reason: highly sensitive action blocked")
        with pytest.raises(PolicyViolationError) as exc_info:
            enforce_policy(decision)
        assert "highly sensitive action blocked" in str(exc_info.value)

    def test_require_approval_returns_string_without_raising(self):
        result = enforce_policy(_decision("require_approval"))
        assert result == "approval_required"

    def test_allow_returns_allowed_string(self):
        result = enforce_policy(_decision("allow"))
        assert result == "allowed"


# ---------------------------------------------------------------------------
# 2. Priority ordering — deny at high priority overrides allow at low
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    def test_deny_high_priority_overrides_allow_low_priority(self):
        deny_rule = _rule(id="deny-high", effect="deny", priority=100, source_type="codex")
        allow_rule = _rule(id="allow-low", effect="allow", priority=0, source_type="codex")
        engine = _engine(deny_rule, allow_rule)
        ctx = _context(source_type="codex")
        from core.decision.task_intent import TaskIntent
        decision = engine.evaluate(TaskIntent(task_type="analysis", domain="general"), None, ctx)
        assert decision.effect == "deny"
        assert decision.winning_rule_id == "deny-high"

    def test_require_approval_high_priority_overrides_allow_low(self):
        approval_rule = _rule(id="approval-high", effect="require_approval", priority=50, source_type="flowise")
        allow_rule = _rule(id="allow-low", effect="allow", priority=0, source_type="flowise")
        engine = _engine(approval_rule, allow_rule)
        ctx = _context(source_type="flowise")
        from core.decision.task_intent import TaskIntent
        decision = engine.evaluate(TaskIntent(task_type="analysis", domain="general"), None, ctx)
        assert decision.effect == "require_approval"

    def test_no_matching_rule_defaults_to_allow_with_no_policy_matched_reason(self):
        rule = _rule(id="codex-only", effect="deny", source_type="codex")
        engine = _engine(rule)
        ctx = _context(source_type="adminbot")
        from core.decision.task_intent import TaskIntent
        decision = engine.evaluate(TaskIntent(task_type="analysis", domain="general"), None, ctx)
        assert decision.effect == "allow"
        assert decision.reason == "no_policy_matched"


# ---------------------------------------------------------------------------
# 3. Adapter-tier enforcement via default policy bindings
# ---------------------------------------------------------------------------


class TestAdapterTierEnforcement:
    def _rules_for(self, adapter_cls):
        from core.execution.adapters.policy_bindings import build_default_rules_for_manifest
        return build_default_rules_for_manifest(adapter_cls.manifest)

    def test_all_high_tier_adapters_get_require_approval(self):
        from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
        from core.execution.adapters.codex_adapter import CodexExecutionAdapter
        from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
        for cls in [ClaudeCodeExecutionAdapter, CodexExecutionAdapter, OpenHandsExecutionAdapter]:
            rules = self._rules_for(cls)
            effects = {r.effect for r in rules}
            assert effects == {"require_approval"}, (
                f"{cls.__name__} HIGH-tier should have only require_approval rules, got {effects}"
            )

    def test_low_tier_adapter_gets_allow_only(self):
        from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
        rules = self._rules_for(AdminBotExecutionAdapter)
        effects = {r.effect for r in rules}
        assert effects == {"allow"}, (
            f"AdminBot LOW-tier should have only allow rules, got {effects}"
        )

    def test_medium_tier_adapter_gets_both_rules(self):
        from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
        from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
        for cls in [FlowiseExecutionAdapter, N8NExecutionAdapter]:
            rules = self._rules_for(cls)
            effects = {r.effect for r in rules}
            assert "require_approval" in effects, (
                f"{cls.__name__} MEDIUM-tier should include require_approval rule"
            )
            assert "allow" in effects, (
                f"{cls.__name__} MEDIUM-tier should include allow fallback rule"
            )

    def test_medium_tier_external_side_effect_triggers_require_approval(self):
        from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
        from core.execution.adapters.policy_bindings import build_default_rules_for_manifest
        from core.decision.task_intent import TaskIntent
        rules = build_default_rules_for_manifest(FlowiseExecutionAdapter.manifest)
        engine = PolicyEngine(policy_registry=PolicyRegistry(rules=rules))
        ctx = _context(
            source_type=FlowiseExecutionAdapter.adapter_name,
            external_side_effect=True,
        )
        decision = engine.evaluate(TaskIntent(task_type="workflow", domain="automation"), None, ctx)
        assert decision.effect == "require_approval"

    def test_medium_tier_no_external_side_effect_allows(self):
        from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
        from core.execution.adapters.policy_bindings import build_default_rules_for_manifest
        from core.decision.task_intent import TaskIntent
        rules = build_default_rules_for_manifest(FlowiseExecutionAdapter.manifest)
        engine = PolicyEngine(policy_registry=PolicyRegistry(rules=rules))
        ctx = _context(
            source_type=FlowiseExecutionAdapter.adapter_name,
            external_side_effect=False,
        )
        decision = engine.evaluate(TaskIntent(task_type="workflow", domain="automation"), None, ctx)
        assert decision.effect == "allow"

    def test_combined_default_rules_all_have_nonempty_ids(self):
        from core.execution.adapters.policy_bindings import get_all_adapter_default_rules
        rules = get_all_adapter_default_rules()
        for rule in rules:
            assert rule.id.strip(), f"Rule has empty id: {rule!r}"

    def test_combined_default_rules_high_tier_adapters_present(self):
        from core.execution.adapters.policy_bindings import get_all_adapter_default_rules
        rules = get_all_adapter_default_rules()
        high_tier_rules = [r for r in rules if r.effect == "require_approval"]
        # ClaudeCode, Codex, OpenHands → 1 rule each = 3 minimum
        assert len(high_tier_rules) >= 3


# ---------------------------------------------------------------------------
# 4. PolicyRule structural validation
# ---------------------------------------------------------------------------


class TestPolicyRuleStructuralValidation:
    def test_empty_id_rejected(self):
        with pytest.raises(Exception):
            PolicyRule(id="", description="x", effect="allow")

    def test_whitespace_id_rejected(self):
        with pytest.raises(Exception):
            PolicyRule(id="   ", description="x", effect="allow")

    def test_empty_description_rejected(self):
        with pytest.raises(Exception):
            PolicyRule(id="r1", description="", effect="allow")

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            PolicyRule(
                id="r1",
                description="x",
                effect="allow",
                hidden_override="bypass_all",
            )

    def test_invalid_effect_rejected(self):
        with pytest.raises(Exception):
            PolicyRule(id="r1", description="x", effect="permit")

    def test_negative_priority_accepted(self):
        rule = PolicyRule(id="r1", description="x", effect="allow", priority=-1)
        assert rule.priority == -1

    def test_negative_max_cost_rejected(self):
        with pytest.raises(Exception):
            PolicyRule(id="r1", description="x", effect="deny", max_cost=-1.0)


# ---------------------------------------------------------------------------
# 5. PolicyEvaluationContext normalization — string injection boundary
# ---------------------------------------------------------------------------


class TestEvaluationContextNormalization:
    """Whitespace-only strings are coerced to None to prevent empty-string
    source_type or execution_kind from accidentally matching policy rules."""

    def test_whitespace_only_source_type_becomes_none(self):
        ctx = _context(source_type="   ")
        assert ctx.source_type is None

    def test_whitespace_only_execution_kind_becomes_none(self):
        ctx = _context(execution_kind="   ")
        assert ctx.execution_kind is None

    def test_whitespace_only_agent_id_becomes_none(self):
        ctx = _context(agent_id="   ")
        assert ctx.agent_id is None

    def test_whitespace_only_risk_level_becomes_none(self):
        ctx = _context(risk_level="   ")
        assert ctx.risk_level is None

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            PolicyEvaluationContext(task_type="x", bypass_audit=True)

    def test_empty_task_type_rejected(self):
        with pytest.raises(Exception):
            PolicyEvaluationContext(task_type="")

    def test_empty_required_capability_silently_stripped(self):
        ctx = PolicyEvaluationContext(task_type="x", required_capabilities=["valid", ""])
        assert ctx.required_capabilities == ["valid"]

    def test_duplicate_capabilities_deduplicated(self):
        ctx = _context(required_capabilities=["cap_a", "cap_b", "cap_a"])
        assert ctx.required_capabilities == ["cap_a", "cap_b"]

    def test_negative_estimated_cost_rejected(self):
        with pytest.raises(Exception):
            PolicyEvaluationContext(task_type="x", estimated_cost=-0.01)
