import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType, TaskIntent
from core.governance import (
    PolicyEngine,
    PolicyRegistry,
    PolicyRule,
    PolicyViolationError,
    enforce_policy,
)

pytestmark = pytest.mark.unit


def build_descriptor() -> AgentDescriptor:
    return AgentDescriptor(
        agent_id="codex-agent",
        display_name="Codex",
        source_type=AgentSourceType.CODEX,
        execution_kind=AgentExecutionKind.CLOUD_AGENT,
        capabilities=["code.generate"],
    )


def test_policy_engine_defaults_to_allow_without_rules():
    engine = PolicyEngine(policy_registry=PolicyRegistry())
    intent = TaskIntent(
        task_type="code_generate",
        domain="code",
        required_capabilities=["code.generate"],
    )
    descriptor = build_descriptor()

    decision = engine.evaluate(
        intent,
        descriptor,
        engine.build_execution_context(intent, descriptor),
    )

    assert decision.effect == "allow"
    assert decision.matched_rules == []
    assert decision.reason == "no_policy_matched"
    assert enforce_policy(decision) == "allowed"


def test_policy_engine_uses_priority_and_effect_order():
    engine = PolicyEngine(
        policy_registry=PolicyRegistry(
            rules=[
                PolicyRule(
                    id="allow-cloud-code",
                    description="Allow cloud code generation by default.",
                    capability="code.generate",
                    source_type="codex",
                    effect="allow",
                    priority=10,
                ),
                PolicyRule(
                    id="deny-expensive-cloud",
                    description="Deny expensive cloud code generation.",
                    capability="code.generate",
                    source_type="codex",
                    max_cost=1.0,
                    effect="deny",
                    priority=20,
                ),
                PolicyRule(
                    id="review-cloud-code",
                    description="Review cloud code generation over a moderate cost threshold.",
                    capability="code.generate",
                    source_type="codex",
                    max_cost=0.5,
                    effect="require_approval",
                    priority=20,
                ),
            ]
        )
    )
    intent = TaskIntent(
        task_type="code_generate",
        domain="code",
        required_capabilities=["code.generate"],
    )
    descriptor = build_descriptor()

    decision = engine.evaluate(
        intent,
        descriptor,
        engine.build_execution_context(
            intent,
            descriptor,
            metadata={"estimated_cost": 2.5},
        ),
    )

    assert decision.effect == "deny"
    assert decision.matched_rules == [
        "deny-expensive-cloud",
        "review-cloud-code",
        "allow-cloud-code",
    ]
    with pytest.raises(PolicyViolationError):
        enforce_policy(decision)


def test_policy_engine_can_trigger_approval_without_deny():
    engine = PolicyEngine(
        policy_registry=PolicyRegistry(
            rules=[
                PolicyRule(
                    id="review-remote-write",
                    description="Require approval for remote mutating code steps.",
                    capability="repo.modify",
                    source_type="claude_code",
                    effect="require_approval",
                    priority=5,
                )
            ]
        )
    )
    intent = TaskIntent(
        task_type="code_refactor",
        domain="code",
        required_capabilities=["repo.modify"],
    )
    descriptor = AgentDescriptor(
        agent_id="claude-agent",
        display_name="Claude Code",
        source_type=AgentSourceType.CLAUDE_CODE,
        execution_kind=AgentExecutionKind.CLOUD_AGENT,
        capabilities=["repo.modify"],
    )

    decision = engine.evaluate(
        intent,
        descriptor,
        engine.build_execution_context(intent, descriptor),
    )

    assert decision.effect == "require_approval"
    assert enforce_policy(decision) == "approval_required"
