"""Resume helpers for paused multi-step orchestration."""

from __future__ import annotations

from typing import Any

from core.approval import ApprovalDecision, ApprovalPolicy, ApprovalRequest, ApprovalStatus, ApprovalStore
from core.audit import add_span_event, finish_span, start_child_span
from core.decision import AgentCreationEngine, AgentDescriptor, AgentRegistry, FeedbackLoop, RoutingEngine
from core.decision.plan_models import ExecutionPlan
from core.execution.execution_engine import ExecutionEngine
from core.governance import PolicyEngine

from .orchestrator import PlanExecutionOrchestrator
from .result_aggregation import OrchestrationStatus, PlanExecutionResult, PlanExecutionState, ResultAggregator, StepExecutionResult


def resume_plan(
    approval_request: ApprovalRequest,
    *,
    registry: AgentRegistry | list[AgentDescriptor] | dict[str, AgentDescriptor],
    routing_engine: RoutingEngine,
    execution_engine: ExecutionEngine,
    feedback_loop: FeedbackLoop,
    creation_engine: AgentCreationEngine | None = None,
    approval_policy: ApprovalPolicy | None = None,
    approval_store: ApprovalStore | None = None,
    policy_engine: PolicyEngine | None = None,
    orchestrator: PlanExecutionOrchestrator | None = None,
    trace_context: Any | None = None,
) -> PlanExecutionResult:
    """Resume a previously paused plan from a stored approval request."""
    decision = ApprovalDecision.model_validate(approval_request.metadata.get("decision") or {})
    plan = ExecutionPlan.model_validate(approval_request.metadata.get("plan") or {})
    state = PlanExecutionState.model_validate(approval_request.metadata.get("plan_state") or {})
    if state.status != OrchestrationStatus.PAUSED:
        raise ValueError("resume_plan requires a paused plan state")

    resume_span = start_child_span(
        trace_context,
        span_type="approval",
        name="resume_plan",
        attributes={
            "approval_id": approval_request.approval_id,
            "decision": decision.decision.value,
            "user_rating": decision.rating,
        },
    )
    if decision.decision == ApprovalStatus.APPROVED:
        add_span_event(
            trace_context,
            resume_span,
            event_type="approval_approved",
            message="human approval granted",
            payload={"approval_id": approval_request.approval_id},
        )
        add_span_event(
            trace_context,
            resume_span,
            event_type="plan_resumed",
            message="paused plan resumed after approval",
            payload={"step_id": approval_request.step_id},
        )
        orchestrator = orchestrator or PlanExecutionOrchestrator()
        result = orchestrator.execute_plan(
            plan,
            registry,
            routing_engine,
            execution_engine,
            feedback_loop,
            creation_engine=creation_engine,
            approval_policy=approval_policy,
            approval_store=approval_store,
            policy_engine=policy_engine,
            start_step_index=state.next_step_index or 0,
            existing_step_results=list(state.step_results),
            approved_step_ids={state.next_step_id} if state.next_step_id else set(),
            approved_step_rating=decision.rating,
            trace_context=trace_context,
        )
        finish_span(
            trace_context,
            resume_span,
            status="completed" if result.success else "failed",
            attributes={"result_status": result.status.value},
        )
        return result

    add_span_event(
        trace_context,
        resume_span,
        event_type="approval_rejected",
        message="human approval rejected the pending step",
        payload={"approval_id": approval_request.approval_id, "step_id": approval_request.step_id},
    )
    rejected_step = StepExecutionResult(
        step_id=approval_request.step_id,
        selected_agent_id=approval_request.agent_id,
        success=False,
        output={
            "approval_status": decision.decision.value,
            "step_id": approval_request.step_id,
        },
        warnings=[f"approval_{decision.decision.value}"],
        metadata={
            "approval_status": decision.decision.value,
            "approval_decision": decision.model_dump(mode="json"),
            "approval_reason": approval_request.reason,
        },
    )
    ordered_results = list(state.step_results) + [rejected_step]
    aggregator = (orchestrator.result_aggregator if orchestrator is not None else ResultAggregator())
    result = aggregator.aggregate(
        plan.task_id,
        ordered_results,
        status=OrchestrationStatus.REJECTED,
        state=PlanExecutionState(
            status=OrchestrationStatus.REJECTED,
            next_step_index=None,
            next_step_id=None,
            pending_approval_id=approval_request.approval_id,
            step_results=ordered_results,
            metadata={
                "approval_request": approval_request.model_dump(mode="json"),
                "approval_decision": decision.model_dump(mode="json"),
            },
        ),
        metadata={
            "strategy": plan.strategy.value,
            "plan_metadata": plan.metadata,
            "approval_terminal_decision": decision.decision.value,
        },
    )
    finish_span(
        trace_context,
        resume_span,
        status="rejected",
        attributes={"result_status": result.status.value},
    )
    if trace_context is not None:
        trace_context.finish_trace(
            status=result.status.value,
            metadata={
                "plan_id": plan.task_id,
                "approval_terminal_decision": decision.decision.value,
            },
        )
    return result
