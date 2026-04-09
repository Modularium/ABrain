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
from core.model_context import TaskContext

try:  # pragma: no cover - optional metrics dependency
    from core.metrics_utils import ROUTING_DECISIONS
except Exception:  # pragma: no cover - optional metrics dependency
    ROUTING_DECISIONS = None

try:  # pragma: no cover - optional registry-service dependency
    from services.agent_registry.schemas import AgentInfo
    from services.agent_registry.service import AgentRegistryService
except Exception:  # pragma: no cover - optional registry-service dependency
    AgentInfo = None
    AgentRegistryService = None


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
        self.registry_service = (
            registry_service
            if registry_service is not None
            else AgentRegistryService()
            if AgentRegistryService is not None
            else None
        )
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
        if ROUTING_DECISIONS is not None:
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
        descriptors = (
            self.registry_service.list_descriptors()
            if self.registry_service is not None
            else []
        )
        if descriptors:
            return descriptors
        return [self._bootstrap_worker_dev_descriptor()]

    def _coerce_descriptor(self, item: Any) -> AgentDescriptor:
        if isinstance(item, AgentDescriptor):
            return item
        if isinstance(item, Mapping) and {"agent_id", "display_name"} <= set(item):
            return AgentDescriptor.model_validate(item)
        if isinstance(item, Mapping):
            traits = item.get("traits") if isinstance(item.get("traits"), Mapping) else {}
            capabilities = item.get("capabilities")
            return AgentDescriptor(
                agent_id=str(item.get("id") or item.get("agent_id") or "unknown-agent"),
                display_name=str(item.get("name") or item.get("display_name") or "unknown-agent"),
                source_type=AgentSourceType.NATIVE,
                execution_kind=AgentExecutionKind.HTTP_SERVICE,
                capabilities=list(capabilities) if isinstance(capabilities, list) else [],
                trust_level=self._coerce_trust_level(traits.get("trust_level")),
                cost_profile=self._coerce_cost_profile(item.get("estimated_cost_per_token")),
                latency_profile=self._coerce_latency_profile(item.get("avg_response_time")),
                availability=self._coerce_availability(traits.get("availability")),
                metadata={
                    "url": item.get("url"),
                    "estimated_cost_per_token": item.get("estimated_cost_per_token"),
                    "avg_response_time": item.get("avg_response_time"),
                    "legacy_agent_info": True,
                },
            )
        if isinstance(item, Mapping) and AgentInfo is not None:
            return AgentInfo.model_validate(item).to_descriptor()
        raise TypeError(f"Unsupported agent descriptor input: {type(item)!r}")

    def _coerce_trust_level(self, value: Any) -> AgentTrustLevel:
        try:
            return AgentTrustLevel(str(value))
        except ValueError:
            return AgentTrustLevel.UNKNOWN

    def _coerce_availability(self, value: Any) -> AgentAvailability:
        try:
            return AgentAvailability(str(value))
        except ValueError:
            return AgentAvailability.ONLINE

    def _coerce_cost_profile(self, value: Any) -> AgentCostProfile:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return AgentCostProfile.MEDIUM
        if numeric <= 0.002:
            return AgentCostProfile.LOW
        if numeric <= 0.01:
            return AgentCostProfile.MEDIUM
        return AgentCostProfile.HIGH

    def _coerce_latency_profile(self, value: Any) -> AgentLatencyProfile:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return AgentLatencyProfile.INTERACTIVE
        if numeric <= 2.0:
            return AgentLatencyProfile.INTERACTIVE
        if numeric <= 10.0:
            return AgentLatencyProfile.BACKGROUND
        return AgentLatencyProfile.BATCH

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
