"""Tests for Trace ↔ Plan ↔ Approval linkage.

Verifies that:
1. TraceStore is durable after restart (SQLite).
2. Explainability records with approval_id reference are queryable.
3. PlanStateStore.trace_id links plan results back to traces.
4. The triangle Plan ↔ Trace ↔ Approval is navigable at rest.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from pathlib import Path

from core.audit.trace_store import TraceStore
from core.audit.trace_models import ExplainabilityRecord
from core.orchestration.result_aggregation import (
    OrchestrationStatus,
    PlanExecutionResult,
    PlanExecutionState,
    StepExecutionResult,
)
from core.orchestration.state_store import PlanStateStore


def _explainability(trace_id: str, approval_id: str | None = None) -> ExplainabilityRecord:
    return ExplainabilityRecord(
        trace_id=trace_id,
        step_id="step-1",
        selected_agent_id="agent-x",
        candidate_agent_ids=["agent-x", "agent-y"],
        selected_score=0.85,
        routing_reason_summary="selected agent-x with score 0.850",
        matched_policy_ids=["rule-external-check"],
        approval_required=approval_id is not None,
        approval_id=approval_id,
        metadata={"winning_policy_rule": "rule-external-check"},
    )


class TestTraceDurability:
    def test_trace_survives_restart(self, tmp_path: Path) -> None:
        """A trace written to SQLite is readable after creating a new TraceStore."""
        db_path = tmp_path / "traces.sqlite3"
        store = TraceStore(db_path)
        record = store.create_trace("run_task_plan", task_id="task-001", trace_id="trace-durable-001")
        store.finish_trace("trace-durable-001", status="completed")

        # Simulate restart.
        reloaded = TraceStore(db_path)
        snapshot = reloaded.get_trace("trace-durable-001")
        assert snapshot is not None
        assert snapshot.trace.trace_id == "trace-durable-001"
        assert snapshot.trace.status == "completed"

    def test_explainability_with_approval_id_survives_restart(self, tmp_path: Path) -> None:
        """Explainability records that reference an approval_id are durable."""
        db_path = tmp_path / "traces.sqlite3"
        store = TraceStore(db_path)
        store.create_trace("run_task_plan", task_id="task-002", trace_id="trace-expl-001")
        span = store.start_span("trace-expl-001", span_type="step", name="plan_step:step-1")
        store.finish_span(span.span_id, status="paused")
        store.store_explainability(
            _explainability("trace-expl-001", approval_id="appr-link-001")
        )
        store.finish_trace("trace-expl-001", status="paused")

        # Simulate restart.
        reloaded = TraceStore(db_path)
        records = reloaded.get_explainability("trace-expl-001")
        assert len(records) == 1
        assert records[0].approval_id == "appr-link-001"
        assert records[0].approval_required is True

    def test_recent_traces_list_reflects_persisted_data(self, tmp_path: Path) -> None:
        """list_recent_traces returns all traces after reload."""
        db_path = tmp_path / "traces.sqlite3"
        store = TraceStore(db_path)
        for i in range(3):
            tid = f"trace-list-{i:03d}"
            store.create_trace("run_task_plan", trace_id=tid)
            store.finish_trace(tid, status="completed")

        reloaded = TraceStore(db_path)
        traces = reloaded.list_recent_traces(limit=10)
        trace_ids = [t.trace_id for t in traces]
        for i in range(3):
            assert f"trace-list-{i:03d}" in trace_ids


class TestPlanTraceLinkage:
    def test_trace_id_stored_in_plan_state_store(self, tmp_path: Path) -> None:
        """plan_state_store.trace_id correctly references the canonical trace."""
        trace_db = tmp_path / "traces.sqlite3"
        plan_db = tmp_path / "plan_state.sqlite3"

        trace_store = TraceStore(trace_db)
        plan_store = PlanStateStore(plan_db)

        trace = trace_store.create_trace("run_task_plan", task_id="task-link-001", trace_id="trace-link-001")
        trace_store.finish_trace("trace-link-001", status="completed")

        result = PlanExecutionResult(
            plan_id="plan-link-001",
            success=True,
            status=OrchestrationStatus.COMPLETED,
            step_results=[
                StepExecutionResult(step_id="step-1", success=True, output={"ok": True}),
            ],
            final_output={"ok": True},
            state=PlanExecutionState(
                status=OrchestrationStatus.COMPLETED,
                step_results=[],
                metadata={},
            ),
            metadata={},
        )
        plan_store.save_result(result, trace_id="trace-link-001")

        rows = plan_store.list_recent()
        assert rows[0]["trace_id"] == "trace-link-001"

        # Navigate: plan → trace.
        linked_trace = trace_store.get_trace("trace-link-001")
        assert linked_trace is not None
        assert linked_trace.trace.workflow_name == "run_task_plan"

    def test_full_triangle_plan_approval_trace(self, tmp_path: Path) -> None:
        """Plan, approval, and trace can all be navigated from any starting point."""
        from core.approval.models import ApprovalRequest, ApprovalStatus
        from core.approval.store import ApprovalStore
        from core.decision.capabilities import CapabilityRisk

        trace_db = tmp_path / "traces.sqlite3"
        plan_db = tmp_path / "plan_state.sqlite3"
        approval_path = tmp_path / "approvals.json"

        trace_store = TraceStore(trace_db)
        plan_store = PlanStateStore(plan_db)
        approval_store = ApprovalStore(path=approval_path)

        # 1. Create trace.
        trace_store.create_trace("run_task_plan", task_id="task-tri", trace_id="trace-tri-001")

        # 2. Create approval that references trace.
        req = ApprovalRequest(
            plan_id="plan-tri-001",
            step_id="step-1",
            task_summary="Triangle test step",
            reason="external_side_effect",
            risk=CapabilityRisk.MEDIUM,
            proposed_action_summary="Execute triangle test",
            metadata={"trace_id": "trace-tri-001", "plan": {}},
        )
        approval_store.create_request(req)

        # 3. Store explainability linking trace → approval.
        span = trace_store.start_span("trace-tri-001", span_type="step", name="plan_step:step-1")
        trace_store.store_explainability(
            _explainability("trace-tri-001", approval_id=req.approval_id)
        )
        trace_store.finish_span(span.span_id, status="paused")
        trace_store.finish_trace("trace-tri-001", status="paused")

        # 4. Save paused plan state.
        paused_result = PlanExecutionResult(
            plan_id="plan-tri-001",
            success=False,
            status=OrchestrationStatus.PAUSED,
            step_results=[],
            final_output=None,
            state=PlanExecutionState(
                status=OrchestrationStatus.PAUSED,
                next_step_index=0,
                next_step_id="step-1",
                pending_approval_id=req.approval_id,
                step_results=[],
                metadata={},
            ),
            metadata={},
        )
        plan_store.save_result(paused_result, trace_id="trace-tri-001")

        # --- Navigate the triangle from each vertex ---

        # Plan → Trace
        plan_row = plan_store.list_recent()[0]
        assert plan_row["trace_id"] == "trace-tri-001"
        trace_from_plan = trace_store.get_trace(plan_row["trace_id"])
        assert trace_from_plan is not None

        # Trace → Approval (via explainability)
        expl = trace_store.get_explainability("trace-tri-001")
        assert expl[0].approval_id == req.approval_id
        approval_from_trace = approval_store.get_request(expl[0].approval_id)
        assert approval_from_trace is not None

        # Approval → Plan (via metadata)
        plan_id_from_approval = approval_from_trace.plan_id
        plan_result = plan_store.get_result(plan_id_from_approval)
        assert plan_result is not None
        assert plan_result.status == OrchestrationStatus.PAUSED
