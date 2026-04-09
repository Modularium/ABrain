import pytest

from core.decision import AgentCreationEngine, AgentExecutionKind, AgentSourceType
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def test_agent_creation_prefers_n8n_for_backend_automation_tasks():
    engine = AgentCreationEngine()

    descriptor = engine.create_agent_from_task(
        TaskContext(
            task_type="workflow_automation",
            description="Automate this backend workflow",
            preferences={"execution_hints": {"integration_heavy": True}},
        ),
        ["workflow.execute", "workflow.automation", "data.transform"],
    )

    assert descriptor.source_type == AgentSourceType.N8N
    assert descriptor.execution_kind == AgentExecutionKind.WORKFLOW_ENGINE


def test_agent_creation_prefers_flowise_for_visual_editable_tasks():
    engine = AgentCreationEngine()

    descriptor = engine.create_agent_from_task(
        TaskContext(
            task_type="visual_agent_editable",
            description="Create a visual agent flow that users can edit",
            preferences={"execution_hints": {"editable_in_ui": True}},
        ),
        ["flow.visual_agent", "flow.tool_orchestration"],
    )

    assert descriptor.source_type == AgentSourceType.FLOWISE
    assert descriptor.execution_kind == AgentExecutionKind.WORKFLOW_ENGINE
