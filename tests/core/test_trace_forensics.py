"""S10 — unit tests for the trace forensics drilldown and replay-readiness layer.

Covers:
- ExplainabilityRecord new first-class forensics fields
- ReplayStepInput and ReplayDescriptor models
- TraceStore new columns: persist and round-trip
- TraceStore._build_replay_descriptor() via get_trace()
- TraceSnapshot.replay_descriptor populated correctly
- Backwards compat: old records without new columns produce None/empty defaults
"""

import pytest
from pydantic import ValidationError

from core.audit.trace_models import (
    ExplainabilityRecord,
    ReplayDescriptor,
    ReplayStepInput,
    TraceSnapshot,
)
from core.audit.trace_store import TraceStore

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ExplainabilityRecord — new first-class forensics fields
# ---------------------------------------------------------------------------


def test_explainability_record_new_fields_have_defaults():
    rec = ExplainabilityRecord(
        trace_id="trace-1",
        routing_reason_summary="selected agent-1",
    )
    assert rec.routing_confidence is None
    assert rec.score_gap is None
    assert rec.confidence_band is None
    assert rec.policy_effect is None
    assert rec.scored_candidates == []


def test_explainability_record_new_fields_accepted():
    rec = ExplainabilityRecord(
        trace_id="trace-1",
        routing_reason_summary="selected agent-1 with score 0.85",
        routing_confidence=0.85,
        score_gap=0.12,
        confidence_band="high",
        policy_effect="allow",
        scored_candidates=[
            {"agent_id": "agent-1", "score": 0.85, "capability_match_score": 1.0},
            {"agent_id": "agent-2", "score": 0.73, "capability_match_score": 0.9},
        ],
    )
    assert rec.routing_confidence == pytest.approx(0.85)
    assert rec.score_gap == pytest.approx(0.12)
    assert rec.confidence_band == "high"
    assert rec.policy_effect == "allow"
    assert len(rec.scored_candidates) == 2
    assert rec.scored_candidates[0]["agent_id"] == "agent-1"


def test_explainability_record_confidence_band_normalised():
    rec = ExplainabilityRecord(
        trace_id="trace-1",
        routing_reason_summary="routing",
        confidence_band="  medium  ",
    )
    assert rec.confidence_band == "medium"


def test_explainability_record_policy_effect_normalised():
    rec = ExplainabilityRecord(
        trace_id="trace-1",
        routing_reason_summary="routing",
        policy_effect="  require_approval  ",
    )
    assert rec.policy_effect == "require_approval"


def test_explainability_record_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        ExplainabilityRecord(
            trace_id="trace-1",
            routing_reason_summary="routing",
            undocumented=True,
        )


# ---------------------------------------------------------------------------
# ReplayStepInput
# ---------------------------------------------------------------------------


def test_replay_step_input_minimal():
    step = ReplayStepInput(step_id="step-1")
    assert step.task_type is None
    assert step.required_capabilities == []
    assert step.candidate_agent_ids == []
    assert step.routing_confidence is None
    assert step.confidence_band is None
    assert step.policy_effect is None


def test_replay_step_input_full():
    step = ReplayStepInput(
        step_id="deploy",
        task_type="workflow_automation",
        required_capabilities=["workflow.execute"],
        selected_agent_id="workflow-agent",
        candidate_agent_ids=["workflow-agent", "fallback-agent"],
        routing_confidence=0.78,
        confidence_band="high",
        policy_effect="require_approval",
    )
    assert step.step_id == "deploy"
    assert step.selected_agent_id == "workflow-agent"
    assert len(step.candidate_agent_ids) == 2
    assert step.routing_confidence == pytest.approx(0.78)


def test_replay_step_input_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        ReplayStepInput(step_id="s", unknown_field=True)


# ---------------------------------------------------------------------------
# ReplayDescriptor
# ---------------------------------------------------------------------------


def test_replay_descriptor_minimal():
    rd = ReplayDescriptor(trace_id="trace-1", workflow_name="wf")
    assert rd.can_replay is False
    assert rd.missing_inputs == []
    assert rd.step_inputs == []


def test_replay_descriptor_can_replay():
    rd = ReplayDescriptor(
        trace_id="trace-1",
        workflow_name="system_status",
        task_type="system_status",
        step_inputs=[
            ReplayStepInput(
                step_id="task",
                task_type="system_status",
                candidate_agent_ids=["adminbot-agent"],
                selected_agent_id="adminbot-agent",
                routing_confidence=0.9,
                confidence_band="high",
                policy_effect="allow",
            )
        ],
        can_replay=True,
        missing_inputs=[],
    )
    assert rd.can_replay is True
    assert len(rd.step_inputs) == 1


def test_replay_descriptor_model_dump_json():
    rd = ReplayDescriptor(
        trace_id="t1",
        workflow_name="wf",
        task_type="system_status",
        can_replay=True,
    )
    dumped = rd.model_dump(mode="json")
    assert dumped["trace_id"] == "t1"
    assert dumped["can_replay"] is True


def test_replay_descriptor_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        ReplayDescriptor(trace_id="t", workflow_name="wf", bogus=1)


# ---------------------------------------------------------------------------
# TraceSnapshot — replay_descriptor field
# ---------------------------------------------------------------------------


def test_trace_snapshot_replay_descriptor_defaults_none(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("bare_workflow", task_id="task-x")
    store.finish_trace(trace.trace_id, status="completed")
    snapshot = store.get_trace(trace.trace_id)
    assert snapshot is not None
    # No explainability records → no replay descriptor
    assert snapshot.replay_descriptor is None


# ---------------------------------------------------------------------------
# TraceStore — S10 column persistence and round-trip
# ---------------------------------------------------------------------------


def test_trace_store_persists_new_forensics_fields(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("routing_workflow", task_id="task-r")
    exp = ExplainabilityRecord(
        trace_id=trace.trace_id,
        step_id="step-1",
        selected_agent_id="agent-1",
        candidate_agent_ids=["agent-1", "agent-2"],
        selected_score=0.82,
        routing_reason_summary="selected agent-1 with score 0.82",
        routing_confidence=0.82,
        score_gap=0.10,
        confidence_band="high",
        policy_effect="allow",
        scored_candidates=[
            {"agent_id": "agent-1", "score": 0.82, "capability_match_score": 1.0},
            {"agent_id": "agent-2", "score": 0.72, "capability_match_score": 0.8},
        ],
    )
    store.store_explainability(exp)
    snapshot = store.get_trace(trace.trace_id)
    assert snapshot is not None
    assert len(snapshot.explainability) == 1
    retrieved = snapshot.explainability[0]
    assert retrieved.routing_confidence == pytest.approx(0.82)
    assert retrieved.score_gap == pytest.approx(0.10)
    assert retrieved.confidence_band == "high"
    assert retrieved.policy_effect == "allow"
    assert len(retrieved.scored_candidates) == 2
    assert retrieved.scored_candidates[0]["agent_id"] == "agent-1"


def test_trace_store_missing_forensics_columns_produce_none_defaults(tmp_path):
    """Old explainability rows lacking the new columns should give None/[] defaults."""
    import json
    import sqlite3

    db_path = tmp_path / "old.sqlite3"
    # Create a minimal table WITHOUT the S10 columns (simulates old schema)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE traces (
            trace_id TEXT PRIMARY KEY,
            workflow_name TEXT NOT NULL,
            task_id TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE spans (
            span_id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            parent_span_id TEXT,
            span_type TEXT NOT NULL,
            name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL,
            attributes_json TEXT NOT NULL,
            events_json TEXT NOT NULL,
            error_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE explainability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            step_id TEXT,
            selected_agent_id TEXT,
            candidate_agent_ids_json TEXT NOT NULL,
            selected_score REAL,
            routing_reason_summary TEXT NOT NULL,
            matched_policy_ids_json TEXT NOT NULL,
            approval_required INTEGER NOT NULL,
            approval_id TEXT,
            metadata_json TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO traces VALUES (?,?,?,?,?,?,?)",
        ("trace-old", "legacy_workflow", None, "2025-01-01T00:00:00", None, "completed", "{}"),
    )
    conn.execute(
        """INSERT INTO explainability
           (trace_id, step_id, selected_agent_id, candidate_agent_ids_json,
            selected_score, routing_reason_summary, matched_policy_ids_json,
            approval_required, approval_id, metadata_json)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        ("trace-old", None, "agent-1", '["agent-1"]', 0.8, "selected agent-1", "[]", 0, None, "{}"),
    )
    conn.commit()
    conn.close()

    # Open with TraceStore — it will run ALTER TABLE ADD COLUMN (new columns appear)
    store = TraceStore(db_path)
    snapshot = store.get_trace("trace-old")
    assert snapshot is not None
    assert len(snapshot.explainability) == 1
    exp = snapshot.explainability[0]
    # New fields should be None/empty (old row, no data in new columns)
    assert exp.routing_confidence is None
    assert exp.score_gap is None
    assert exp.confidence_band is None
    assert exp.policy_effect is None
    assert exp.scored_candidates == []


# ---------------------------------------------------------------------------
# TraceStore._build_replay_descriptor via get_trace
# ---------------------------------------------------------------------------


def test_replay_descriptor_built_from_explainability(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("routing_workflow", task_id="task-r")
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="step-1",
            selected_agent_id="agent-1",
            candidate_agent_ids=["agent-1", "agent-2"],
            selected_score=0.82,
            routing_reason_summary="selected agent-1",
            routing_confidence=0.82,
            confidence_band="high",
            policy_effect="allow",
            metadata={"routing_decision": {"task_type": "system_status", "required_capabilities": []}},
        )
    )
    snapshot = store.get_trace(trace.trace_id)
    assert snapshot is not None
    rd = snapshot.replay_descriptor
    assert rd is not None
    assert rd.trace_id == trace.trace_id
    assert rd.workflow_name == "routing_workflow"
    assert rd.task_id == "task-r"
    assert len(rd.step_inputs) == 1
    step = rd.step_inputs[0]
    assert step.step_id == "step-1"
    assert step.selected_agent_id == "agent-1"
    assert "agent-1" in step.candidate_agent_ids
    assert step.routing_confidence == pytest.approx(0.82)
    assert step.confidence_band == "high"
    assert step.policy_effect == "allow"


def test_replay_descriptor_can_replay_true_when_complete(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("routing_workflow")
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="task",
            candidate_agent_ids=["agent-1"],
            routing_reason_summary="selected agent-1",
            metadata={"routing_decision": {"task_type": "system_status"}},
        )
    )
    snapshot = store.get_trace(trace.trace_id)
    rd = snapshot.replay_descriptor
    assert rd is not None
    assert rd.can_replay is True
    assert rd.missing_inputs == []


def test_replay_descriptor_missing_task_type_when_not_in_metadata(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("bare_routing")
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="task",
            candidate_agent_ids=["agent-1"],
            routing_reason_summary="selected agent-1",
            # No task_type in metadata.routing_decision
        )
    )
    snapshot = store.get_trace(trace.trace_id)
    rd = snapshot.replay_descriptor
    assert rd is not None
    assert rd.can_replay is False
    assert "task_type" in rd.missing_inputs


def test_replay_descriptor_missing_candidates(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("bare_routing")
    store.store_explainability(
        ExplainabilityRecord(
            trace_id=trace.trace_id,
            step_id="task",
            candidate_agent_ids=[],  # no candidates
            routing_reason_summary="no candidates available",
            metadata={"routing_decision": {"task_type": "system_status"}},
        )
    )
    snapshot = store.get_trace(trace.trace_id)
    rd = snapshot.replay_descriptor
    assert rd is not None
    assert rd.can_replay is False
    assert "candidate_agent_ids" in rd.missing_inputs


def test_replay_descriptor_none_without_explainability(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("no_routing_workflow")
    snapshot = store.get_trace(trace.trace_id)
    assert snapshot is not None
    assert snapshot.replay_descriptor is None


def test_replay_descriptor_multiple_steps(tmp_path):
    store = TraceStore(tmp_path / "t.sqlite3")
    trace = store.create_trace("multi_step_plan")
    for step_id, agent in [("step-1", "agent-a"), ("step-2", "agent-b")]:
        store.store_explainability(
            ExplainabilityRecord(
                trace_id=trace.trace_id,
                step_id=step_id,
                selected_agent_id=agent,
                candidate_agent_ids=[agent],
                routing_reason_summary=f"selected {agent}",
                routing_confidence=0.9,
                confidence_band="high",
                metadata={"routing_decision": {"task_type": "code_review"}},
            )
        )
    snapshot = store.get_trace(trace.trace_id)
    rd = snapshot.replay_descriptor
    assert rd is not None
    assert len(rd.step_inputs) == 2
    assert rd.step_inputs[0].step_id == "step-1"
    assert rd.step_inputs[1].step_id == "step-2"
    assert rd.can_replay is True
