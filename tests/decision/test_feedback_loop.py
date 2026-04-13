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


def test_feedback_loop_propagates_token_count():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    update = loop.update_performance(
        "agent-3",
        ExecutionResult(
            agent_id="agent-3",
            success=True,
            output={"ok": True},
            duration_ms=600,
            cost=0.005,
            token_count=1024,
        ),
    )

    assert update.token_count == 1024
    assert update.performance.avg_token_count == pytest.approx(1024.0)


def test_feedback_loop_token_count_none_when_absent():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    update = loop.update_performance(
        "agent-4",
        ExecutionResult(agent_id="agent-4", success=True),
    )

    assert update.token_count is None


def test_feedback_loop_propagates_user_rating_from_metadata():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    update = loop.update_performance(
        "agent-5",
        ExecutionResult(
            agent_id="agent-5",
            success=True,
            metadata={"approval_decision": {"rating": 0.8}},
        ),
    )

    assert update.user_rating == pytest.approx(0.8)
    assert update.performance.avg_user_rating == pytest.approx(0.8)


def test_feedback_loop_user_rating_none_when_no_approval_metadata():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    update = loop.update_performance(
        "agent-6",
        ExecutionResult(agent_id="agent-6", success=True),
    )

    assert update.user_rating is None


def test_feedback_loop_user_rating_preserved_on_rejected_approval():
    store = PerformanceHistoryStore()
    loop = FeedbackLoop(performance_history=store)

    # Rejected path: rating present but learning is skipped
    update = loop.update_performance(
        "agent-7",
        ExecutionResult(
            agent_id="agent-7",
            success=False,
            metadata={
                "approval_status": "rejected",
                "approval_decision": {"rating": 0.2},
            },
        ),
    )

    # rating is surfaced on the update even though learning is skipped
    assert update.user_rating == pytest.approx(0.2)
    assert update.score_delta == 0
    # execution_count must not increment on a skipped result
    assert update.performance.execution_count == 0
