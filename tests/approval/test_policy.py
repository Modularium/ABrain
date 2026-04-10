import pytest

from core.approval import ApprovalPolicy
from core.decision import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    CapabilityRisk,
)
from core.decision.plan_models import PlanStep

pytestmark = pytest.mark.unit


def test_approval_policy_requires_human_review_for_external_workflow_side_effects():
    policy = ApprovalPolicy()
    step = PlanStep(
        step_id="deploy",
        title="Deploy Workflow",
        description="Trigger the external deployment workflow.",
        required_capabilities=["workflow.execute"],
        risk=CapabilityRisk.MEDIUM,
        metadata={"task_type": "workflow_automation", "domain": "workflow", "external_side_effect": True},
    )
    descriptor = AgentDescriptor(
        agent_id="workflow-agent",
        display_name="Workflow Agent",
        source_type=AgentSourceType.N8N,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["workflow.execute"],
    )

    check = policy.evaluate(step, descriptor)

    assert check.required is True
    assert "workflow_engine_external_side_effect" in check.matched_rules


def test_approval_policy_keeps_low_risk_analysis_steps_unblocked():
    policy = ApprovalPolicy()
    step = PlanStep(
        step_id="analyze",
        title="Analyze",
        description="Inspect the codebase.",
        required_capabilities=["analysis.general"],
        risk=CapabilityRisk.LOW,
        metadata={"task_type": "analysis_general", "domain": "analysis"},
    )
    descriptor = AgentDescriptor(
        agent_id="analysis-agent",
        display_name="Analysis Agent",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["analysis.general"],
    )

    check = policy.evaluate(step, descriptor)

    assert check.required is False
    assert check.reason is None
