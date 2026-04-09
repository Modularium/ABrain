import pytest

from adapters.flowise.importer import import_flowise_artifact


@pytest.mark.unit
def test_flowise_importer_accepts_supported_agent_artifact():
    report = import_flowise_artifact(
        {
            "id": "ops-agent",
            "name": "Ops Agent",
            "description": "Reads system status",
            "type": "agent",
            "tools": ["adminbot_system_status", "list_agents"],
            "capabilities": ["ops.read_status"],
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "version": "1.0.0",
            "created_at": "2026-04-09T10:00:00Z",
        }
    )

    assert report.descriptor.agent_id == "ops-agent"
    assert report.descriptor.source_type.value == "flowise"
    assert report.descriptor.execution_kind.value == "workflow_engine"
    assert report.descriptor.editable_in_flowise is True
    assert report.descriptor.capabilities == ["ops.read_status"]
    assert report.descriptor.metadata["tool_refs"] == ["adminbot_system_status", "list_agents"]
    assert report.descriptor.metadata["flowise_llm"]["model"] == "gpt-4o-mini"
    assert report.warnings == []


@pytest.mark.unit
def test_flowise_importer_keeps_unsupported_fields_in_metadata_with_warning():
    report = import_flowise_artifact(
        {
            "name": "Ops Agent",
            "type": "agent",
            "tools": ["adminbot_system_status"],
            "uiState": {"collapsed": True},
            "credentialId": "secret-1",
        }
    )

    assert report.descriptor.agent_id == "ops-agent"
    assert report.descriptor.metadata["flowise_extra_fields"]["credentialId"] == "secret-1"
    assert "uiState" in report.descriptor.metadata["flowise_extra_fields"]
    assert report.warnings[0].code == "ignored_fields"


@pytest.mark.unit
def test_flowise_importer_chatflow_is_partial_and_metadata_only():
    report = import_flowise_artifact(
        {
            "id": "chatflow-1",
            "name": "Support Chatflow",
            "type": "chatflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "chatOpenAI",
                    "label": "ChatOpenAI",
                    "data": {"modelName": "gpt-4o-mini", "provider": "openai"},
                },
                {
                    "id": "node-2",
                    "type": "ToolAgent",
                    "label": "Tool Agent",
                    "data": {"name": "Tool Agent"},
                },
            ],
            "edges": [{"id": "edge-1"}],
        }
    )

    assert report.descriptor.agent_id == "chatflow-1"
    assert report.descriptor.metadata["flowise_node_refs"] == ["ChatOpenAI", "Tool Agent"]
    assert report.descriptor.metadata["flowise_llm"]["provider"] == "openai"
    assert report.warnings[0].code == "partial_chatflow_support"
