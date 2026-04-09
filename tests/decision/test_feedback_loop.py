import pytest

from core.decision import FeedbackLoop, PerformanceHistoryStore
from core.execution.adapters.base import ExecutionResult
from core.models.errors import StructuredError

pytestmark = pytest.mark.unit


def test_feedback_loop_updates_success_history():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    update = loop.update_performance(
        "agent-1",
        ExecutionResult(
            agent_id="agent-1",
            success=True,
            output={"ok": True},
            duration_ms=800,
            cost=0.002,
        ),
    )

    assert update.score_delta == 1
    assert update.performance.execution_count == 1
    assert update.performance.success_rate == 1.0


def test_feedback_loop_updates_failure_history():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    update = loop.update_performance(
        "agent-2",
        ExecutionResult(
            agent_id="agent-2",
            success=False,
            error=StructuredError(error_code="adapter_error", message="failed"),
            duration_ms=1200,
        ),
    )

    assert update.score_delta == -1
    assert update.performance.execution_count == 1
    assert update.performance.recent_failures == 1
