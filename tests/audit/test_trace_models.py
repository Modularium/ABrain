import pytest

from core.audit import ExplainabilityRecord, SpanRecord, TraceEvent, TraceRecord, TraceSnapshot

pytestmark = pytest.mark.unit


def test_trace_models_are_serializable_and_nested():
    trace = TraceRecord(
        workflow_name="run_task",
        task_id="task-1",
        metadata={"entrypoint": "run_task"},
    )
    span = SpanRecord(
        trace_id=trace.trace_id,
        span_type="decision",
        name="routing",
        attributes={"selected_agent_id": "agent-1"},
        events=[
            TraceEvent(
                event_type="routing_completed",
                message="Routing finished successfully.",
                payload={"selected_agent_id": "agent-1"},
            )
        ],
    )
    explainability = ExplainabilityRecord(
        trace_id=trace.trace_id,
        step_id="execute",
        selected_agent_id="agent-1",
        candidate_agent_ids=["agent-1", "agent-2"],
        selected_score=0.82,
        routing_reason_summary="selected agent-1 with score 0.820; 2 ranked candidates; 1 rejected by CandidateFilter",
        matched_policy_ids=["allow-default"],
        approval_required=False,
        metadata={"candidate_filter": {"allowed": 1}},
    )

    snapshot = TraceSnapshot(
        trace=trace,
        spans=[span],
        explainability=[explainability],
    )

    dumped = snapshot.model_dump(mode="json")

    assert dumped["trace"]["workflow_name"] == "run_task"
    assert dumped["spans"][0]["events"][0]["event_type"] == "routing_completed"
    assert dumped["explainability"][0]["selected_agent_id"] == "agent-1"
