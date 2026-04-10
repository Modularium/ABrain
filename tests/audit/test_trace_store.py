import pytest

from core.audit import ExplainabilityRecord, TraceStore

pytestmark = pytest.mark.unit


def test_trace_store_persists_trace_span_event_and_explainability(tmp_path):
    store = TraceStore(tmp_path / "traces.sqlite3")
    trace = store.create_trace(
        "run_task",
        task_id="task-1",
        metadata={"entrypoint": "run_task"},
    )
    span = store.start_span(
        trace.trace_id,
        span_type="decision",
        name="routing",
        attributes={"task_type": "system_status"},
    )
    store.add_event(
        span.span_id,
        event_type="routing_completed",
        message="Routing finished.",
        payload={"selected_agent_id": "adminbot-agent"},
    )
    store.finish_span(
        span.span_id,
        status="completed",
        attributes={"selected_agent_id": "adminbot-agent"},
    )
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="execute",
            selected_agent_id="adminbot-agent",
            candidate_agent_ids=["adminbot-agent"],
            selected_score=0.91,
            routing_reason_summary="selected adminbot-agent with score 0.910; 1 ranked candidates; 0 rejected by CandidateFilter",
            matched_policy_ids=[],
            approval_required=False,
            metadata={"routing_decision": {"selected_agent_id": "adminbot-agent"}},
        )
    )
    store.finish_trace(
        trace.trace_id,
        status="completed",
        metadata={"selected_agent_id": "adminbot-agent"},
    )

    snapshot = store.get_trace(trace.trace_id)
    recent = store.list_recent_traces(limit=5)

    assert snapshot is not None
    assert snapshot.trace.status == "completed"
    assert snapshot.spans[0].events[0].event_type == "routing_completed"
    assert snapshot.explainability[0].selected_agent_id == "adminbot-agent"
    assert recent[0].trace_id == trace.trace_id
