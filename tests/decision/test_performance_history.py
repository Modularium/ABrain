from pathlib import Path

import pytest

from core.decision import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    PerformanceHistoryStore,
)

pytestmark = pytest.mark.unit


def test_performance_history_reads_metadata_defaults():
    descriptor = AgentDescriptor(
        agent_id="agent-1",
        display_name="Agent 1",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        metadata={
            "success_rate": "0.8",
            "avg_response_time": "2.5",
            "estimated_cost_per_token": "0.003",
            "recent_failures": "1",
            "execution_count": "12",
            "load_factor": "0.4",
        },
    )

    history = PerformanceHistoryStore().get_for_descriptor(descriptor)

    assert history.success_rate == pytest.approx(0.8)
    assert history.avg_latency == pytest.approx(2.5)
    assert history.avg_cost == pytest.approx(0.003)
    assert history.execution_count == 12


def test_performance_history_records_and_persists_results(tmp_path: Path):
    store = PerformanceHistoryStore()

    first = store.record_result("agent-1", success=True, latency=1.0, cost=0.002)
    second = store.record_result("agent-1", success=False, latency=3.0, cost=0.004)
    saved = store.save_json(tmp_path / "performance.json")
    loaded = PerformanceHistoryStore.load_json(saved)

    assert first.execution_count == 1
    assert second.execution_count == 2
    assert second.success_rate == pytest.approx(0.5)
    assert loaded.get("agent-1").recent_failures == 1
