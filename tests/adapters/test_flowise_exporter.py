import pytest

from adapters.flowise.exporter import export_to_flowise
from core.decision import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)

pytestmark = pytest.mark.unit


def test_flowise_exporter_projects_supported_descriptor():
    descriptor = AgentDescriptor(
        agent_id="flowise-ready-agent",
        display_name="Flowise Ready Agent",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis.code", "code.refactor"],
        editable_in_flowise=True,
        metadata={
            "flowise_description": "Editable in external UI",
            "flowise_tools": [
                {"id": "refactor_code", "name": "Refactor Code", "description": "Refactor a file"}
            ],
        },
    )

    exported = export_to_flowise(descriptor)

    assert exported.id == "flowise-ready-agent"
    assert exported.name == "Flowise Ready Agent"
    assert exported.description == "Editable in external UI"
    assert exported.tools[0].id == "refactor_code"
    assert exported.metadata is not None
    assert exported.metadata.values["execution_kind"] == "local_process"


def test_flowise_exporter_rejects_system_executor_descriptor():
    descriptor = AgentDescriptor(
        agent_id="adminbot-agent",
        display_name="AdminBot",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        capabilities=["system.read", "system.status"],
    )

    with pytest.raises(ValueError, match="system_executor"):
        export_to_flowise(descriptor)
