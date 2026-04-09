from __future__ import annotations

"""Shared service helpers for CLI and API."""

import asyncio
from typing import Any, Dict

from core.execution.dispatcher import ExecutionDispatcher
from core.models import RequesterIdentity, RequesterType, ToolExecutionRequest
from core.model_context import ModelContext
from core.tools import build_default_registry

__all__ = [
    "create_agent",
    "dispatch_task",
    "evaluate_agent",
    "execute_tool",
    "list_agents",
    "load_model",
    "run_task",
    "train_model",
]

DEFAULT_REQUESTER = RequesterIdentity(
    type=RequesterType.AGENT,
    id="services.core",
)


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

    descriptors = registry.list_descriptors()
    decision = routing_engine.route(task, descriptors)
    created_agent = None
    if creation_engine.should_create_agent(decision.selected_score):
        created_agent = creation_engine.create_agent_from_task(
            task,
            decision.required_capabilities,
            registry=registry,
        )
        rerouted = routing_engine.route(task, registry.list_descriptors())
        if rerouted.selected_agent_id:
            decision = rerouted
        else:
            decision.selected_agent_id = created_agent.agent_id

    execution = execution_engine.execute(task, decision, registry)
    feedback = None
    if execution.agent_id:
        selected_descriptor = registry.get(execution.agent_id)
        feedback = feedback_loop.update_performance(
            execution.agent_id,
            execution,
            task=task,
            agent_descriptor=selected_descriptor,
        )

    return {
        "decision": decision.model_dump(mode="json"),
        "execution": execution.model_dump(mode="json"),
        "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
        "feedback": feedback.model_dump(mode="json") if feedback else None,
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
