import pytest

from core.decision import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    OnlineUpdater,
)
from core.decision.performance_history import AgentPerformanceHistory
from core.execution.adapters.base import ExecutionResult

pytestmark = pytest.mark.unit


def test_online_updater_creates_training_sample_after_execution():
    updater = OnlineUpdater(train_every=10)
    descriptor = AgentDescriptor(
        agent_id="agent-1",
        display_name="Agent 1",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis.code", "code.refactor"],
    )
    result = ExecutionResult(
        agent_id="agent-1",
        success=True,
        duration_ms=1200,
        cost=0.002,
        output={"status": "ok"},
    )
    history = AgentPerformanceHistory(
        success_rate=0.9,
        avg_latency=1.2,
        avg_cost=0.002,
        recent_failures=0,
        execution_count=4,
    )

    sample = updater.record_execution(
        {"task_type": "code_refactor", "description": "Refactor this module"},
        descriptor,
        result,
        history,
    )

    assert updater.dataset.size() == 1
    assert sample.agent_id == "agent-1"
    assert sample.reward > 0.0
    assert sample.capability_match == 1.0
