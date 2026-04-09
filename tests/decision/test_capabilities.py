import pytest

from core.decision.capabilities import Capability, CapabilityRisk


@pytest.mark.unit
def test_capability_normalizes_required_tools():
    capability = Capability(
        id="service.status.read",
        domain="operations",
        risk=CapabilityRisk.LOW,
        required_tools=[" list_agents ", "list_agents", "adminbot_system_status"],
    )

    assert capability.required_tools == ["list_agents", "adminbot_system_status"]


@pytest.mark.unit
def test_capability_rejects_blank_tool_ids():
    with pytest.raises(ValueError):
        Capability(
            id="service.status.read",
            domain="operations",
            required_tools=["   "],
        )
