import pytest

from core.decision import AgentCreationEngine, AgentRegistry
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def test_agent_creation_creates_code_agent_and_registers_it():
    registry = AgentRegistry()
    engine = AgentCreationEngine(threshold=0.6)

    descriptor = engine.create_agent_from_task(
        TaskContext(task_type="code_refactor", description="Refactor"),
        ["analysis.code", "code.refactor"],
        registry=registry,
    )

    assert descriptor.source_type.value == "openhands"
    assert descriptor.execution_kind.value == "http_service"
    assert registry.get(descriptor.agent_id) is not None


def test_agent_creation_uses_threshold_for_low_score():
    engine = AgentCreationEngine(threshold=0.6)

    assert engine.should_create_agent(0.4) is True
    assert engine.should_create_agent(0.9) is False
