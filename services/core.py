from __future__ import annotations

"""Shared service helpers for CLI and API."""

import json
import logging
import os
from typing import Any, Dict

from core.decision.agent_descriptor import AgentAvailability, AgentTrustLevel
from core.decision.agent_quality import compute_agent_quality
from core.execution.adapters.registry import ExecutionAdapterRegistry
from core.execution.dispatcher import ExecutionDispatcher
from core.models import RequesterIdentity, RequesterType, ToolExecutionRequest
from core.model_context import ModelContext
from core.tools import build_default_registry

__all__ = [
    "approve_plan_step",
    "compute_evaluation_baselines",
    "evaluate_trace",
    "execute_tool",
    "get_control_plane_overview",
    "get_explainability",
    "get_governance_state",
    "get_trace",
    "list_agent_catalog",
    "list_pending_approvals",
    "list_recent_governance_decisions",
    "list_recent_plans",
    "list_recent_traces",
    "list_agents",
    "reject_plan_step",
    "run_task",
    "run_task_plan",
]

DEFAULT_REQUESTER = RequesterIdentity(
    type=RequesterType.AGENT,
    id="services.core",
)

logger = logging.getLogger(__name__)


def _build_dispatcher() -> ExecutionDispatcher:
    """Create the fixed execution dispatcher used by service helpers."""
    return ExecutionDispatcher(build_default_registry())


def execute_tool(
    tool_name: str,
    payload: Dict[str, Any] | None = None,
    *,
    requested_by: RequesterIdentity | None = None,
    run_id: str | None = None,
    correlation_id: str | None = None,
) -> Dict[str, Any]:
    """Execute a fixed internal tool with typed validation."""
    request = ToolExecutionRequest.from_raw(
        tool_name=tool_name,
        payload=payload or {},
        requested_by=requested_by or DEFAULT_REQUESTER,
        run_id=run_id,
        correlation_id=correlation_id,
    )
    result = _build_dispatcher().execute_sync(request)
    return result.output


def list_agents() -> Dict[str, Any]:
    """List agents from the canonical decision-layer registry."""
    from core.decision.agent_registry import AgentRegistry

    registry = AgentRegistry()
    return {"agents": [a.model_dump(mode="json") for a in registry.list_descriptors()]}


def run_task(
    task: Any,
    *,
    registry: Any | None = None,
    routing_engine: Any | None = None,
    execution_engine: Any | None = None,
    feedback_loop: Any | None = None,
    creation_engine: Any | None = None,
    approval_store: Any | None = None,
    policy_engine: Any | None = None,
    trace_store: Any | None = None,
) -> Dict[str, Any]:
    """Run the canonical decision -> execution -> feedback pipeline."""
    from core.decision import (
        AgentCreationEngine,
        AgentRegistry,
        FeedbackLoop,
        NeuralTrainer,
        OnlineUpdater,
        RoutingEngine,
        TrainingDataset,
    )
    from core.audit import create_trace_context, finish_span, record_error, start_child_span
    from core.execution.execution_engine import ExecutionEngine
    from core.governance import PolicyEngine, PolicyViolationError, enforce_policy

    registry = registry or AgentRegistry()
    routing_engine = routing_engine or RoutingEngine()
    execution_engine = execution_engine or ExecutionEngine()
    approval_state = _get_approval_state()
    approval_store = approval_store or approval_state["store"]
    governance_state = _get_governance_state()
    policy_engine = policy_engine or governance_state["engine"]
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    learning_state = _get_learning_state()
    feedback_loop = feedback_loop or FeedbackLoop(
        performance_history=routing_engine.performance_history,
        online_updater=learning_state["online_updater"],
        trainer=learning_state["trainer"],
        neural_policy=routing_engine.neural_policy,
    )
    creation_engine = creation_engine or AgentCreationEngine()
    task_mapping = _as_mapping(task)
    trace_context = create_trace_context(
        trace_store,
        workflow_name="run_task",
        task_id=_resolve_trace_task_id(task_mapping, default_prefix="task"),
        metadata={
            "entrypoint": "run_task",
            "task_type": str(task_mapping.get("task_type") or ""),
        },
    )

    routing_span = start_child_span(
        trace_context,
        span_type="decision",
        name="routing",
        attributes={"task_type": str(task_mapping.get("task_type") or "analysis")},
    )
    try:
        descriptors = registry.list_descriptors()
        planner_result = routing_engine.planner.plan(task)
        decision = routing_engine.route_intent(
            planner_result.intent,
            descriptors,
            diagnostics={"planner": planner_result.diagnostics},
        )
        created_agent = None
        if creation_engine.should_create_agent(decision.selected_score):
            created_agent = creation_engine.create_agent_from_task(
                task,
                decision.required_capabilities,
                registry=registry,
            )
            rerouted = routing_engine.route_intent(
                planner_result.intent,
                registry.list_descriptors(),
                diagnostics={"planner": planner_result.diagnostics},
            )
            if rerouted.selected_agent_id:
                decision = rerouted
            else:
                decision.selected_agent_id = created_agent.agent_id
        finish_span(
            trace_context,
            routing_span,
            status="completed",
            attributes={
                "selected_agent_id": decision.selected_agent_id,
                "selected_score": decision.selected_score,
                "candidate_count": len(decision.ranked_candidates),
                "rejected_count": len(decision.diagnostics.get("rejected_agents") or []),
            },
        )
    except Exception as exc:
        record_error(
            trace_context,
            routing_span,
            exc,
            message="routing_failed",
            payload={"task_type": str(task_mapping.get("task_type") or "analysis")},
        )
        trace_context.finish_trace(status="failed", metadata={"failed_stage": "routing"})
        raise

    selected_descriptor = registry.get(decision.selected_agent_id) if decision.selected_agent_id else None
    governance_span = start_child_span(
        trace_context,
        span_type="governance",
        name="policy_check",
        attributes={"selected_agent_id": decision.selected_agent_id},
    )
    policy_decision = policy_engine.evaluate(
        planner_result.intent,
        selected_descriptor,
        policy_engine.build_execution_context(
            planner_result.intent,
            selected_descriptor,
            task=task_mapping,
            task_id=task_mapping.get("task_id"),
            metadata={
                "external_side_effect": _extract_task_flag(task, "external_side_effect"),
                "risky_operation": _extract_task_flag(task, "risky_operation"),
                "requires_human_approval": _extract_task_flag(task, "requires_human_approval"),
            },
        ),
    )
    try:
        governance_result = enforce_policy(policy_decision)
    except PolicyViolationError:
        from core.execution.adapters.base import ExecutionResult
        from core.models.errors import StructuredError

        _store_trace_explainability(
            trace_context,
            step_id="execute",
            decision=decision,
            policy_decision=policy_decision,
            approval_required=False,
            approval_id=None,
            created_agent=created_agent,
        )
        finish_span(
            trace_context,
            governance_span,
            status="denied",
            attributes={
                "effect": "deny",
                "matched_rules": policy_decision.matched_rules,
            },
        )
        denied_execution = ExecutionResult(
            agent_id=decision.selected_agent_id or "",
            success=False,
            error=StructuredError(
                error_code="policy_denied",
                message=policy_decision.reason,
                details={
                    "matched_rules": policy_decision.matched_rules,
                    "task_type": decision.task_type,
                },
            ),
            metadata={"governance": policy_decision.model_dump(mode="json")},
            warnings=["policy_denied"],
        )
        trace_context.finish_trace(
            status="denied",
            metadata={
                "selected_agent_id": decision.selected_agent_id,
                "policy_effect": "deny",
            },
        )
        return {
            "status": "denied",
            "decision": decision.model_dump(mode="json"),
            "execution": denied_execution.model_dump(mode="json"),
            "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
            "feedback": None,
            "warnings": ["policy_denied"],
            "governance": policy_decision.model_dump(mode="json"),
            "approval": None,
            "trace": trace_context.summary(),
        }
    if governance_result == "approval_required":
        approval_payload = _build_single_step_approval_result(
            task,
            planner_result=planner_result,
            decision=decision,
            selected_descriptor=selected_descriptor,
            policy_decision=policy_decision,
            approval_store=approval_store,
            trace_context=trace_context,
        )
        _store_trace_explainability(
            trace_context,
            step_id="execute",
            decision=decision,
            policy_decision=policy_decision,
            approval_required=True,
            approval_id=approval_payload["approval"]["approval_id"],
            created_agent=created_agent,
        )
        finish_span(
            trace_context,
            governance_span,
            status="approval_required",
            attributes={
                "effect": "require_approval",
                "approval_id": approval_payload["approval"]["approval_id"],
                "matched_rules": policy_decision.matched_rules,
            },
        )
        trace_context.finish_trace(
            status="paused",
            metadata={
                "pending_approval_id": approval_payload["approval"]["approval_id"],
                "policy_effect": "require_approval",
            },
        )
        return {
            "status": "paused",
            "decision": decision.model_dump(mode="json"),
            "execution": None,
            "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
            "feedback": None,
            "warnings": [],
            "governance": policy_decision.model_dump(mode="json"),
            **approval_payload,
            "trace": trace_context.summary(),
        }
    _store_trace_explainability(
        trace_context,
        step_id="execute",
        decision=decision,
        policy_decision=policy_decision,
        approval_required=False,
        approval_id=None,
        created_agent=created_agent,
    )
    finish_span(
        trace_context,
        governance_span,
        status="completed",
        attributes={
            "effect": policy_decision.effect,
            "matched_rules": policy_decision.matched_rules,
        },
    )

    execution_span = start_child_span(
        trace_context,
        span_type="execution",
        name="adapter_execution",
        attributes={"selected_agent_id": decision.selected_agent_id},
    )
    try:
        from core.execution.audit import canonical_execution_span_attributes
        execution = execution_engine.execute(task, decision, registry)
        finish_span(
            trace_context,
            execution_span,
            status="completed" if execution.success else "failed",
            attributes=canonical_execution_span_attributes(
                execution,
                task_type=str(task_mapping.get("task_type") or ""),
                policy_effect=policy_decision.effect,
            ),
            error=execution.error.model_dump(mode="json") if execution.error is not None else None,
        )
    except Exception as exc:
        record_error(
            trace_context,
            execution_span,
            exc,
            message="execution_failed",
            payload={"selected_agent_id": decision.selected_agent_id},
        )
        trace_context.finish_trace(status="failed", metadata={"failed_stage": "execution"})
        raise
    feedback = None
    warnings: list[str] = []
    if execution.agent_id:
        selected_descriptor = registry.get(execution.agent_id)
        feedback_span = start_child_span(
            trace_context,
            span_type="learning",
            name="feedback_update",
            attributes={"agent_id": execution.agent_id},
        )
        try:
            feedback = feedback_loop.update_performance(
                execution.agent_id,
                execution,
                task=task,
                agent_descriptor=selected_descriptor,
            )
            warnings.extend(feedback.warnings)
            finish_span(
                trace_context,
                feedback_span,
                status="completed",
                attributes={
                    "reward": feedback.reward,
                    "token_count": feedback.token_count,
                    "user_rating": feedback.user_rating,
                    "dataset_size": feedback.dataset_size,
                    "training_triggered": feedback.training_metrics is not None,
                    "warning_count": len(feedback.warnings),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            warnings.append(f"feedback_loop_failed:{exc.__class__.__name__}")
            logger.warning(
                json.dumps(
                    {
                        "event": "feedback_loop_failed",
                        "agent_id": execution.agent_id,
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )
            record_error(
                trace_context,
                feedback_span,
                exc,
                message="feedback_loop_failed",
                payload={"agent_id": execution.agent_id},
            )

    trace_context.finish_trace(
        status="completed" if execution.success else "failed",
        metadata={
            "selected_agent_id": execution.agent_id,
            "warning_count": len(warnings),
            "execution_success": execution.success,
        },
    )
    return {
        "decision": decision.model_dump(mode="json"),
        "execution": execution.model_dump(mode="json"),
        "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
        "feedback": feedback.model_dump(mode="json") if feedback else None,
        "warnings": warnings,
        "governance": policy_decision.model_dump(mode="json"),
        "approval": None,
        "status": "completed",
        "trace": trace_context.summary(),
    }


def run_task_plan(
    task: Any,
    *,
    registry: Any | None = None,
    routing_engine: Any | None = None,
    execution_engine: Any | None = None,
    feedback_loop: Any | None = None,
    creation_engine: Any | None = None,
    plan_builder: Any | None = None,
    orchestrator: Any | None = None,
    approval_store: Any | None = None,
    approval_policy: Any | None = None,
    policy_engine: Any | None = None,
    trace_store: Any | None = None,
) -> Dict[str, Any]:
    """Run the canonical multi-step plan -> route -> execute -> feedback pipeline."""
    from core.approval import ApprovalPolicy, ApprovalStore
    from core.decision import (
        AgentCreationEngine,
        AgentRegistry,
        FeedbackLoop,
        NeuralTrainer,
        OnlineUpdater,
        PlanBuilder,
        RoutingEngine,
    )
    from core.audit import create_trace_context, finish_span, record_error, start_child_span
    from core.execution.execution_engine import ExecutionEngine
    from core.governance import PolicyEngine
    from core.orchestration import PlanExecutionOrchestrator

    registry = registry or AgentRegistry()
    routing_engine = routing_engine or RoutingEngine()
    execution_engine = execution_engine or ExecutionEngine()
    approval_state = _get_approval_state()
    approval_store = approval_store or approval_state["store"]
    approval_policy = approval_policy or approval_state["policy"]
    governance_state = _get_governance_state()
    policy_engine = policy_engine or governance_state["engine"]
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    learning_state = _get_learning_state()
    feedback_loop = feedback_loop or FeedbackLoop(
        performance_history=routing_engine.performance_history,
        online_updater=learning_state["online_updater"],
        trainer=learning_state["trainer"],
        neural_policy=routing_engine.neural_policy,
    )
    creation_engine = creation_engine or AgentCreationEngine()
    plan_builder = plan_builder or PlanBuilder(planner=routing_engine.planner)
    orchestrator = orchestrator or PlanExecutionOrchestrator()
    task_mapping = _as_mapping(task)
    trace_context = create_trace_context(
        trace_store,
        workflow_name="run_task_plan",
        task_id=_resolve_trace_task_id(task_mapping, default_prefix="plan"),
        metadata={
            "entrypoint": "run_task_plan",
            "task_type": str(task_mapping.get("task_type") or ""),
        },
    )
    planning_span = start_child_span(
        trace_context,
        span_type="planning",
        name="build_execution_plan",
        attributes={"task_type": str(task_mapping.get("task_type") or "analysis")},
    )
    try:
        plan = plan_builder.build(task)
        finish_span(
            trace_context,
            planning_span,
            status="completed",
            attributes={
                "plan_id": plan.task_id,
                "strategy": plan.strategy.value,
                "step_count": len(plan.steps),
            },
        )
    except Exception as exc:
        record_error(
            trace_context,
            planning_span,
            exc,
            message="plan_build_failed",
            payload={"task_type": str(task_mapping.get("task_type") or "analysis")},
        )
        trace_context.finish_trace(status="failed", metadata={"failed_stage": "planning"})
        raise
    try:
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
            trace_context=trace_context,
        )
    except Exception:
        trace_context.finish_trace(status="failed", metadata={"failed_stage": "plan_execution"})
        raise
    # Persist the plan execution result so it survives a process restart.
    plan_state = _get_plan_state_store()
    if plan_state["store"] is not None:
        try:
            plan_state["store"].save_result(
                result,
                trace_id=getattr(trace_context, "trace_id", None),
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            logger.warning(
                json.dumps(
                    {
                        "event": "plan_state_save_failed",
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                        "plan_id": result.plan_id,
                    },
                    sort_keys=True,
                )
            )
    return {
        "plan": plan.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "trace": trace_context.summary(),
    }


def approve_plan_step(
    approval_id: str,
    *,
    decided_by: str = "human",
    comment: str | None = None,
    rating: float | None = None,
    registry: Any | None = None,
    routing_engine: Any | None = None,
    execution_engine: Any | None = None,
    feedback_loop: Any | None = None,
    creation_engine: Any | None = None,
    orchestrator: Any | None = None,
    approval_store: Any | None = None,
    approval_policy: Any | None = None,
    policy_engine: Any | None = None,
    trace_store: Any | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Approve a paused plan step and resume execution."""
    return _decide_plan_step(
        approval_id,
        decision="approved",
        decided_by=decided_by,
        comment=comment,
        rating=rating,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=execution_engine,
        feedback_loop=feedback_loop,
        creation_engine=creation_engine,
        orchestrator=orchestrator,
        approval_store=approval_store,
        approval_policy=approval_policy,
        policy_engine=policy_engine,
        trace_store=trace_store,
        metadata=metadata,
    )


def reject_plan_step(
    approval_id: str,
    *,
    decided_by: str = "human",
    comment: str | None = None,
    rating: float | None = None,
    registry: Any | None = None,
    routing_engine: Any | None = None,
    execution_engine: Any | None = None,
    feedback_loop: Any | None = None,
    creation_engine: Any | None = None,
    orchestrator: Any | None = None,
    approval_store: Any | None = None,
    approval_policy: Any | None = None,
    policy_engine: Any | None = None,
    trace_store: Any | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Reject a paused plan step and return the terminal plan result."""
    return _decide_plan_step(
        approval_id,
        decision="rejected",
        decided_by=decided_by,
        comment=comment,
        rating=rating,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=execution_engine,
        feedback_loop=feedback_loop,
        creation_engine=creation_engine,
        orchestrator=orchestrator,
        approval_store=approval_store,
        approval_policy=approval_policy,
        policy_engine=policy_engine,
        trace_store=trace_store,
        metadata=metadata,
    )


def list_pending_approvals(*, approval_store: Any | None = None) -> Dict[str, Any]:
    """List pending approval requests from the canonical approval store."""
    approval_state = _get_approval_state()
    approval_store = approval_store or approval_state["store"]
    return {
        "approvals": [
            request.model_dump(mode="json") for request in approval_store.list_pending()
        ]
    }


def get_trace(trace_id: str, *, trace_store: Any | None = None) -> Dict[str, Any]:
    """Return a stored trace snapshot for internal inspection."""
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    if trace_store is None:
        return {"trace": None}
    snapshot = trace_store.get_trace(trace_id)
    return {"trace": snapshot.model_dump(mode="json") if snapshot is not None else None}


def list_recent_traces(limit: int = 10, *, trace_store: Any | None = None) -> Dict[str, Any]:
    """List recent traces for internal diagnostics."""
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    if trace_store is None:
        return {"traces": []}
    return {
        "traces": [
            record.model_dump(mode="json") for record in trace_store.list_recent_traces(limit=limit)
        ]
    }


def get_explainability(trace_id: str, *, trace_store: Any | None = None) -> Dict[str, Any]:
    """Return explainability records for a stored trace."""
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    if trace_store is None:
        return {"explainability": []}
    return {
        "explainability": [
            record.model_dump(mode="json") for record in trace_store.get_explainability(trace_id)
        ]
    }


def list_recent_plans(
    limit: int = 10,
    *,
    trace_store: Any | None = None,
    approval_store: Any | None = None,
    plan_state_store: Any | None = None,
) -> Dict[str, Any]:
    """Return recent plan executions from PlanStateStore (primary) with
    trace-scan fallback for plans not yet recorded there.

    Priority:
    1. PlanStateStore — O(1) index on updated_at; always up to date after Phase N.
    2. Trace scan — backward-compatible fallback for plans recorded before
       Phase N or when the PlanStateStore is unavailable.
    """
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    approval_state = _get_approval_state()
    approval_store = approval_store or approval_state["store"]

    # --- Primary path: PlanStateStore ---
    pss_state = _get_plan_state_store()
    plan_state_store = plan_state_store if plan_state_store is not None else pss_state["store"]

    if plan_state_store is not None:
        try:
            rows = plan_state_store.list_recent(limit)
            # Enrich each row with approval linkage where relevant.
            pending_by_plan: dict[str, dict[str, Any]] = {}
            for request in approval_store.list_pending():
                if request.plan_id:
                    pending_by_plan[request.plan_id] = request.model_dump(mode="json")

            plans: list[dict[str, Any]] = []
            for row in rows:
                approval = pending_by_plan.get(row["plan_id"])
                plan_meta = approval.get("metadata", {}).get("plan") if approval else None
                state_meta = approval.get("metadata", {}).get("plan_state") if approval else None
                plans.append(
                    {
                        "plan_id": row["plan_id"],
                        "trace_id": row["trace_id"],
                        "workflow_name": "run_task_plan",
                        "task_id": None,
                        "status": row["status"],
                        "started_at": row["created_at"],
                        "ended_at": row["updated_at"] if row["status"] != "paused" else None,
                        "pending_approval_id": row.get("pending_approval_id") or (approval or {}).get("approval_id"),
                        "policy_effect": None,
                        "plan": plan_meta,
                        "state": state_meta,
                    }
                )
            return {"plans": plans}
        except Exception as exc:  # pragma: no cover - fall through to trace scan
            logger.warning(
                json.dumps(
                    {
                        "event": "plan_state_store_query_failed",
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )

    # --- Fallback path: trace scan (pre-Phase N or store unavailable) ---
    if trace_store is None:
        return {"plans": []}

    approvals_by_trace_id: dict[str, dict[str, Any]] = {}
    for request in approval_store.list_pending():
        trace_id = str(request.metadata.get("trace_id") or "").strip()
        if trace_id:
            approvals_by_trace_id[trace_id] = request.model_dump(mode="json")

    plans_fb: list[dict[str, Any]] = []
    traces = trace_store.list_recent_traces(limit=max(limit * 5, limit))
    for record in traces:
        if record.workflow_name != "run_task_plan":
            continue
        approval = approvals_by_trace_id.get(record.trace_id)
        plan_meta = approval.get("metadata", {}).get("plan") if approval else None
        state_meta = approval.get("metadata", {}).get("plan_state") if approval else None
        pending_approval_id = (
            record.metadata.get("pending_approval_id")
            or (approval or {}).get("approval_id")
        )
        plans_fb.append(
            {
                "trace_id": record.trace_id,
                "plan_id": str(record.metadata.get("plan_id") or record.task_id or record.trace_id),
                "workflow_name": record.workflow_name,
                "task_id": record.task_id,
                "status": record.status,
                "started_at": record.started_at.isoformat(),
                "ended_at": record.ended_at.isoformat() if record.ended_at else None,
                "pending_approval_id": pending_approval_id,
                "policy_effect": record.metadata.get("policy_effect"),
                "plan": plan_meta,
                "state": state_meta,
            }
        )
        if len(plans_fb) >= limit:
            break
    return {"plans": plans_fb}


def list_recent_governance_decisions(
    limit: int = 10,
    *,
    trace_store: Any | None = None,
) -> Dict[str, Any]:
    """Return recent governance decisions inferred from canonical trace data."""
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    if trace_store is None:
        return {"governance": []}

    decisions: list[dict[str, Any]] = []
    traces = trace_store.list_recent_traces(limit=max(limit * 5, limit))
    for record in traces:
        explainability = [
            item.model_dump(mode="json") for item in trace_store.get_explainability(record.trace_id)
        ]
        effect = _derive_governance_effect(record.model_dump(mode="json"), explainability)
        if effect is None:
            continue
        first = explainability[0] if explainability else {}
        decisions.append(
            {
                "trace_id": record.trace_id,
                "workflow_name": record.workflow_name,
                "task_id": record.task_id,
                "status": record.status,
                "effect": effect,
                "selected_agent_id": first.get("selected_agent_id"),
                "matched_policy_ids": list(first.get("matched_policy_ids") or []),
                "winning_policy_rule": first.get("metadata", {}).get("winning_policy_rule"),
                "approval_required": bool(first.get("approval_required")),
                "started_at": record.started_at.isoformat(),
                "ended_at": record.ended_at.isoformat() if record.ended_at else None,
            }
        )
        if len(decisions) >= limit:
            break
    return {"governance": decisions}


def _coerce_availability(raw: object) -> AgentAvailability:
    """Coerce a raw string to AgentAvailability, defaulting to UNKNOWN."""
    if raw is None:
        return AgentAvailability.UNKNOWN
    try:
        return AgentAvailability(str(raw).lower())
    except ValueError:
        return AgentAvailability.UNKNOWN


def _coerce_trust_level(raw: object) -> AgentTrustLevel:
    """Coerce a raw string to AgentTrustLevel, defaulting to UNKNOWN."""
    if raw is None:
        return AgentTrustLevel.UNKNOWN
    try:
        return AgentTrustLevel(str(raw).lower())
    except ValueError:
        return AgentTrustLevel.UNKNOWN


def list_agent_catalog() -> Dict[str, Any]:
    """Project currently listed agents into a control-plane-friendly catalog.

    Each entry is enriched with a deterministic ``quality`` summary derived
    from the canonical descriptor + performance-history state.

    Each entry is also enriched with an ``execution_capabilities`` field derived
    from the static adapter capability table — no IO required.
    """
    from core.decision.agent_registry import AgentRegistry

    raw_agents = list_agents().get("agents", [])
    descriptors_by_id = {
        descriptor.agent_id: descriptor
        for descriptor in AgentRegistry().list_descriptors()
    }
    perf_history = _get_learning_state()["perf_history"]
    _adapter_registry = ExecutionAdapterRegistry()
    catalog: list[dict[str, Any]] = []
    for item in raw_agents:
        if not isinstance(item, dict):
            continue
        traits = item.get("traits") if isinstance(item.get("traits"), dict) else {}
        raw_availability = traits.get("availability") or item.get("status")
        raw_trust = traits.get("trust_level")
        agent_id = (
            item.get("id") or item.get("agent_id") or item.get("name") or "unknown-agent"
        )
        raw_source_type = item.get("source_type") or ""
        raw_execution_kind = item.get("execution_kind") or ""
        descriptor = descriptors_by_id.get(agent_id)

        # Compute quality — safe; never raises.
        try:
            quality = compute_agent_quality(
                agent_id=agent_id,
                availability=(
                    descriptor.availability
                    if descriptor is not None
                    else _coerce_availability(raw_availability)
                ),
                trust_level=(
                    descriptor.trust_level
                    if descriptor is not None
                    else _coerce_trust_level(raw_trust)
                ),
                history=(
                    perf_history.get_for_descriptor(descriptor)
                    if descriptor is not None
                    else perf_history.get(agent_id)
                ),
            ).model_dump(mode="json")
        except Exception:  # pragma: no cover — defensive
            quality = None

        # Look up static execution capabilities for this (execution_kind, source_type).
        exec_caps = _adapter_registry.get_capabilities_for(raw_execution_kind, raw_source_type)
        exec_caps_dict = exec_caps.model_dump(mode="json") if exec_caps is not None else None

        catalog.append(
            {
                "agent_id": agent_id,
                "display_name": (
                    item.get("name") or item.get("display_name") or item.get("id") or "unknown-agent"
                ),
                "capabilities": list(item.get("capabilities") or []),
                "source_type": item.get("source_type"),
                "execution_kind": item.get("execution_kind"),
                "availability": raw_availability,
                "trust_level": raw_trust,
                "quality": quality,
                "execution_capabilities": exec_caps_dict,
                "metadata": {
                    "domain": item.get("domain"),
                    "role": item.get("role"),
                    "version": item.get("version"),
                    "skills": list(item.get("skills") or []),
                    "estimated_cost_per_token": item.get("estimated_cost_per_token"),
                    "avg_response_time": item.get("avg_response_time"),
                    "load_factor": item.get("load_factor"),
                    "projection_source": "services.core.list_agents",
                    "descriptor_projection_complete": bool(
                        item.get("source_type") and item.get("execution_kind")
                    ),
                },
            }
        )
    return {"agents": catalog}


def _compute_health_summary(
    agents: list,
    approvals: list,
    plans: list,
    warnings: list[str],
    layers: list[dict],
) -> Dict[str, Any]:
    """Derive a health summary from the already-collected canonical signals.

    This function contains no IO.  It derives operator-relevant health signals
    from the lists already gathered by ``get_control_plane_overview``.

    Returns a dict with:
    - ``overall``: "healthy" | "attention" | "degraded"
    - ``degraded_agent_count``, ``offline_agent_count``
    - ``paused_plan_count``, ``failed_plan_count``
    - ``pending_approval_count``
    - ``has_warnings``
    - ``attention_items``: prioritised list for the health view
    """
    # Agent availability counts
    degraded_agents = [a for a in agents if str(a.get("availability") or "").lower() == "degraded"]
    offline_agents = [a for a in agents if str(a.get("availability") or "").lower() == "offline"]
    degraded_agent_count = len(degraded_agents)
    offline_agent_count = len(offline_agents)

    # Plan status breakdown
    paused_plans = [p for p in plans if str(p.get("status") or "").lower() == "paused"]
    failed_plans = [p for p in plans if str(p.get("status") or "").lower() in {"failed", "rejected"}]
    paused_plan_count = len(paused_plans)
    failed_plan_count = len(failed_plans)

    pending_approval_count = len(approvals)
    has_warnings = bool(warnings)

    # Layer health
    unavailable_layers = [l["name"] for l in layers if l.get("status") == "unavailable"]

    # Build attention items list (ordered by severity)
    attention_items: list[dict[str, str]] = []

    for layer_name in unavailable_layers:
        attention_items.append({
            "level": "warning",
            "label": f"{layer_name} layer unavailable",
            "detail": "Read from this layer failed during overview assembly.",
        })

    for agent in offline_agents[:3]:
        attention_items.append({
            "level": "warning",
            "label": f"Agent offline: {agent.get('display_name') or agent.get('agent_id', '?')}",
            "detail": f"Availability: offline — this agent will not be selected for routing.",
        })

    if pending_approval_count > 0:
        attention_items.append({
            "level": "warning",
            "label": f"{pending_approval_count} pending approval{'s' if pending_approval_count > 1 else ''}",
            "detail": "Plans are paused waiting for human approval.",
        })

    for plan in paused_plans[:3]:
        attention_items.append({
            "level": "info",
            "label": f"Plan paused: {plan.get('workflow_name') or plan.get('plan_id', '?')}",
            "detail": f"Plan {plan.get('plan_id', '?')} is paused — may be waiting for approval.",
        })

    for plan in failed_plans[:3]:
        attention_items.append({
            "level": "warning",
            "label": f"Plan failed: {plan.get('workflow_name') or plan.get('plan_id', '?')}",
            "detail": f"Plan {plan.get('plan_id', '?')} ended with status {plan.get('status', 'failed')!r}.",
        })

    for agent in degraded_agents[:3]:
        attention_items.append({
            "level": "info",
            "label": f"Agent degraded: {agent.get('display_name') or agent.get('agent_id', '?')}",
            "detail": "This agent is available but may have reduced capacity or reliability.",
        })

    if has_warnings:
        for warning in warnings[:3]:
            attention_items.append({"level": "info", "label": "System warning", "detail": warning})

    # Overall status
    if unavailable_layers or offline_agent_count > 0:
        overall = "degraded"
    elif pending_approval_count > 0 or paused_plan_count > 0 or failed_plan_count > 0 or degraded_agent_count > 0 or has_warnings:
        overall = "attention"
    else:
        overall = "healthy"

    return {
        "overall": overall,
        "degraded_agent_count": degraded_agent_count,
        "offline_agent_count": offline_agent_count,
        "paused_plan_count": paused_plan_count,
        "failed_plan_count": failed_plan_count,
        "pending_approval_count": pending_approval_count,
        "has_warnings": has_warnings,
        "attention_items": attention_items,
    }


def get_control_plane_overview(
    *,
    agent_limit: int = 5,
    approval_limit: int = 5,
    trace_limit: int = 5,
    plan_limit: int = 5,
    governance_limit: int = 5,
) -> Dict[str, Any]:
    """Return the canonical control-plane overview for API and CLI callers."""

    def _safe_read(label: str, func) -> tuple[Any, list[str]]:
        try:
            return func(), []
        except Exception as exc:  # pragma: no cover - defensive operator read path
            return None, [f"{label}_unavailable:{exc.__class__.__name__}"]

    warnings: list[str] = []
    agents_result, issues = _safe_read(
        "agents",
        lambda: list_agent_catalog()["agents"][: max(0, agent_limit)],
    )
    warnings.extend(issues)
    approvals_result, issues = _safe_read(
        "approvals",
        lambda: list_pending_approvals()["approvals"][: max(0, approval_limit)],
    )
    warnings.extend(issues)
    traces_result, issues = _safe_read(
        "traces",
        lambda: list_recent_traces(limit=max(1, trace_limit))["traces"][: max(0, trace_limit)],
    )
    warnings.extend(issues)
    plans_result, issues = _safe_read(
        "plans",
        lambda: list_recent_plans(limit=max(1, plan_limit))["plans"][: max(0, plan_limit)],
    )
    warnings.extend(issues)
    governance_result, issues = _safe_read(
        "governance",
        lambda: list_recent_governance_decisions(limit=max(1, governance_limit))["governance"][
            : max(0, governance_limit)
        ],
    )
    warnings.extend(issues)
    governance_state, issues = _safe_read("governance_state", get_governance_state)
    warnings.extend(issues)

    agents = list(agents_result or [])
    approvals = list(approvals_result or [])
    traces = list(traces_result or [])
    plans = list(plans_result or [])
    governance = list(governance_result or [])

    # S7: derive layer statuses from read success/failure flags
    # A layer is "unavailable" if its canonical read failed (captured in warnings).
    layer_status_map: dict[str, str] = {
        "Decision": "available",
        "Execution": "available",
        "Learning": "available",
        "Orchestration": "available",
        "Approval": "available" if agents_result is not None else "unavailable",
        "Governance": "available" if governance_state is not None else "unavailable",
        "Audit/Trace": "available" if traces_result is not None else "unavailable",
        "MCP v2": "available",
    }
    # Override Approval layer if approval read failed
    if approvals_result is None:
        layer_status_map["Approval"] = "unavailable"
    # Override Orchestration if plan read failed
    if plans_result is None:
        layer_status_map["Orchestration"] = "unavailable"

    layers = [{"name": name, "status": status} for name, status in layer_status_map.items()]

    # S7: compute health summary from canonical signals
    health = _compute_health_summary(agents, approvals, plans, warnings, layers)

    return {
        "system": {
            "name": "ABrain Control Plane",
            "layers": layers,
            "governance": governance_state or {},
            "warnings": warnings,
        },
        "summary": {
            "agent_count": len(agents),
            "pending_approvals": len(approvals),
            "recent_traces": len(traces),
            "recent_plans": len(plans),
            "recent_governance_events": len(governance),
        },
        "health": health,
        "agents": agents,
        "pending_approvals": approvals,
        "recent_traces": traces,
        "recent_plans": plans,
        "recent_governance": governance,
    }


def get_governance_state() -> Dict[str, Any]:
    """Return lightweight governance configuration metadata for inspection."""
    state = _get_governance_state()
    registry = state["registry"]
    return {
        "policy_path": getattr(registry, "path", None),
        "engine": state["engine"].__class__.__name__,
        "registry": registry.__class__.__name__,
    }


def _get_learning_state() -> dict[str, Any]:
    """Return process-local training state for online updates.

    Performance history is loaded from disk on first call so the routing engine
    starts with warm priors after a restart.  The training dataset is similarly
    rehydrated when a persisted file exists.  Neither is auto-saved on update —
    write frequency does not justify per-call I/O at this stage.
    """
    if not hasattr(_get_learning_state, "_state"):
        from core.decision import NeuralTrainer, OnlineUpdater, TrainingDataset
        from core.decision.performance_history import PerformanceHistoryStore

        perf_path = os.getenv("ABRAIN_PERF_HISTORY_PATH", "runtime/abrain_perf_history.json")
        perf_history: PerformanceHistoryStore
        if os.path.exists(perf_path):
            try:
                perf_history = PerformanceHistoryStore.load_json(perf_path)
            except Exception as exc:
                logger.warning(
                    json.dumps(
                        {
                            "event": "perf_history_load_failed",
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                            "path": perf_path,
                        },
                        sort_keys=True,
                    )
                )
                perf_history = PerformanceHistoryStore()
        else:
            perf_history = PerformanceHistoryStore()

        dataset_path = os.getenv("ABRAIN_TRAINING_DATASET_PATH", "runtime/abrain_training_dataset.json")
        dataset: TrainingDataset
        if os.path.exists(dataset_path):
            try:
                from core.decision.learning.persistence import load_dataset
                dataset = load_dataset(dataset_path)
            except Exception as exc:
                logger.warning(
                    json.dumps(
                        {
                            "event": "training_dataset_load_failed",
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                            "path": dataset_path,
                        },
                        sort_keys=True,
                    )
                )
                dataset = TrainingDataset()
        else:
            dataset = TrainingDataset()

        _get_learning_state._state = {
            "dataset": dataset,
            "online_updater": OnlineUpdater(dataset=dataset),
            "trainer": NeuralTrainer(),
            "perf_history": perf_history,
            "perf_history_path": perf_path,
            "dataset_path": dataset_path,
        }
    return _get_learning_state._state


def _get_approval_state() -> dict[str, Any]:
    """Return process-local approval state for pause/resume orchestration.

    The ApprovalStore is wired to a JSON file so pending approvals and their
    embedded plan state survive a process restart.  On first call the file is
    loaded if it exists; subsequent mutations auto-save via ApprovalStore's
    built-in ``_auto_save`` hook.
    """
    if not hasattr(_get_approval_state, "_state"):
        from core.approval import ApprovalPolicy, ApprovalStore
        from pathlib import Path

        approval_path = Path(os.getenv("ABRAIN_APPROVAL_STORE_PATH", "runtime/abrain_approvals.json"))
        store: ApprovalStore
        if approval_path.exists():
            try:
                store = ApprovalStore.load_json(approval_path)
                # Ensure the loaded store keeps auto-saving to the same path.
                store.path = approval_path
            except Exception as exc:
                logger.warning(
                    json.dumps(
                        {
                            "event": "approval_store_load_failed",
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                            "path": str(approval_path),
                        },
                        sort_keys=True,
                    )
                )
                store = ApprovalStore(path=approval_path)
        else:
            store = ApprovalStore(path=approval_path)

        _get_approval_state._state = {
            "store": store,
            "policy": ApprovalPolicy(),
        }
    return _get_approval_state._state


def _get_plan_state_store() -> dict[str, Any]:
    """Return the process-local PlanStateStore for durable plan run tracking."""
    if not hasattr(_get_plan_state_store, "_state"):
        from core.orchestration.state_store import PlanStateStore

        path = os.getenv("ABRAIN_PLAN_STATE_DB_PATH", "runtime/abrain_plan_state.sqlite3")
        store = None
        try:
            store = PlanStateStore(path)
        except Exception as exc:  # pragma: no cover - defensive containment
            logger.warning(
                json.dumps(
                    {
                        "event": "plan_state_store_init_failed",
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                        "path": path,
                    },
                    sort_keys=True,
                )
            )
        _get_plan_state_store._state = {"store": store, "path": path}
    return _get_plan_state_store._state


def _get_trace_state() -> dict[str, Any]:
    """Return process-local trace state for best-effort audit storage."""
    if not hasattr(_get_trace_state, "_state"):
        from core.audit import TraceStore

        path = os.getenv("ABRAIN_TRACE_DB_PATH", "runtime/abrain_traces.sqlite3")
        store = None
        try:
            store = TraceStore(path)
        except Exception as exc:  # pragma: no cover - defensive containment
            logger.warning(
                json.dumps(
                    {
                        "event": "trace_store_init_failed",
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                        "path": path,
                    },
                    sort_keys=True,
                )
            )
        _get_trace_state._state = {
            "store": store,
            "path": path,
        }
    return _get_trace_state._state


def _decide_plan_step(
    approval_id: str,
    *,
    decision: str,
    decided_by: str,
    comment: str | None,
    rating: float | None = None,
    registry: Any | None,
    routing_engine: Any | None,
    execution_engine: Any | None,
    feedback_loop: Any | None,
    creation_engine: Any | None,
    orchestrator: Any | None,
    approval_store: Any | None,
    approval_policy: Any | None,
    policy_engine: Any | None,
    trace_store: Any | None,
    metadata: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Apply an approval decision and resume or reject the paused plan."""
    from core.approval import ApprovalDecision, ApprovalStatus
    from core.audit import attach_trace_context
    from core.decision import (
        AgentCreationEngine,
        AgentRegistry,
        FeedbackLoop,
        RoutingEngine,
    )
    from core.execution.execution_engine import ExecutionEngine
    from core.governance import PolicyEngine
    from core.orchestration import PlanExecutionOrchestrator, resume_plan

    approval_state = _get_approval_state()
    approval_store = approval_store or approval_state["store"]
    approval_policy = approval_policy or approval_state["policy"]
    governance_state = _get_governance_state()
    policy_engine = policy_engine or governance_state["engine"]
    trace_state = _get_trace_state()
    trace_store = trace_store if trace_store is not None else trace_state["store"]
    registry = registry or AgentRegistry()
    routing_engine = routing_engine or RoutingEngine()
    execution_engine = execution_engine or ExecutionEngine()
    learning_state = _get_learning_state()
    feedback_loop = feedback_loop or FeedbackLoop(
        performance_history=routing_engine.performance_history,
        online_updater=learning_state["online_updater"],
        trainer=learning_state["trainer"],
        neural_policy=routing_engine.neural_policy,
    )
    creation_engine = creation_engine or AgentCreationEngine()
    orchestrator = orchestrator or PlanExecutionOrchestrator()

    updated_request = approval_store.record_decision(
        approval_id,
        ApprovalDecision(
            approval_id=approval_id,
            decision=ApprovalStatus(decision),
            decided_by=decided_by,
            comment=comment,
            rating=rating,
            metadata=dict(metadata or {}),
        ),
    )
    trace_context = attach_trace_context(
        trace_store,
        trace_id=str(updated_request.metadata.get("trace_id") or "") or None,
        workflow_name=f"{decision}_plan_step",
    )
    result = resume_plan(
        updated_request,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=execution_engine,
        feedback_loop=feedback_loop,
        creation_engine=creation_engine,
        approval_policy=approval_policy,
        approval_store=approval_store,
        policy_engine=policy_engine,
        orchestrator=orchestrator,
        trace_context=trace_context,
    )
    # Update the plan state store so the post-decision result is durable.
    plan_state = _get_plan_state_store()
    if plan_state["store"] is not None:
        try:
            plan_state["store"].save_result(
                result,
                trace_id=str(updated_request.metadata.get("trace_id") or "") or None,
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            logger.warning(
                json.dumps(
                    {
                        "event": "plan_state_save_failed",
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                        "plan_id": result.plan_id,
                    },
                    sort_keys=True,
                )
            )
    return {
        "approval": updated_request.model_dump(mode="json"),
        "plan": updated_request.metadata.get("plan"),
        "result": result.model_dump(mode="json"),
        "trace": trace_context.summary(),
    }


def _get_governance_state() -> dict[str, Any]:
    """Return process-local runtime governance state."""
    if not hasattr(_get_governance_state, "_state"):
        from core.governance import PolicyEngine, PolicyRegistry

        policy_path = os.getenv("ABRAIN_POLICY_PATH")
        registry = PolicyRegistry(path=policy_path) if policy_path else PolicyRegistry()
        _get_governance_state._state = {
            "registry": registry,
            "engine": PolicyEngine(policy_registry=registry),
        }
    return _get_governance_state._state


def _build_single_step_approval_result(
    task: Any,
    *,
    planner_result: Any,
    decision: Any,
    selected_descriptor: Any,
    policy_decision: Any,
    approval_store: Any,
    trace_context: Any | None = None,
) -> Dict[str, Any]:
    """Create a serializable paused approval artifact for single-step tasks."""
    from core.approval import ApprovalRequest
    from core.decision import ExecutionPlan, PlanStep, PlanStrategy
    from core.orchestration import OrchestrationStatus, PlanExecutionState, ResultAggregator

    task_mapping = _as_mapping(task)
    plan = ExecutionPlan(
        task_id=str(task_mapping.get("task_id") or f"plan-{decision.task_type}"),
        original_task=task_mapping,
        strategy=PlanStrategy.SINGLE,
        steps=[
            PlanStep(
                step_id="execute",
                title=f"Execute {decision.task_type}",
                description=planner_result.intent.description or decision.task_type,
                required_capabilities=list(decision.required_capabilities),
                risk=planner_result.intent.risk,
                metadata={
                    "task_type": planner_result.intent.task_type,
                    "domain": planner_result.intent.domain,
                    "requires_human_approval": True,
                    "governance_origin": True,
                },
            )
        ],
        metadata={"intent_domain": planner_result.intent.domain},
    )
    approval_request = ApprovalRequest(
        plan_id=plan.task_id,
        step_id="execute",
        task_summary=planner_result.intent.description or decision.task_type,
        agent_id=decision.selected_agent_id,
        source_type=selected_descriptor.source_type if selected_descriptor else None,
        execution_kind=selected_descriptor.execution_kind if selected_descriptor else None,
        reason=policy_decision.reason,
        risk=planner_result.intent.risk,
        preview={
            "task_type": decision.task_type,
            "required_capabilities": list(decision.required_capabilities),
        },
        proposed_action_summary=(
            f"Single-step execution via "
            f"{selected_descriptor.display_name if selected_descriptor else 'unselected-agent'}"
        ),
        metadata={
            "approval_origin": "governance",
            "policy_decision": policy_decision.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "trace_id": getattr(trace_context, "trace_id", None),
        },
    )
    state = PlanExecutionState(
        status=OrchestrationStatus.PAUSED,
        next_step_index=0,
        next_step_id="execute",
        pending_approval_id=approval_request.approval_id,
        step_results=[],
        metadata={
            "approval_request": approval_request.model_dump(mode="json"),
            "approval_context": {
                "routing_decision": decision.model_dump(mode="json"),
                "policy_decision": policy_decision.model_dump(mode="json"),
                "selected_agent": selected_descriptor.model_dump(mode="json") if selected_descriptor else None,
                "trace_id": getattr(trace_context, "trace_id", None),
            },
        },
    )
    approval_request.metadata["plan_state"] = state.model_dump(mode="json")
    if approval_store.get_request(approval_request.approval_id) is None:
        approval_store.create_request(approval_request)
    result = ResultAggregator().aggregate(
        plan.task_id,
        [],
        status=OrchestrationStatus.PAUSED,
        state=state,
        metadata={
            "strategy": plan.strategy.value,
            "plan_metadata": plan.metadata,
            "pending_approval_id": approval_request.approval_id,
        },
    )
    return {
        "approval": approval_request.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }


def _as_mapping(task: Any) -> Dict[str, Any]:
    if isinstance(task, dict):
        return dict(task)
    if hasattr(task, "model_dump"):
        dumped = task.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _extract_task_flag(task: Any, name: str) -> Any:
    mapping = _as_mapping(task)
    if name in mapping:
        return mapping[name]
    preferences = mapping.get("preferences")
    if isinstance(preferences, dict) and name in preferences:
        return preferences[name]
    execution_hints = preferences.get("execution_hints") if isinstance(preferences, dict) else None
    if isinstance(execution_hints, dict) and name in execution_hints:
        return execution_hints[name]
    return None


def _resolve_trace_task_id(task_mapping: Dict[str, Any], *, default_prefix: str) -> str:
    task_id = str(task_mapping.get("task_id") or "").strip()
    if task_id:
        return task_id
    task_type = str(task_mapping.get("task_type") or "analysis").strip() or "analysis"
    return f"{default_prefix}-{task_type}"


def _build_routing_reason_summary(decision: Any) -> str:
    selected = decision.selected_agent_id or "unselected-agent"
    score = (
        f"{decision.selected_score:.3f}" if isinstance(decision.selected_score, (int, float)) else "n/a"
    )
    rejected_count = len(decision.diagnostics.get("rejected_agents") or [])
    candidate_count = len(decision.ranked_candidates or [])
    return (
        f"selected {selected} with score {score}; "
        f"{candidate_count} ranked candidates; {rejected_count} rejected by CandidateFilter"
    )


def _derive_governance_effect(
    trace_record: Dict[str, Any],
    explainability: list[dict[str, Any]],
) -> str | None:
    metadata = trace_record.get("metadata") if isinstance(trace_record.get("metadata"), dict) else {}
    explicit_effect = metadata.get("policy_effect")
    if isinstance(explicit_effect, str) and explicit_effect.strip():
        return explicit_effect.strip()
    if any(bool(item.get("approval_required")) for item in explainability):
        return "require_approval"
    if trace_record.get("status") == "denied":
        return "deny"
    if explainability:
        return "allow"
    return None


def _store_trace_explainability(
    trace_context: Any,
    *,
    step_id: str,
    decision: Any,
    policy_decision: Any,
    approval_required: bool,
    approval_id: str | None,
    created_agent: Any | None,
) -> None:
    from core.audit import ExplainabilityRecord

    if trace_context is None or not getattr(trace_context, "trace_id", None):
        return
    # Build scored_candidates list for first-class forensics access
    scored_candidates = [
        {
            "agent_id": candidate.agent_id,
            "score": candidate.score,
            "capability_match_score": candidate.capability_match_score,
        }
        for candidate in (decision.ranked_candidates or [])
    ]
    selected_candidate = decision.diagnostics.get("selected_candidate") or {}
    trace_context.store_explainability(
        ExplainabilityRecord(
            trace_id=trace_context.trace_id,
            step_id=step_id,
            selected_agent_id=decision.selected_agent_id,
            candidate_agent_ids=[candidate.agent_id for candidate in decision.ranked_candidates],
            selected_score=decision.selected_score,
            routing_reason_summary=_build_routing_reason_summary(decision),
            matched_policy_ids=list(policy_decision.matched_rules),
            approval_required=approval_required,
            approval_id=approval_id,
            # S10 — first-class forensics signals
            routing_confidence=decision.routing_confidence,
            score_gap=decision.score_gap,
            confidence_band=decision.confidence_band,
            policy_effect=policy_decision.effect if policy_decision is not None else None,
            scored_candidates=scored_candidates,
            metadata={
                "task_type": decision.task_type,
                "required_capabilities": list(decision.required_capabilities),
                "rejected_agents": decision.diagnostics.get("rejected_agents") or [],
                "candidate_filter": decision.diagnostics.get("candidate_filter") or {},
                "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
                "winning_policy_rule": policy_decision.winning_rule_id,
                "routing_model_source": decision.diagnostics.get("neural_policy_source"),
                "selected_candidate_model_source": selected_candidate.get("model_source"),
                "selected_candidate_feature_summary": (
                    selected_candidate.get("feature_summary") or {}
                ),
            },
        )
    )


def evaluate_trace(trace_id: str) -> Dict[str, Any] | None:
    """Dry-run replay and compliance check for a single stored trace.

    Runs a read-only evaluation of the stored trace against the current routing
    and governance engines.  No execution is triggered and no data is written.

    Returns ``None`` when the trace_id is not found in the store.
    Returns a serializable ``TraceEvaluationResult.model_dump()`` dict otherwise.
    """
    from core.decision import AgentRegistry, RoutingEngine
    from core.evaluation import TraceEvaluator
    from core.governance import PolicyEngine

    trace_state = _get_trace_state()
    trace_store = trace_state["store"]
    governance_state = _get_governance_state()
    policy_engine = governance_state["engine"]

    routing_engine = RoutingEngine()
    registry = AgentRegistry()
    descriptors = registry.list_descriptors()

    evaluator = TraceEvaluator(
        trace_store,
        routing_engine,
        policy_engine,
        agent_descriptors=descriptors,
    )
    result = evaluator.evaluate_trace(trace_id)
    if result is None:
        return None
    return result.model_dump(mode="json")


def compute_evaluation_baselines(*, limit: int = 100) -> Dict[str, Any]:
    """Compute baseline evaluation metrics across recent stored traces.

    Reads up to *limit* recent traces from the canonical TraceStore, runs
    dry-run routing and policy comparisons for each, and returns a
    ``BatchEvaluationReport.model_dump()`` dict with aggregated metrics.

    No execution is triggered and no data is written.
    """
    from core.decision import AgentRegistry, RoutingEngine
    from core.evaluation import TraceEvaluator
    from core.governance import PolicyEngine

    trace_state = _get_trace_state()
    trace_store = trace_state["store"]
    governance_state = _get_governance_state()
    policy_engine = governance_state["engine"]

    routing_engine = RoutingEngine()
    registry = AgentRegistry()
    descriptors = registry.list_descriptors()

    evaluator = TraceEvaluator(
        trace_store,
        routing_engine,
        policy_engine,
        agent_descriptors=descriptors,
    )
    report = evaluator.compute_baselines(limit=limit)
    return report.model_dump(mode="json")


def get_brain_operations_snapshot(
    *,
    trace_limit: int = 1000,
    workflow_filter: str | None = None,
    version_filter: str | None = None,
    max_feed_entries: int | None = None,
) -> Dict[str, Any]:
    """Return a Brain v1 baseline + suggestion-feed snapshot.

    Thin read-only wrapper over ``BrainOperationsReporter`` that exposes the
    composite Phase 6 operator lagebericht (baseline verdict + gated
    suggestion feed) to the canonical CLI / control-plane surfaces. Reads
    ``brain_shadow_eval`` spans from the canonical ``TraceStore``; writes
    nothing.
    """
    from core.decision.brain import BrainOperationsReporter

    trace_state = _get_trace_state()
    trace_store = trace_state["store"]
    if trace_store is None:
        return {
            "error": "trace_store_unavailable",
            "trace_store_path": trace_state["path"],
        }

    reporter = BrainOperationsReporter(trace_store=trace_store)
    report = reporter.generate(
        trace_limit=trace_limit,
        workflow_filter=workflow_filter,
        version_filter=version_filter,
        max_feed_entries=max_feed_entries,
    )
    return report.model_dump(mode="json")


def get_retention_scan(
    *,
    trace_retention_days: int = 90,
    approval_retention_days: int = 90,
    trace_limit: int = 10_000,
    keep_open_traces: bool = True,
    keep_pending_approvals: bool = True,
) -> Dict[str, Any]:
    """Return a read-only retention candidate report.

    Thin wrapper over ``RetentionScanner`` exposing the §6.4 governance
    surface to the canonical CLI / control-plane. Reads ``TraceStore`` and
    ``ApprovalStore`` only; no record is deleted (pruning lives in the
    separate ``RetentionPruner`` surface). Returns an error payload if the
    canonical TraceStore is not available.
    """
    from core.audit.retention import RetentionPolicy, RetentionScanner

    trace_state = _get_trace_state()
    trace_store = trace_state["store"]
    if trace_store is None:
        return {
            "error": "trace_store_unavailable",
            "trace_store_path": trace_state["path"],
        }

    approval_state = _get_approval_state()
    approval_store = approval_state["store"]

    policy = RetentionPolicy(
        trace_retention_days=trace_retention_days,
        approval_retention_days=approval_retention_days,
        keep_open_traces=keep_open_traces,
        keep_pending_approvals=keep_pending_approvals,
    )
    scanner = RetentionScanner(
        trace_store=trace_store,
        approval_store=approval_store,
        policy=policy,
    )
    report = scanner.scan(trace_limit=trace_limit)
    return report.model_dump(mode="json")


def get_retention_pii_annotation(
    *,
    trace_retention_days: int = 90,
    approval_retention_days: int = 90,
    trace_limit: int = 10_000,
    keep_open_traces: bool = True,
    keep_pending_approvals: bool = True,
    enabled_categories: list[str] | None = None,
) -> Dict[str, Any]:
    """Return PII findings annotated onto the retention candidate set.

    Composes ``RetentionScanner`` (governance windows) and ``PiiDetector``
    (string scanning) via :func:`core.audit.pii.annotate_retention_candidates`
    so operators see *which* records flagged for deletion also contain PII.
    Read-only across both stores; no record is mutated or deleted.
    """
    from core.audit.pii import (
        DEFAULT_PII_CATEGORIES,
        PiiDetector,
        PiiPolicy,
        annotate_retention_candidates,
    )
    from core.audit.retention import RetentionPolicy, RetentionScanner

    trace_state = _get_trace_state()
    trace_store = trace_state["store"]
    if trace_store is None:
        return {
            "error": "trace_store_unavailable",
            "trace_store_path": trace_state["path"],
        }

    approval_state = _get_approval_state()
    approval_store = approval_state["store"]

    retention_policy = RetentionPolicy(
        trace_retention_days=trace_retention_days,
        approval_retention_days=approval_retention_days,
        keep_open_traces=keep_open_traces,
        keep_pending_approvals=keep_pending_approvals,
    )
    scanner = RetentionScanner(
        trace_store=trace_store,
        approval_store=approval_store,
        policy=retention_policy,
    )
    report = scanner.scan(trace_limit=trace_limit)

    categories = (
        list(enabled_categories)
        if enabled_categories is not None
        else list(DEFAULT_PII_CATEGORIES)
    )
    pii_policy = PiiPolicy(enabled_categories=categories)
    detector = PiiDetector(policy=pii_policy)
    annotation = annotate_retention_candidates(
        detector=detector,
        report=report,
        trace_store=trace_store,
        approval_store=approval_store,
    )
    return {
        "retention_report": report.model_dump(mode="json"),
        "pii_annotation": annotation.model_dump(mode="json"),
        "policy": {
            "enabled_categories": categories,
        },
    }


def get_agent_performance_report(
    *,
    sort_key: str = "avg_cost",
    descending: bool = True,
    min_executions: int = 0,
    agent_ids: list[str] | None = None,
) -> Dict[str, Any]:
    """Return a cost/latency/success snapshot per agent path.

    Read-only consumer of the canonical ``PerformanceHistoryStore``
    (same instance used by the routing engine).  Composes the store
    with :class:`core.decision.performance_report.AgentPerformanceReporter`
    so operators get a one-call "what is each agent path currently
    costing us" view.  No second history, no re-derivation from traces.
    """
    from core.decision.performance_report import AgentPerformanceReporter

    state = _get_learning_state()
    store = state["perf_history"]
    reporter = AgentPerformanceReporter(store=store)
    report = reporter.generate(
        sort_key=sort_key,  # type: ignore[arg-type]
        descending=descending,
        min_executions=min_executions,
        agent_ids=agent_ids,
    )
    return report.model_dump(mode="json")
