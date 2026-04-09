import pytest

from core.decision.agent_descriptor import (
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)


@pytest.mark.unit
def test_agent_descriptor_has_safe_defaults():
    descriptor = AgentDescriptor(
        agent_id="registry-agent",
        display_name="Registry Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
    )

    assert descriptor.capabilities == []
    assert descriptor.editable_in_flowise is False
    assert descriptor.cost_profile == AgentCostProfile.UNKNOWN
    assert descriptor.metadata == {}


@pytest.mark.unit
def test_agent_descriptor_rejects_extra_fields():
    with pytest.raises(ValueError):
        AgentDescriptor(
            agent_id="registry-agent",
            display_name="Registry Agent",
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            unexpected=True,
        )
