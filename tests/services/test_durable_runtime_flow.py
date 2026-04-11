"""Durable runtime flow tests for services/core.py.

Verifies:
1. _get_approval_state() loads from disk when ABRAIN_APPROVAL_STORE_PATH exists.
2. _get_plan_state_store() initialises PlanStateStore at configured path.
3. _get_learning_state() loads PerformanceHistoryStore from disk.
4. list_recent_plans() uses PlanStateStore when available.
5. Existing sanity behaviour of list_pending_approvals / get_trace is unchanged.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pydantic = pytest.importorskip("pydantic", reason="pydantic required for core models")


def _reset_service_state() -> None:
    """Remove cached process-local state from services.core helpers."""
    import services.core as core_mod
    for attr in (
        "_get_approval_state",
        "_get_trace_state",
        "_get_plan_state_store",
        "_get_learning_state",
        "_get_governance_state",
    ):
        fn = getattr(core_mod, attr, None)
        if fn is not None and hasattr(fn, "_state"):
            del fn._state


class TestApprovalStateLoadsFromDisk:
    def test_approval_store_loads_existing_json(self, tmp_path: Path) -> None:
        """_get_approval_state() rehydrates from disk when the JSON file exists."""
        from core.approval.models import ApprovalRequest, ApprovalStatus
        from core.approval.store import ApprovalStore
        from core.decision.capabilities import CapabilityRisk

        approval_path = tmp_path / "approvals.json"
        req = ApprovalRequest(
            plan_id="plan-svc-001",
            step_id="step-1",
            task_summary="Service layer test",
            reason="external_side_effect",
            risk=CapabilityRisk.LOW,
            proposed_action_summary="Test approval",
        )
        prior_store = ApprovalStore(path=approval_path)
        prior_store.create_request(req)

        _reset_service_state()
        env = {"ABRAIN_APPROVAL_STORE_PATH": str(approval_path)}
        with patch.dict(os.environ, env):
            import services.core as core_mod
            state = core_mod._get_approval_state()
            store = state["store"]
            pending = store.list_pending()
            assert len(pending) == 1
            assert pending[0].approval_id == req.approval_id
        _reset_service_state()

    def test_approval_store_creates_fresh_when_no_file(self, tmp_path: Path) -> None:
        """_get_approval_state() creates a new store (with path) when no file exists."""
        approval_path = tmp_path / "new_approvals.json"
        _reset_service_state()
        env = {"ABRAIN_APPROVAL_STORE_PATH": str(approval_path)}
        with patch.dict(os.environ, env):
            import services.core as core_mod
            state = core_mod._get_approval_state()
            store = state["store"]
            assert store.path == approval_path
            assert store.list_pending() == []
        _reset_service_state()

    def test_approval_store_auto_saves_to_disk(self, tmp_path: Path) -> None:
        """After _get_approval_state() is wired, create_request auto-saves."""
        from core.approval.models import ApprovalRequest
        from core.approval.store import ApprovalStore
        from core.decision.capabilities import CapabilityRisk

        approval_path = tmp_path / "auto_save.json"
        _reset_service_state()
        env = {"ABRAIN_APPROVAL_STORE_PATH": str(approval_path)}
        with patch.dict(os.environ, env):
            import services.core as core_mod
            state = core_mod._get_approval_state()
            store = state["store"]
            req = ApprovalRequest(
                plan_id="plan-auto",
                step_id="s1",
                task_summary="Auto-save test",
                reason="test",
                risk=CapabilityRisk.LOW,
                proposed_action_summary="Auto-save test action",
            )
            store.create_request(req)
        # After the context exits the file should exist.
        assert approval_path.exists(), "ApprovalStore must auto-save after create_request"
        data = json.loads(approval_path.read_text())
        assert req.approval_id in data
        _reset_service_state()


class TestPlanStateStoreInit:
    def test_plan_state_store_initialises(self, tmp_path: Path) -> None:
        """_get_plan_state_store() creates a PlanStateStore at the configured path."""
        db_path = tmp_path / "plan_state.sqlite3"
        _reset_service_state()
        env = {"ABRAIN_PLAN_STATE_DB_PATH": str(db_path)}
        with patch.dict(os.environ, env):
            import services.core as core_mod
            state = core_mod._get_plan_state_store()
            assert state["store"] is not None
            assert db_path.exists()
        _reset_service_state()

    def test_list_recent_plans_uses_plan_state_store(self, tmp_path: Path) -> None:
        """list_recent_plans() uses PlanStateStore when available, not trace scan."""
        from core.orchestration.result_aggregation import (
            OrchestrationStatus,
            PlanExecutionResult,
            PlanExecutionState,
        )
        from core.orchestration.state_store import PlanStateStore

        db_path = tmp_path / "plan_state.sqlite3"
        pss = PlanStateStore(db_path)
        pss.save_result(
            PlanExecutionResult(
                plan_id="plan-list-001",
                success=True,
                status=OrchestrationStatus.COMPLETED,
                step_results=[],
                final_output=None,
                state=PlanExecutionState(
                    status=OrchestrationStatus.COMPLETED,
                    step_results=[],
                    metadata={},
                ),
                metadata={},
            )
        )

        from core.approval.store import ApprovalStore
        appr_store = ApprovalStore()

        import services.core as core_mod
        result = core_mod.list_recent_plans(
            limit=5,
            plan_state_store=pss,
            approval_store=appr_store,
        )
        plans = result["plans"]
        assert len(plans) == 1
        assert plans[0]["plan_id"] == "plan-list-001"
        assert plans[0]["status"] == "completed"


class TestLearningStateLoadsFromDisk:
    def test_perf_history_loads_from_disk(self, tmp_path: Path) -> None:
        """_get_learning_state() loads PerformanceHistoryStore from disk."""
        from core.decision.performance_history import AgentPerformanceHistory, PerformanceHistoryStore

        perf_path = tmp_path / "perf.json"
        prior = PerformanceHistoryStore(
            {"agent-warm": AgentPerformanceHistory(success_rate=0.9, execution_count=50)}
        )
        prior.save_json(perf_path)

        _reset_service_state()
        env = {"ABRAIN_PERF_HISTORY_PATH": str(perf_path)}
        with patch.dict(os.environ, env):
            import services.core as core_mod
            state = core_mod._get_learning_state()
            perf = state["perf_history"]
            history = perf.get("agent-warm")
            assert history.success_rate == pytest.approx(0.9)
            assert history.execution_count == 50
        _reset_service_state()

    def test_perf_history_fresh_when_no_file(self, tmp_path: Path) -> None:
        """_get_learning_state() creates a fresh PerformanceHistoryStore when no file."""
        from core.decision.performance_history import AgentPerformanceHistory

        perf_path = tmp_path / "no_such_file.json"
        _reset_service_state()
        env = {"ABRAIN_PERF_HISTORY_PATH": str(perf_path)}
        with patch.dict(os.environ, env):
            import services.core as core_mod
            state = core_mod._get_learning_state()
            # Fresh store returns neutral defaults.
            history = state["perf_history"].get("unknown-agent")
            assert history.success_rate == pytest.approx(0.5)
        _reset_service_state()


class TestListPendingApprovals:
    def test_list_pending_uses_injected_store(self) -> None:
        """list_pending_approvals respects an injected approval_store."""
        from core.approval.models import ApprovalRequest
        from core.approval.store import ApprovalStore
        from core.decision.capabilities import CapabilityRisk

        store = ApprovalStore()
        req = ApprovalRequest(
            plan_id="plan-pending-test",
            step_id="step-1",
            task_summary="Pending test",
            reason="test",
            risk=CapabilityRisk.LOW,
            proposed_action_summary="Test pending approval",
        )
        store.create_request(req)

        import services.core as core_mod
        result = core_mod.list_pending_approvals(approval_store=store)
        assert len(result["approvals"]) == 1
        assert result["approvals"][0]["approval_id"] == req.approval_id
