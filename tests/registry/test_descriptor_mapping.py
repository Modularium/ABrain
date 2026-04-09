import pytest

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from services.agent_registry.schemas import AgentInfo
from services.agent_registry.service import AgentRegistryService


@pytest.mark.unit
def test_agentinfo_roundtrip_to_descriptor():
    info = AgentInfo(
        id="ops-agent",
        name="Ops Agent",
        url="http://ops.local",
        domain="operations",
        version="1.0.0",
        capabilities=["ops.read_status"],
        traits={"availability": "online", "editable_in_flowise": True},
    )

    descriptor = info.to_descriptor()

    assert descriptor.agent_id == "ops-agent"
    assert descriptor.execution_kind.value == "http_service"
    assert descriptor.metadata["url"] == "http://ops.local"
    assert descriptor.editable_in_flowise is True

    roundtrip = AgentInfo.from_descriptor(descriptor)
    assert roundtrip.id == "ops-agent"
    assert roundtrip.url == "http://ops.local"


@pytest.mark.unit
def test_registry_service_can_register_descriptor():
    descriptor = AgentDescriptor(
        agent_id="ops-agent",
        display_name="Ops Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        editable_in_flowise=True,
        metadata={"url": "http://ops.local"},
    )

    service = AgentRegistryService()
    service.register_descriptor(descriptor)

    loaded = service.get_descriptor("ops-agent")
    assert loaded is not None
    assert loaded.agent_id == "ops-agent"
    assert service.list_descriptors()[0].agent_id == "ops-agent"
