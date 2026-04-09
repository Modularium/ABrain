import pytest

from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
    RoutingEngine,
)
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def build_descriptor(
    agent_id: str,
    *,
    capabilities: list[str],
    trust_level: AgentTrustLevel = AgentTrustLevel.SANDBOXED,
    availability: AgentAvailability = AgentAvailability.ONLINE,
    success_rate: float = 0.7,
    cost: float = 0.001,
    latency: float = 1.0,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=capabilities,
        trust_level=trust_level,
        availability=availability,
        metadata={
            "success_rate": success_rate,
            "estimated_cost_per_token": cost,
            "avg_response_time": latency,
        },
    )


def test_routing_engine_selects_top_candidate_from_safe_set():
    engine = RoutingEngine()
    task = TaskContext(task_type="code_refactor", description="Refactor a service")
    descriptors = [
        build_descriptor(
            "best-agent",
            capabilities=["analysis.code", "code.refactor"],
            trust_level=AgentTrustLevel.TRUSTED,
            success_rate=0.95,
            cost=0.001,
            latency=1.0,
        ),
        build_descriptor(
            "safe-but-weaker",
            capabilities=["analysis.code", "code.refactor"],
            trust_level=AgentTrustLevel.TRUSTED,
            success_rate=0.75,
            cost=0.008,
            latency=5.0,
        ),
        build_descriptor(
            "unsafe-agent",
            capabilities=["analysis.code"],
            trust_level=AgentTrustLevel.PRIVILEGED,
            success_rate=0.99,
            cost=0.0001,
            latency=0.5,
        ),
    ]

    decision = engine.route(task, descriptors)

    assert decision.selected_agent_id == "best-agent"
    assert [item.agent_id for item in decision.ranked_candidates] == [
        "best-agent",
        "safe-but-weaker",
    ]
    rejected_ids = {item["agent_id"] for item in decision.diagnostics["rejected_agents"]}
    assert "unsafe-agent" in rejected_ids


def test_routing_engine_never_selects_agent_outside_filtered_candidates():
    engine = RoutingEngine()
    task = {
        "task_type": "system_health",
        "preferences": {"execution_hints": {"minimum_trust_level": "trusted"}},
    }
    descriptors = [
        build_descriptor(
            "sandboxed-health",
            capabilities=["system.read", "system.health"],
            trust_level=AgentTrustLevel.SANDBOXED,
            success_rate=0.99,
        ),
        build_descriptor(
            "trusted-health",
            capabilities=["system.read", "system.health"],
            trust_level=AgentTrustLevel.TRUSTED,
            success_rate=0.6,
        ),
    ]

    decision = engine.route(task, descriptors)

    assert decision.selected_agent_id == "trusted-health"
    assert all(item.agent_id != "sandboxed-health" for item in decision.ranked_candidates)
