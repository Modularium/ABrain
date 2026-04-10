from __future__ import annotations

"""Shared service helpers for CLI and API."""

import asyncio
import json
import logging
import os
from typing import Any, Dict

from core.execution.dispatcher import ExecutionDispatcher
from core.models import RequesterIdentity, RequesterType, ToolExecutionRequest
from core.model_context import ModelContext
from core.tools import build_default_registry

__all__ = [
    "approve_plan_step",
    "create_agent",
    "dispatch_task",
    "evaluate_agent",
    "execute_tool",
    "list_pending_approvals",
    "list_agents",
    "load_model",
    "reject_plan_step",
    "run_task",
    "run_task_plan",
    "train_model",
]

DEFAULT_REQUESTER = RequesterIdentity(
    type=RequesterType.AGENT,
    id="services.core",
)

logger = logging.getLogger(__name__)


def _build_dispatcher() -> ExecutionDispatcher:
    """Create the fixed execution dispatcher used by service helpers."""
    from sdk.client import AgentClient

    return ExecutionDispatcher(build_default_registry(client_factory=AgentClient))


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


def create_agent(
    config: Dict[str, Any], endpoint: str = "http://localhost:8090"
) -> Dict[str, Any]:
    """Register ``config`` with the MCP agent registry."""
    from agentnn.deployment.agent_registry import AgentRegistry

    registry = AgentRegistry(endpoint)
    return registry.deploy(config)


def dispatch_task(ctx: ModelContext) -> Dict[str, Any]:
    """Dispatch ``ctx`` through the fixed tool execution layer."""
    description = None
    if ctx.task_context is not None:
        description = getattr(ctx.task_context.description, "text", ctx.task_context.description)
    payload = {
        "task": description or getattr(ctx, "task", "") or "",
        "task_type": getattr(ctx.task_context, "task_type", None)
        if ctx.task_context
        else None,
        "session_id": getattr(ctx, "session_id", None),
        "task_value": getattr(ctx, "task_value", None),
        "max_tokens": getattr(ctx, "max_tokens", None),
        "priority": getattr(ctx, "priority", None),
        "deadline": getattr(ctx, "deadline", None),
    }
    return execute_tool("dispatch_task", payload)


def list_agents() -> Dict[str, Any]:
    """List agents through the fixed tool execution layer."""
    return execute_tool("list_agents", {})


def evaluate_agent(agent_id: str) -> Dict[str, Any]:
    """Return evaluation metrics for ``agent_id``."""
    from managers.agent_optimizer import AgentOptimizer

    optimizer = AgentOptimizer()
    return asyncio.run(optimizer.evaluate_agent(agent_id))


def load_model(
    name: str,
    type: str,
    source: str,
    config: Dict[str, Any],
    version: str | None = None,
) -> Dict[str, Any]:
    """Load a model using :class:`ModelManager`."""
    from managers.model_manager import ModelManager

    manager = ModelManager()
    return asyncio.run(manager.load_model(name, type, source, config, version))


def train_model(args: Any) -> Any:
    """Run the training routine with ``args``."""
    from training.train import train

    return train(args)


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
    from core.execution.execution_engine import ExecutionEngine
    from core.governance import PolicyEngine, PolicyViolationError, enforce_policy

    registry = registry or AgentRegistry()
    routing_engine = routing_engine or RoutingEngine()
    execution_engine = execution_engine or ExecutionEngine()
    approval_state = _get_approval_state()
    approval_store = approval_store or approval_state["store"]
    governance_state = _get_governance_state()
    policy_engine = policy_engine or governance_state["engine"]
    learning_state = _get_learning_state()
    feedback_loop = feedback_loop or FeedbackLoop(
        performance_history=routing_engine.performance_history,
        online_updater=learning_state["online_updater"],
        trainer=learning_state["trainer"],
        neural_policy=routing_engine.neural_policy,
    )
    creation_engine = creation_engine or AgentCreationEngine()

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

    selected_descriptor = registry.get(decision.selected_agent_id) if decision.selected_agent_id else None
    policy_decision = policy_engine.evaluate(
        planner_result.intent,
        selected_descriptor,
        policy_engine.build_execution_context(
            planner_result.intent,
            selected_descriptor,
            task=_as_mapping(task),
            task_id=_as_mapping(task).get("task_id"),
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
        return {
            "status": "denied",
            "decision": decision.model_dump(mode="json"),
            "execution": denied_execution.model_dump(mode="json"),
            "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
            "feedback": None,
            "warnings": ["policy_denied"],
            "governance": policy_decision.model_dump(mode="json"),
            "approval": None,
        }
    if governance_result == "approval_required":
        approval_payload = _build_single_step_approval_result(
            task,
            planner_result=planner_result,
            decision=decision,
            selected_descriptor=selected_descriptor,
            policy_decision=policy_decision,
            approval_store=approval_store,
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
        }

    execution = execution_engine.execute(task, decision, registry)
    feedback = None
    warnings: list[str] = []
    if execution.agent_id:
        selected_descriptor = registry.get(execution.agent_id)
        try:
            feedback = feedback_loop.update_performance(
                execution.agent_id,
                execution,
                task=task,
                agent_descriptor=selected_descriptor,
            )
            warnings.extend(feedback.warnings)
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

    return {
        "decision": decision.model_dump(mode="json"),
        "execution": execution.model_dump(mode="json"),
        "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
        "feedback": feedback.model_dump(mode="json") if feedback else None,
        "warnings": warnings,
        "governance": policy_decision.model_dump(mode="json"),
        "approval": None,
        "status": "completed",
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

    plan = plan_builder.build(task)
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
    )
    return {
        "plan": plan.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }


def approve_plan_step(
    approval_id: str,
    *,
    decided_by: str = "human",
    comment: str | None = None,
    registry: Any | None = None,
    routing_engine: Any | None = None,
    execution_engine: Any | None = None,
    feedback_loop: Any | None = None,
    creation_engine: Any | None = None,
    orchestrator: Any | None = None,
    approval_store: Any | None = None,
    approval_policy: Any | None = None,
    policy_engine: Any | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Approve a paused plan step and resume execution."""
    return _decide_plan_step(
        approval_id,
        decision="approved",
        decided_by=decided_by,
        comment=comment,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=execution_engine,
        feedback_loop=feedback_loop,
        creation_engine=creation_engine,
        orchestrator=orchestrator,
        approval_store=approval_store,
        approval_policy=approval_policy,
        policy_engine=policy_engine,
        metadata=metadata,
    )


def reject_plan_step(
    approval_id: str,
    *,
    decided_by: str = "human",
    comment: str | None = None,
    registry: Any | None = None,
    routing_engine: Any | None = None,
    execution_engine: Any | None = None,
    feedback_loop: Any | None = None,
    creation_engine: Any | None = None,
    orchestrator: Any | None = None,
    approval_store: Any | None = None,
    approval_policy: Any | None = None,
    policy_engine: Any | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Reject a paused plan step and return the terminal plan result."""
    return _decide_plan_step(
        approval_id,
        decision="rejected",
        decided_by=decided_by,
        comment=comment,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=execution_engine,
        feedback_loop=feedback_loop,
        creation_engine=creation_engine,
        orchestrator=orchestrator,
        approval_store=approval_store,
        approval_policy=approval_policy,
        policy_engine=policy_engine,
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


def _get_learning_state() -> dict[str, Any]:
    """Return process-local training state for online updates."""
    if not hasattr(_get_learning_state, "_state"):
        from core.decision import NeuralTrainer, OnlineUpdater, TrainingDataset

        dataset = TrainingDataset()
        _get_learning_state._state = {
            "dataset": dataset,
            "online_updater": OnlineUpdater(dataset=dataset),
            "trainer": NeuralTrainer(),
        }
    return _get_learning_state._state


def _get_approval_state() -> dict[str, Any]:
    """Return process-local approval state for pause/resume orchestration."""
    if not hasattr(_get_approval_state, "_state"):
        from core.approval import ApprovalPolicy, ApprovalStore

        _get_approval_state._state = {
            "store": ApprovalStore(),
            "policy": ApprovalPolicy(),
        }
    return _get_approval_state._state


def _decide_plan_step(
    approval_id: str,
    *,
    decision: str,
    decided_by: str,
    comment: str | None,
    registry: Any | None,
    routing_engine: Any | None,
    execution_engine: Any | None,
    feedback_loop: Any | None,
    creation_engine: Any | None,
    orchestrator: Any | None,
    approval_store: Any | None,
    approval_policy: Any | None,
    policy_engine: Any | None,
    metadata: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Apply an approval decision and resume or reject the paused plan."""
    from core.approval import ApprovalDecision, ApprovalStatus
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
            metadata=dict(metadata or {}),
        ),
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
    )
    return {
        "approval": updated_request.model_dump(mode="json"),
        "plan": updated_request.metadata.get("plan"),
        "result": result.model_dump(mode="json"),
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
