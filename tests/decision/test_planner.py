import pytest

from core.decision import Planner
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def test_planner_maps_code_refactor_to_required_capabilities():
    planner = Planner()

    result = planner.plan(
        TaskContext(
            task_type="code_refactor",
            description="Refactor router",
        )
    )

    assert result.intent.domain == "code"
    assert result.intent.required_capabilities == ["analysis.code", "code.refactor"]


def test_planner_respects_explicit_required_capabilities_from_preferences():
    planner = Planner()

    result = planner.plan(
        TaskContext(
            task_type="system_health",
            preferences={
                "required_capabilities": ["audit.logs", "system.health"],
                "execution_hints": {"minimum_trust_level": "trusted"},
            },
        )
    )

    assert result.intent.required_capabilities == [
        "system.read",
        "system.health",
        "audit.logs",
    ]
    assert result.intent.execution_hints["minimum_trust_level"] == "trusted"
