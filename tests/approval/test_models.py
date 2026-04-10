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
