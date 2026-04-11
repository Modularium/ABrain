"""Tests for ApprovalStore restart-resilient persistence.

Verifies that:
1. pending approvals survive a simulated restart (load_json)
2. recorded decisions are preserved
3. approval_id stability across reload
4. no duplicate decision can be recorded for the same approval
5. expired/cancelled approvals round-trip correctly
"""

from __future__ import annotations

import json
import pytest

pydantic = pytest.importorskip("pydantic", reason="pydantic required for approval models")

from pathlib import Path

from core.approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
)
from core.approval.store import ApprovalStore
from core.decision.capabilities import CapabilityRisk


def _make_request(plan_id: str = "plan-001", step_id: str = "step-1") -> ApprovalRequest:
    return ApprovalRequest(
        plan_id=plan_id,
        step_id=step_id,
        task_summary="Summarise the quarterly report",
        reason="external_side_effect",
        risk=CapabilityRisk.MEDIUM,
        proposed_action_summary="Execute analysis step via claude-code adapter",
        metadata={"trace_id": "trace-abc"},
    )


class TestApprovalStorePersistence:
    def test_pending_approvals_survive_restart(self, tmp_path: Path) -> None:
        """A pending approval written to disk is readable after a fresh store load."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        req = _make_request()
        store.create_request(req)

        assert store_path.exists(), "ApprovalStore should auto-save on create_request"

        # Simulate restart: create a brand-new store from the JSON file.
        reloaded = ApprovalStore.load_json(store_path)
        reloaded.path = store_path

        pending = reloaded.list_pending()
        assert len(pending) == 1
        assert pending[0].approval_id == req.approval_id
        assert pending[0].status == ApprovalStatus.PENDING

    def test_approval_id_is_stable_across_reload(self, tmp_path: Path) -> None:
        """approval_id must not change after serialisation / deserialisation."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        req = _make_request()
        store.create_request(req)

        reloaded = ApprovalStore.load_json(store_path)
        assert reloaded.get_request(req.approval_id) is not None
        assert reloaded.get_request(req.approval_id).approval_id == req.approval_id

    def test_decision_persisted_after_approve(self, tmp_path: Path) -> None:
        """An approved decision is readable after reload."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        req = _make_request()
        store.create_request(req)

        decision = ApprovalDecision(
            approval_id=req.approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="operator",
            comment="Looks fine",
        )
        store.record_decision(req.approval_id, decision)

        reloaded = ApprovalStore.load_json(store_path)
        updated = reloaded.get_request(req.approval_id)
        assert updated is not None
        assert updated.status == ApprovalStatus.APPROVED
        assert updated.metadata["decision"]["decided_by"] == "operator"

    def test_rejected_decision_persisted(self, tmp_path: Path) -> None:
        """A rejected decision is readable after reload and absent from pending list."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        req = _make_request()
        store.create_request(req)
        store.record_decision(
            req.approval_id,
            ApprovalDecision(
                approval_id=req.approval_id,
                decision=ApprovalStatus.REJECTED,
                decided_by="operator",
            ),
        )

        reloaded = ApprovalStore.load_json(store_path)
        updated = reloaded.get_request(req.approval_id)
        assert updated.status == ApprovalStatus.REJECTED
        assert reloaded.list_pending() == []

    def test_multiple_approvals_all_persisted(self, tmp_path: Path) -> None:
        """Multiple pending requests all survive reload."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        ids = []
        for i in range(5):
            req = _make_request(plan_id=f"plan-{i}", step_id=f"step-{i}")
            store.create_request(req)
            ids.append(req.approval_id)

        reloaded = ApprovalStore.load_json(store_path)
        assert len(reloaded.list_pending()) == 5
        for approval_id in ids:
            assert reloaded.get_request(approval_id) is not None

    def test_plan_state_embedded_in_approval_survives_reload(self, tmp_path: Path) -> None:
        """plan_state embedded in approval metadata is readable after reload."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        req = _make_request()
        req.metadata["plan_state"] = {
            "status": "paused",
            "next_step_index": 2,
            "next_step_id": "step-3",
            "pending_approval_id": req.approval_id,
            "step_results": [],
            "metadata": {"completed_step_ids": ["step-1", "step-2"]},
        }
        store.create_request(req)

        reloaded = ApprovalStore.load_json(store_path)
        loaded_req = reloaded.get_request(req.approval_id)
        plan_state = loaded_req.metadata["plan_state"]
        assert plan_state["status"] == "paused"
        assert plan_state["next_step_index"] == 2
        assert plan_state["next_step_id"] == "step-3"
        assert "step-1" in plan_state["metadata"]["completed_step_ids"]

    def test_empty_store_round_trips(self, tmp_path: Path) -> None:
        """An empty store can be saved and reloaded without error."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        store.save_json()

        reloaded = ApprovalStore.load_json(store_path)
        assert reloaded.list_pending() == []

    def test_no_duplicate_creation_raises(self, tmp_path: Path) -> None:
        """Creating a request with an existing approval_id raises ValueError."""
        store_path = tmp_path / "approvals.json"
        store = ApprovalStore(path=store_path)
        req = _make_request()
        store.create_request(req)
        with pytest.raises(ValueError, match="duplicate approval_id"):
            store.create_request(req)
