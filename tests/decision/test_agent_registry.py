import json

import pytest

from core.decision.agent_descriptor import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)
from core.decision.agent_registry import AgentRegistry


def _descriptor(agent_id: str) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id.title(),
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
    )


@pytest.mark.unit
def test_agent_registry_registers_and_loads_json(tmp_path):
    registry = AgentRegistry()
    registry.register(_descriptor("alpha"))
    registry.register(_descriptor("beta"))

    path = tmp_path / "descriptors.json"
    registry.save_json(path)

    reloaded = AgentRegistry.load_json(path)
    assert [item.agent_id for item in reloaded.list_descriptors()] == ["alpha", "beta"]
    assert json.loads(path.read_text())["descriptors"][0]["agent_id"] == "alpha"


@pytest.mark.unit
def test_agent_registry_rejects_duplicates():
    registry = AgentRegistry()
    registry.register(_descriptor("alpha"))

    with pytest.raises(ValueError):
        registry.register(_descriptor("alpha"))
