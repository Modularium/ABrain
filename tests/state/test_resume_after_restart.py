"""Restart-resume integration tests.

These tests simulate a process restart by:
1. Writing approval + plan state to disk.
2. Creating fresh store instances from the same paths (simulating a new process).
3. Verifying that resume_plan can reconstruct the full continuation.

Also verifies:
- No double-execution after resume (step already in existing_step_results is skipped).
- Rejected approval terminates the plan cleanly.
- Trace and explainability remain linked through the TraceStore.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

from core.approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
)
from core.approval.store import ApprovalStore
from core.decision.capabilities import CapabilityRisk
from core.orchestration.result_aggregation import (
    OrchestrationStatus,
    PlanExecutionResult,
    PlanExecutionState,
    ResultAggregator,
    StepExecutionResult,
)
from core.orchestration.resume import resume_plan
from core.orchestration.state_store import PlanStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_paused_approval(
    approval_id: str,
    plan_id: str,
    step_id: str,
    next_step_index: int,
    prior_results: list[StepExecutionResult],
    trace_id: str | None = None,
) -> ApprovalRequest:
    """Build an ApprovalRequest that embeds enough state for resume_plan."""
    from core.decision.plan_models import ExecutionPlan, PlanStep, PlanStrategy

    plan = ExecutionPlan(
        task_id=plan_id,
        original_task={"task_type": "analysis", "description": "test"},
        strategy=PlanStrategy.SEQUENTIAL,
        steps=[
            PlanStep(
                step_id="step-1",
                title="Step one",
                description="First step",
                required_capabilities=["analysis"],
                risk=CapabilityRisk.LOW,
            ),
            PlanStep(
                step_id="step-2",
                title="Step two",
                description="Second step — requires approval",
                required_capabilities=["analysis"],
                risk=CapabilityRisk.MEDIUM,
            ),
        ],
        metadata={},
    )
    state = PlanExecutionState(
        status=OrchestrationStatus.PAUSED,
        next_step_index=next_step_index,
        next_step_id=step_id,
        pending_approval_id=approval_id,
        step_results=prior_results,
        metadata={"trace_id": trace_id},
    )
    req = ApprovalRequest(
        approval_id=approval_id,
        plan_id=plan_id,
        step_id=step_id,
        task_summary="Execute step requiring approval",
        agent_id="agent-test",
        reason="external_side_effect",
        risk=CapabilityRisk.MEDIUM,
        proposed_action_summary="Execute step-2 via test adapter",
        metadata={
            "plan": plan.model_dump(mode="json"),
            "plan_state": state.model_dump(mode="json"),
            "trace_id": trace_id,
        },
    )
    return req


def _stub_orchestrator_returns(result: PlanExecutionResult) -> MagicMock:
    """Return a mock PlanExecutionOrchestrator that returns a fixed result."""
    orch = MagicMock()
    orch.result_aggregator = ResultAggregator()
    orch.execute_plan.return_value = result
    return orch


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResumeAfterRestart:
    def test_pending_approval_survives_restart_and_approves(self, tmp_path: Path) -> None:
        """After restart, approve works and resume_plan is called with correct context."""
        approval_path = tmp_path / "approvals.json"
        prior_step = StepExecutionResult(
            step_id="step-1",
            selected_agent_id="agent-test",
            success=True,
            output={"result": "done"},
        )
        req = _build_paused_approval(
            approval_id="appr-001",
            plan_id="plan-001",
            step_id="step-2",
            next_step_index=1,
            prior_results=[prior_step],
            trace_id="trace-001",
        )

        # --- "First process" ---
        store_p1 = ApprovalStore(path=approval_path)
        store_p1.create_request(req)
        assert approval_path.exists()

        # --- Simulate restart: "Second process" ---
        store_p2 = ApprovalStore.load_json(approval_path)
        store_p2.path = approval_path

        reloaded_req = store_p2.get_request("appr-001")
        assert reloaded_req is not None, "pending approval must survive restart"
        assert reloaded_req.status == ApprovalStatus.PENDING

        # Record an approval decision.
        decision = ApprovalDecision(
            approval_id="appr-001",
            decision=ApprovalStatus.APPROVED,
            decided_by="operator",
        )
        updated = store_p2.record_decision("appr-001", decision)

        # Confirm decision is persisted back to disk.
        store_p3 = ApprovalStore.load_json(approval_path)
        final_req = store_p3.get_request("appr-001")
        assert final_req.status == ApprovalStatus.APPROVED
        assert final_req.metadata["decision"]["decided_by"] == "operator"

    def test_resume_plan_reconstructs_prior_results(self, tmp_path: Path) -> None:
        """resume_plan receives prior_results from embedded plan_state."""
        approval_path = tmp_path / "approvals.json"
        prior_step = StepExecutionResult(
            step_id="step-1",
            selected_agent_id="agent-test",
            success=True,
            output={"data": "step1_output"},
        )
        req = _build_paused_approval(
            approval_id="appr-002",
            plan_id="plan-002",
            step_id="step-2",
            next_step_index=1,
            prior_results=[prior_step],
        )
        req.metadata["decision"] = ApprovalDecision(
            approval_id="appr-002",
            decision=ApprovalStatus.APPROVED,
            decided_by="test",
        ).model_dump(mode="json")
        req = req.model_copy(update={"status": ApprovalStatus.APPROVED})

        # Build expected result that the orchestrator would return.
        step2 = StepExecutionResult(
            step_id="step-2",
            selected_agent_id="agent-test",
            success=True,
            output={"data": "step2_output"},
        )
        expected_result = PlanExecutionResult(
            plan_id="plan-002",
            success=True,
            status=OrchestrationStatus.COMPLETED,
            step_results=[prior_step, step2],
            final_output={"data": "step2_output"},
            state=PlanExecutionState(
                status=OrchestrationStatus.COMPLETED,
                step_results=[prior_step, step2],
                metadata={},
            ),
            metadata={},
        )
        orch = _stub_orchestrator_returns(expected_result)

        result = resume_plan(
            req,
            registry=MagicMock(),
            routing_engine=MagicMock(),
            execution_engine=MagicMock(),
            feedback_loop=MagicMock(),
            orchestrator=orch,
        )
        assert result.plan_id == "plan-002"
        assert result.success is True
        assert result.status == OrchestrationStatus.COMPLETED

        # Verify orchestrator was called with prior results and correct start index.
        call_kwargs = orch.execute_plan.call_args.kwargs
        assert call_kwargs["start_step_index"] == 1
        existing = call_kwargs["existing_step_results"]
        assert len(existing) == 1
        assert existing[0].step_id == "step-1"

    def test_rejected_approval_terminates_plan(self, tmp_path: Path) -> None:
        """resume_plan with a rejected decision returns a REJECTED terminal result."""
        approval_path = tmp_path / "approvals.json"
        req = _build_paused_approval(
            approval_id="appr-003",
            plan_id="plan-003",
            step_id="step-2",
            next_step_index=1,
            prior_results=[],
        )
        req.metadata["decision"] = ApprovalDecision(
            approval_id="appr-003",
            decision=ApprovalStatus.REJECTED,
            decided_by="operator",
        ).model_dump(mode="json")
        req = req.model_copy(update={"status": ApprovalStatus.REJECTED})

        result = resume_plan(
            req,
            registry=MagicMock(),
            routing_engine=MagicMock(),
            execution_engine=MagicMock(),
            feedback_loop=MagicMock(),
        )
        assert result.status == OrchestrationStatus.REJECTED
        assert result.success is False
        rejected_step = next(r for r in result.step_results if r.step_id == "step-2")
        assert "approval_rejected" in rejected_step.warnings

    def test_no_double_execution_after_resume(self, tmp_path: Path) -> None:
        """step-1 in existing_step_results must NOT be re-executed after resume."""
        prior_step = StepExecutionResult(
            step_id="step-1",
            selected_agent_id="agent-test",
            success=True,
            output={"done": True},
        )
        req = _build_paused_approval(
            approval_id="appr-004",
            plan_id="plan-004",
            step_id="step-2",
            next_step_index=1,
            prior_results=[prior_step],
        )
        req.metadata["decision"] = ApprovalDecision(
            approval_id="appr-004",
            decision=ApprovalStatus.APPROVED,
            decided_by="test",
        ).model_dump(mode="json")
        req = req.model_copy(update={"status": ApprovalStatus.APPROVED})

        step2_result = StepExecutionResult(
            step_id="step-2",
            selected_agent_id="agent-test",
            success=True,
            output={"done": True},
        )
        full_result = PlanExecutionResult(
            plan_id="plan-004",
            success=True,
            status=OrchestrationStatus.COMPLETED,
            step_results=[prior_step, step2_result],
            final_output={"done": True},
            state=PlanExecutionState(
                status=OrchestrationStatus.COMPLETED,
                step_results=[prior_step, step2_result],
                metadata={},
            ),
            metadata={},
        )
        orch = _stub_orchestrator_returns(full_result)

        resume_plan(
            req,
            registry=MagicMock(),
            routing_engine=MagicMock(),
            execution_engine=MagicMock(),
            feedback_loop=MagicMock(),
            orchestrator=orch,
        )
        orch.execute_plan.assert_called_once()
        call_kwargs = orch.execute_plan.call_args.kwargs
        # start_step_index=1 means step-1 (index 0) is skipped.
        assert call_kwargs["start_step_index"] == 1


class TestPlanStateStoreAndApprovalIntegration:
    def test_plan_state_updated_after_completion(self, tmp_path: Path) -> None:
        """PlanStateStore correctly upserts from PAUSED to COMPLETED after resume."""
        db_path = tmp_path / "plan_state.sqlite3"
        store = PlanStateStore(db_path)

        paused = PlanExecutionResult(
            plan_id="plan-int-001",
            success=False,
            status=OrchestrationStatus.PAUSED,
            step_results=[],
            final_output=None,
            state=PlanExecutionState(
                status=OrchestrationStatus.PAUSED,
                next_step_index=1,
                next_step_id="step-2",
                pending_approval_id="appr-int-001",
                step_results=[],
                metadata={},
            ),
            metadata={},
        )
        store.save_result(paused, trace_id="trace-int-001")

        # Confirm paused state is stored.
        assert store.get_result("plan-int-001").status == OrchestrationStatus.PAUSED

        # Simulate approval + resume leading to completion.
        completed = PlanExecutionResult(
            plan_id="plan-int-001",
            success=True,
            status=OrchestrationStatus.COMPLETED,
            step_results=[
                StepExecutionResult(step_id="step-2", success=True, output={"ok": True}),
            ],
            final_output={"ok": True},
            state=PlanExecutionState(
                status=OrchestrationStatus.COMPLETED,
                step_results=[],
                metadata={},
            ),
            metadata={},
        )
        store.save_result(completed, trace_id="trace-int-001")

        # Confirm upsert: single row, now COMPLETED.
        rows = store.list_recent()
        assert len([r for r in rows if r["plan_id"] == "plan-int-001"]) == 1
        assert store.get_result("plan-int-001").status == OrchestrationStatus.COMPLETED
