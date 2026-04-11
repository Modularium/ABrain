"""Tests for PlanStateStore — durable plan execution result storage.

Verifies that:
1. Completed plan results survive a simulated restart
2. Paused plan state (next_step_index, pending_approval_id) is preserved
3. Upsert is idempotent on plan_id
4. list_recent returns correct order (most recent first)
5. list_by_status filters correctly
6. trace_id linkage is stored and readable
"""

from __future__ import annotations

import pytest

pydantic = pytest.importorskip("pydantic", reason="pydantic required for plan models")

from pathlib import Path

from core.orchestration.result_aggregation import (
    OrchestrationStatus,
    PlanExecutionResult,
    PlanExecutionState,
    StepExecutionResult,
)
from core.orchestration.state_store import PlanStateStore


def _completed_result(plan_id: str = "plan-001") -> PlanExecutionResult:
    step = StepExecutionResult(
        step_id="step-1",
        selected_agent_id="agent-x",
        success=True,
        output={"answer": "42"},
    )
    state = PlanExecutionState(
        status=OrchestrationStatus.COMPLETED,
        next_step_index=None,
        next_step_id=None,
        pending_approval_id=None,
        step_results=[step],
        metadata={"completed_step_ids": ["step-1"]},
    )
    return PlanExecutionResult(
        plan_id=plan_id,
        success=True,
        status=OrchestrationStatus.COMPLETED,
        step_results=[step],
        final_output={"answer": "42"},
        state=state,
        metadata={"strategy": "single"},
    )


def _paused_result(plan_id: str = "plan-paused", approval_id: str = "approval-abc") -> PlanExecutionResult:
    state = PlanExecutionState(
        status=OrchestrationStatus.PAUSED,
        next_step_index=1,
        next_step_id="step-2",
        pending_approval_id=approval_id,
        step_results=[],
        metadata={"approval_request": {"approval_id": approval_id}},
    )
    return PlanExecutionResult(
        plan_id=plan_id,
        success=False,
        status=OrchestrationStatus.PAUSED,
        step_results=[],
        final_output=None,
        state=state,
        metadata={"pending_approval_id": approval_id},
    )


class TestPlanStatePersistence:
    def test_completed_result_survives_restart(self, tmp_path: Path) -> None:
        """A completed plan result is readable after creating a new PlanStateStore instance."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        result = _completed_result()
        store.save_result(result, trace_id="trace-001")

        # Simulate restart: new store instance, same DB file.
        reloaded = PlanStateStore(db_path)
        loaded = reloaded.get_result("plan-001")
        assert loaded is not None
        assert loaded.plan_id == "plan-001"
        assert loaded.success is True
        assert loaded.status == OrchestrationStatus.COMPLETED
        assert loaded.final_output == {"answer": "42"}

    def test_paused_state_preserved(self, tmp_path: Path) -> None:
        """Paused plan state (next_step_index, pending_approval_id) survives reload."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        result = _paused_result(approval_id="approval-xyz")
        store.save_result(result, trace_id="trace-002")

        reloaded = PlanStateStore(db_path)
        state = reloaded.get_state("plan-paused")
        assert state is not None
        assert state.status == OrchestrationStatus.PAUSED
        assert state.next_step_index == 1
        assert state.next_step_id == "step-2"
        assert state.pending_approval_id == "approval-xyz"

    def test_upsert_is_idempotent(self, tmp_path: Path) -> None:
        """Saving the same plan_id twice overwrites without creating duplicates."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)

        result_v1 = _paused_result()
        store.save_result(result_v1)

        result_v2 = _completed_result(plan_id="plan-paused")
        store.save_result(result_v2)

        rows = store.list_recent(limit=10)
        plan_ids = [r["plan_id"] for r in rows]
        assert plan_ids.count("plan-paused") == 1, "upsert must not create duplicate rows"

        loaded = store.get_result("plan-paused")
        assert loaded.status == OrchestrationStatus.COMPLETED, "second write should overwrite first"

    def test_trace_id_linkage_persisted(self, tmp_path: Path) -> None:
        """trace_id column is stored and returned in list_recent."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        store.save_result(_completed_result("plan-linked"), trace_id="trace-linked-001")

        rows = store.list_recent()
        assert any(r["trace_id"] == "trace-linked-001" for r in rows)

    def test_list_recent_order(self, tmp_path: Path) -> None:
        """list_recent returns rows most-recently-updated first."""
        import time
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)

        store.save_result(_completed_result("plan-alpha"))
        time.sleep(0.01)
        store.save_result(_completed_result("plan-beta"))
        time.sleep(0.01)
        store.save_result(_completed_result("plan-gamma"))

        rows = store.list_recent(limit=3)
        plan_ids = [r["plan_id"] for r in rows]
        assert plan_ids[0] == "plan-gamma", "most recent should be first"
        assert plan_ids[-1] == "plan-alpha", "oldest should be last"

    def test_list_by_status(self, tmp_path: Path) -> None:
        """list_by_status returns only rows matching the given status."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        store.save_result(_completed_result("plan-c1"))
        store.save_result(_completed_result("plan-c2"))
        store.save_result(_paused_result("plan-p1", "appr-1"))

        completed = store.list_by_status(OrchestrationStatus.COMPLETED)
        paused = store.list_by_status(OrchestrationStatus.PAUSED)
        assert len(completed) == 2
        assert len(paused) == 1
        assert paused[0]["plan_id"] == "plan-p1"

    def test_get_result_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """get_result returns None for an unknown plan_id."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        assert store.get_result("nonexistent-plan") is None

    def test_get_state_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """get_state returns None for an unknown plan_id."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        assert store.get_state("nonexistent-plan") is None

    def test_pending_approval_id_column(self, tmp_path: Path) -> None:
        """pending_approval_id is stored in the column for quick paused-plan lookup."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)
        store.save_result(_paused_result("plan-x", "appr-999"))

        rows = store.list_by_status(OrchestrationStatus.PAUSED)
        assert rows[0]["pending_approval_id"] == "appr-999"
