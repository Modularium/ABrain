import pytest

from core.orchestration import ResultAggregator, StepExecutionResult

pytestmark = pytest.mark.unit


def test_result_aggregator_builds_final_output_and_warning_set():
    aggregator = ResultAggregator()

    result = aggregator.aggregate(
        "plan-1",
        [
            StepExecutionResult(step_id="analyze", selected_agent_id="a1", success=True, output={"summary": "ok"}),
            StepExecutionResult(
                step_id="review",
                selected_agent_id="a2",
                success=True,
                output={"approved": True},
                warnings=["low-confidence"],
            ),
        ],
        metadata={"strategy": "sequential"},
    )

    assert result.success is True
    assert result.final_output == {"approved": True}
    assert result.aggregated_warnings == ["low-confidence"]
    assert result.metadata["outputs_by_step"]["analyze"] == {"summary": "ok"}
