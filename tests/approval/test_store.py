import pytest

from core.approval import ApprovalDecision, ApprovalRequest, ApprovalStatus, ApprovalStore
from core.decision import CapabilityRisk

pytestmark = pytest.mark.unit


def test_approval_store_persists_and_loads_requests(tmp_path):
    path = tmp_path / "approvals.json"
    store = ApprovalStore(path=path)
    request = ApprovalRequest(
        plan_id="plan-1",
        step_id="deploy",
        task_summary="Deploy the workflow",
        reason="external_side_effect",
        risk=CapabilityRisk.HIGH,
        proposed_action_summary="Run deployment workflow",
    )

    store.create_request(request)
    updated = store.record_decision(
        request.approval_id,
        ApprovalDecision(
            approval_id=request.approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="reviewer",
        ),
    )
    loaded = ApprovalStore.load_json(path)

    assert updated.status == ApprovalStatus.APPROVED
    assert loaded.get_request(request.approval_id) is not None
    assert loaded.get_request(request.approval_id).status == ApprovalStatus.APPROVED


def test_approval_store_lists_only_pending_requests():
    store = ApprovalStore()
    pending = store.create_request(
        ApprovalRequest(
            plan_id="plan-1",
            step_id="step-1",
            task_summary="Pending",
            reason="manual_review",
            risk=CapabilityRisk.MEDIUM,
            proposed_action_summary="Pending action",
        )
    )
    approved = store.create_request(
        ApprovalRequest(
            plan_id="plan-2",
            step_id="step-2",
            task_summary="Approved",
            reason="manual_review",
            risk=CapabilityRisk.MEDIUM,
            proposed_action_summary="Approved action",
        )
    )
    store.record_decision(
        approved.approval_id,
        ApprovalDecision(
            approval_id=approved.approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="reviewer",
        ),
    )

    pending_ids = [request.approval_id for request in store.list_pending()]

    assert pending_ids == [pending.approval_id]
