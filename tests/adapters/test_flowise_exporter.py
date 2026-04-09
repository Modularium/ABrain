import pytest

from adapters.flowise.exporter import (
    export_descriptor_to_flowise,
    export_legacy_agent_config_to_flowise,
)
from core.decision.agent_descriptor import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)


@pytest.mark.unit
def test_flowise_exporter_exports_supported_descriptor():
    descriptor = AgentDescriptor(
        agent_id="ops-agent",
        display_name="Ops Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["ops.read_status"],
        editable_in_flowise=True,
        metadata={
            "description": "Reads system status",
            "tool_refs": ["adminbot_system_status"],
            "model_config": {"provider": "openai", "model": "gpt-4o-mini"},
            "version": "1.0.0",
        },
    )

    report = export_descriptor_to_flowise(descriptor)

    assert report.artifact.id == "ops-agent"
    assert report.artifact.name == "Ops Agent"
    assert report.artifact.tools == ["adminbot_system_status"]
    assert report.artifact.llm["model"] == "gpt-4o-mini"
    assert report.warnings == []


@pytest.mark.unit
def test_flowise_exporter_warns_when_optional_fields_are_missing():
    descriptor = AgentDescriptor(
        agent_id="ops-agent",
        display_name="Ops Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        editable_in_flowise=True,
    )

    report = export_descriptor_to_flowise(descriptor)

    assert report.artifact.tools == []
    assert report.artifact.llm == {}
    assert [warning.code for warning in report.warnings] == [
        "missing_tool_refs",
        "missing_llm_config",
    ]


@pytest.mark.unit
def test_flowise_exporter_rejects_non_exportable_descriptor():
    descriptor = AgentDescriptor(
        agent_id="adminbot",
        display_name="AdminBot",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        editable_in_flowise=False,
    )

    with pytest.raises(ValueError):
        export_descriptor_to_flowise(descriptor)


@pytest.mark.unit
def test_flowise_exporter_supports_legacy_agent_config_wrapper():
    payload = export_legacy_agent_config_to_flowise(
        {
            "name": "demo_agent",
            "domain": "demo",
            "capabilities": ["a"],
            "tools": ["t1"],
            "model_config": {"model": "gpt"},
            "created_at": "2024-01-01",
            "version": "1.0.0",
        }
    )

    assert payload["id"] == "demo_agent"
    assert payload["tools"] == ["t1"]
    assert payload["llm"]["model"] == "gpt"
