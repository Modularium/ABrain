import pytest

from core.decision import PlanBuilder, PlanStrategy
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def test_plan_builder_creates_single_step_plan_for_simple_task():
    builder = PlanBuilder()

    plan = builder.build(TaskContext(task_type="system_status", description="Check system status"))

    assert plan.strategy == PlanStrategy.SINGLE
    assert len(plan.steps) == 1
    assert plan.steps[0].required_capabilities == ["system.read", "system.status"]


def test_plan_builder_creates_multi_step_plan_for_large_code_task():
    builder = PlanBuilder()

    plan = builder.build(
        TaskContext(
            task_type="code_refactor",
            description="Refactor the routing stack",
            preferences={
                "execution_hints": {
                    "task_scale": "large",
                    "allow_parallel_quality_checks": True,
                }
            },
        )
    )

    assert plan.strategy == PlanStrategy.PARALLEL_GROUPS
    assert [step.step_id for step in plan.steps] == ["analyze", "implement", "test", "review"]
    assert plan.steps[1].inputs_from_steps == ["analyze"]
    assert plan.steps[2].allow_parallel_group == "quality"
    assert plan.steps[3].allow_parallel_group == "quality"
