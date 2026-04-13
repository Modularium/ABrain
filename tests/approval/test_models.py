from datetime import UTC, datetime

import pytest

from core.approval import ApprovalDecision, ApprovalRequest, ApprovalStatus
from core.decision import AgentExecutionKind, AgentSourceType, CapabilityRisk

pytestmark = pytest.mark.unit


def test_approval_request_is_serializable_and_has_safe_defaults():
    request = ApprovalRequest(
        plan_id="plan-1",
        step_id="deploy",
        task_summary="Deploy the workflow",
        agent_id="workflow-agent",
        source_type=AgentSourceType.N8N,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        reason="external_side_effect",
        risk=CapabilityRisk.HIGH,
        proposed_action_summary="Execute deployment workflow in n8n",
    )

    payload = request.model_dump(mode="json")

    assert payload["status"] == "pending"
    assert payload["plan_id"] == "plan-1"
    assert payload["step_id"] == "deploy"


def test_approval_decision_rejects_pending_as_terminal_state():
    with pytest.raises(ValueError):
        ApprovalDecision(
            approval_id="approval-1",
            decision=ApprovalStatus.PENDING,
            decided_by="reviewer",
            decided_at=datetime.now(UTC),
        )


def test_approval_decision_accepts_optional_rating():
    decision = ApprovalDecision(
        approval_id="approval-2",
        decision=ApprovalStatus.APPROVED,
        decided_by="reviewer",
        rating=0.8,
    )

    assert decision.rating == pytest.approx(0.8)
    payload = decision.model_dump(mode="json")
    assert payload["rating"] == pytest.approx(0.8)


def test_approval_decision_rating_defaults_to_none():
    decision = ApprovalDecision(
        approval_id="approval-3",
        decision=ApprovalStatus.APPROVED,
        decided_by="reviewer",
    )

    assert decision.rating is None
    payload = decision.model_dump(mode="json")
    assert payload["rating"] is None


def test_approval_decision_rejects_rating_out_of_range():
    with pytest.raises(Exception):
        ApprovalDecision(
            approval_id="approval-4",
            decision=ApprovalStatus.APPROVED,
            decided_by="reviewer",
            rating=1.5,
        )
