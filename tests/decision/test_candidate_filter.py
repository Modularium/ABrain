import pytest

from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
    CandidateFilter,
    TaskIntent,
)

pytestmark = pytest.mark.unit


def build_descriptor(
    agent_id: str,
    *,
    capabilities: list[str],
    availability: AgentAvailability = AgentAvailability.ONLINE,
    trust_level: AgentTrustLevel = AgentTrustLevel.SANDBOXED,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=capabilities,
        availability=availability,
        trust_level=trust_level,
    )


def test_candidate_filter_excludes_missing_capabilities_and_offline_agents():
    intent = TaskIntent(
        task_type="system_health",
        domain="system",
        required_capabilities=["system.read", "system.health"],
    )
    descriptors = [
        build_descriptor("safe-agent", capabilities=["system.read", "system.health"]),
        build_descriptor("missing-capability", capabilities=["system.read"]),
        build_descriptor(
            "offline-agent",
            capabilities=["system.read", "system.health"],
            availability=AgentAvailability.OFFLINE,
        ),
    ]

    result = CandidateFilter().filter_candidates(intent, descriptors)

    assert [candidate.agent.agent_id for candidate in result.candidates] == ["safe-agent"]
    rejected = {item.agent_id: item.reasons for item in result.rejected}
    assert "missing_capabilities" in rejected["missing-capability"]
    assert "agent_offline" in rejected["offline-agent"]


def test_candidate_filter_enforces_minimum_trust_level():
    intent = TaskIntent(
        task_type="code_refactor",
        domain="code",
        required_capabilities=["analysis.code", "code.refactor"],
        execution_hints={"minimum_trust_level": "trusted"},
    )
    descriptors = [
        build_descriptor(
            "sandboxed-agent",
            capabilities=["analysis.code", "code.refactor"],
            trust_level=AgentTrustLevel.SANDBOXED,
        ),
        build_descriptor(
            "trusted-agent",
            capabilities=["analysis.code", "code.refactor"],
            trust_level=AgentTrustLevel.TRUSTED,
        ),
    ]

    result = CandidateFilter().filter_candidates(intent, descriptors)

    assert [candidate.agent.agent_id for candidate in result.candidates] == ["trusted-agent"]
