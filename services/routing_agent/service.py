"""Thin routing-service wrapper around the canonical decision layer."""

from __future__ import annotations

from typing import Any, Mapping

from core.decision import (
    AgentAvailability,
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentLatencyProfile,
    AgentSourceType,
    AgentTrustLevel,
    RoutingEngine,
)
from core.metrics_utils import ROUTING_DECISIONS
from core.model_context import TaskContext
from services.agent_registry.schemas import AgentInfo
from services.agent_registry.service import AgentRegistryService


class RoutingAgentService:
    """Route tasks through the canonical planner/filter/neural pipeline."""

    def __init__(
        self,
        rules_path: str | None = None,
        *,
        registry_service: AgentRegistryService | None = None,
        routing_engine: RoutingEngine | None = None,
    ) -> None:
        self.rules_path = rules_path
        self.registry_service = registry_service or AgentRegistryService()
        self.routing_engine = routing_engine or RoutingEngine()

    def predict_agent(self, ctx: dict) -> str:
        """Return the selected agent id from the canonical routing decision."""
        decision = self._route_decision(ctx)
        return decision.selected_agent_id or "worker_dev"

    def route(
        self,
        task_type: str,
        required_tools: list[str] | None = None,
        context: dict | None = None,
    ) -> dict:
        ctx = {"task_type": task_type, "required_tools": required_tools}
        if context:
            ctx.update(context)
        decision = self._route_decision(ctx)
        worker = decision.selected_agent_id or "worker_dev"
        ROUTING_DECISIONS.labels(task_type, worker).inc()
        return {
            "target_worker": worker,
            "decision": decision.model_dump(mode="json"),
        }

    def _route_decision(self, ctx: Mapping[str, Any]):
        descriptors = self._load_descriptors(ctx)
        task_context = TaskContext(
            task_type=str(ctx.get("task_type") or "analysis"),
            description=str(ctx.get("description") or ctx.get("task") or ""),
            preferences=self._build_preferences(ctx),
        )
        return self.routing_engine.route(task_context, descriptors)

    def _load_descriptors(self, ctx: Mapping[str, Any]) -> list[AgentDescriptor]:
        raw_agents = ctx.get("agents")
        if isinstance(raw_agents, list) and raw_agents:
            return [self._coerce_descriptor(item) for item in raw_agents]
        descriptors = self.registry_service.list_descriptors()
        if descriptors:
            return descriptors
        return [self._bootstrap_worker_dev_descriptor()]

    def _coerce_descriptor(self, item: Any) -> AgentDescriptor:
        if isinstance(item, AgentDescriptor):
            return item
        if isinstance(item, Mapping) and {"agent_id", "display_name"} <= set(item):
            return AgentDescriptor.model_validate(item)
        if isinstance(item, Mapping):
            return AgentInfo.model_validate(item).to_descriptor()
        raise TypeError(f"Unsupported agent descriptor input: {type(item)!r}")

    def _build_preferences(self, ctx: Mapping[str, Any]) -> dict[str, Any]:
        preferences = dict(ctx.get("preferences") or {})
        required_capabilities = ctx.get("required_capabilities")
        if isinstance(required_capabilities, list):
            preferences["required_capabilities"] = required_capabilities
        required_tools = ctx.get("required_tools")
        if isinstance(required_tools, list) and required_tools and "required_capabilities" not in preferences:
            preferences["required_capabilities"] = ["analysis.general"]
        return preferences

    def _bootstrap_worker_dev_descriptor(self) -> AgentDescriptor:
        return AgentDescriptor(
            agent_id="worker_dev",
            display_name="worker_dev",
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=[
                "analysis.general",
                "analysis.code",
                "code.refactor",
                "review.code",
                "registry.read",
            ],
            trust_level=AgentTrustLevel.SANDBOXED,
            cost_profile=AgentCostProfile.LOW,
            latency_profile=AgentLatencyProfile.INTERACTIVE,
            availability=AgentAvailability.ONLINE,
            metadata={"bootstrap_descriptor": True},
        )
