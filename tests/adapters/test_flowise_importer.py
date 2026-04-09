import pytest

from adapters.flowise.importer import import_flowise_agent
from core.decision import AgentExecutionKind, AgentSourceType

pytestmark = pytest.mark.unit


def test_flowise_importer_maps_known_fields_and_preserves_unknown_fields():
    descriptor = import_flowise_agent(
        {
            "id": "flowise-agent-1",
            "name": "Flowise Agent",
            "description": "Visual workflow",
            "tools": [
                {"id": "search_docs", "name": "Search Docs", "description": "Lookup docs"},
                "summarize",
            ],
            "metadata": {
                "capabilities": ["analysis.general", "registry.read"],
                "owner": "ui-team",
            },
            "ui_color": "#ffaa00",
        }
    )

    assert descriptor.agent_id == "flowise-agent-1"
    assert descriptor.display_name == "Flowise Agent"
    assert descriptor.source_type == AgentSourceType.FLOWISE
    assert descriptor.execution_kind == AgentExecutionKind.WORKFLOW_ENGINE
    assert descriptor.editable_in_flowise is True
    assert descriptor.capabilities == ["analysis.general", "registry.read"]
    assert descriptor.metadata["flowise_description"] == "Visual workflow"
    assert descriptor.metadata["flowise_extra"] == {"ui_color": "#ffaa00"}
    assert descriptor.metadata["flowise_tools"][0]["id"] == "search_docs"


def test_flowise_importer_rejects_non_mapping_input():
    with pytest.raises(TypeError):
        import_flowise_agent(["not", "a", "mapping"])
