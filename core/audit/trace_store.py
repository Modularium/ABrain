"""SQLite-backed trace and explainability store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from .trace_models import (
    ExplainabilityRecord,
    ReplayDescriptor,
    ReplayStepInput,
    SpanRecord,
    TraceEvent,
    TraceRecord,
    TraceSnapshot,
    utcnow,
)


class TraceStore:
    """Persist traces, spans and explainability records in SQLite."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def create_trace(
        self,
        workflow_name: str,
        *,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> TraceRecord:
        record = TraceRecord(
            trace_id=trace_id or f"trace-{uuid4().hex}",
            workflow_name=workflow_name,
            task_id=task_id,
            metadata=dict(metadata or {}),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO traces (trace_id, workflow_name, task_id, started_at, ended_at, status, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.trace_id,
                    record.workflow_name,
                    record.task_id,
                    record.started_at.isoformat(),
                    None,
                    record.status,
                    json.dumps(record.metadata, sort_keys=True),
                ),
            )
        return record

    def finish_trace(
        self,
        trace_id: str,
        *,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceRecord:
        snapshot = self.get_trace(trace_id)
        if snapshot is None:
            raise KeyError(f"unknown trace_id: {trace_id}")
        trace = snapshot.trace.model_copy(
            update={
                "ended_at": utcnow(),
                "status": status,
                "metadata": {
                    **snapshot.trace.metadata,
                    **(metadata or {}),
                },
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE traces
                SET ended_at = ?, status = ?, metadata_json = ?
                WHERE trace_id = ?
                """,
                (
                    trace.ended_at.isoformat() if trace.ended_at else None,
                    trace.status,
                    json.dumps(trace.metadata, sort_keys=True),
                    trace.trace_id,
                ),
            )
        return trace

    def start_span(
        self,
        trace_id: str,
        *,
        span_type: str,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        span_id: str | None = None,
    ) -> SpanRecord:
        span = SpanRecord(
            span_id=span_id or f"span-{uuid4().hex}",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=span_type,
            name=name,
            attributes=dict(attributes or {}),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO spans (
                    span_id,
                    trace_id,
                    parent_span_id,
                    span_type,
                    name,
                    started_at,
                    ended_at,
                    status,
                    attributes_json,
                    events_json,
                    error_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span.span_id,
                    span.trace_id,
                    span.parent_span_id,
                    span.span_type,
                    span.name,
                    span.started_at.isoformat(),
                    None,
                    span.status,
                    json.dumps(span.attributes, sort_keys=True),
                    "[]",
                    None,
                ),
            )
        return span

    def finish_span(
        self,
        span_id: str,
        *,
        status: str,
        attributes: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> SpanRecord:
        span = self._get_span(span_id)
        if span is None:
            raise KeyError(f"unknown span_id: {span_id}")
        updated = span.model_copy(
            update={
                "ended_at": utcnow(),
                "status": status,
                "attributes": {
                    **span.attributes,
                    **(attributes or {}),
                },
                "error": error or span.error,
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE spans
                SET ended_at = ?, status = ?, attributes_json = ?, error_json = ?
                WHERE span_id = ?
                """,
                (
                    updated.ended_at.isoformat() if updated.ended_at else None,
                    updated.status,
                    json.dumps(updated.attributes, sort_keys=True),
                    json.dumps(updated.error, sort_keys=True) if updated.error is not None else None,
                    updated.span_id,
                ),
            )
        return updated

    def add_event(
        self,
        span_id: str,
        *,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> SpanRecord:
        span = self._get_span(span_id)
        if span is None:
            raise KeyError(f"unknown span_id: {span_id}")
        events = list(span.events)
        events.append(
            TraceEvent(
                event_type=event_type,
                message=message,
                payload=dict(payload or {}),
            )
        )
        updated = span.model_copy(update={"events": events})
        with self._connect() as connection:
            connection.execute(
                "UPDATE spans SET events_json = ? WHERE span_id = ?",
                (
                    json.dumps([item.model_dump(mode="json") for item in updated.events], sort_keys=True),
                    updated.span_id,
                ),
            )
        return updated

    def store_explainability(self, record: ExplainabilityRecord) -> ExplainabilityRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO explainability (
                    trace_id,
                    step_id,
                    selected_agent_id,
                    candidate_agent_ids_json,
                    selected_score,
                    routing_reason_summary,
                    matched_policy_ids_json,
                    approval_required,
                    approval_id,
                    routing_confidence,
                    score_gap,
                    confidence_band,
                    policy_effect,
                    scored_candidates_json,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.trace_id,
                    record.step_id,
                    record.selected_agent_id,
                    json.dumps(record.candidate_agent_ids, sort_keys=True),
                    record.selected_score,
                    record.routing_reason_summary,
                    json.dumps(record.matched_policy_ids, sort_keys=True),
                    int(record.approval_required),
                    record.approval_id,
                    record.routing_confidence,
                    record.score_gap,
                    record.confidence_band,
                    record.policy_effect,
                    json.dumps(record.scored_candidates, sort_keys=True),
                    json.dumps(record.metadata, sort_keys=True),
                ),
            )
        return record

    def get_trace(self, trace_id: str) -> TraceSnapshot | None:
        with self._connect() as connection:
            trace_row = connection.execute(
                "SELECT * FROM traces WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
            if trace_row is None:
                return None
            span_rows = connection.execute(
                "SELECT * FROM spans WHERE trace_id = ? ORDER BY started_at, span_id",
                (trace_id,),
            ).fetchall()
            explain_rows = connection.execute(
                "SELECT * FROM explainability WHERE trace_id = ? ORDER BY id",
                (trace_id,),
            ).fetchall()
        trace = self._row_to_trace(trace_row)
        explainability = self._normalize_explainability_records(
            trace,
            [self._row_to_explainability(row) for row in explain_rows],
        )
        return TraceSnapshot(
            trace=trace,
            spans=[self._row_to_span(row) for row in span_rows],
            explainability=explainability,
            replay_descriptor=self._build_replay_descriptor(trace, explainability),
        )

    def get_explainability(self, trace_id: str) -> list[ExplainabilityRecord]:
        snapshot = self.get_trace(trace_id)
        if snapshot is None:
            return []
        return snapshot.explainability

    def list_recent_traces(self, limit: int = 10) -> list[TraceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM traces
                ORDER BY started_at DESC, trace_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_trace(row) for row in rows]

    def delete_trace(self, trace_id: str) -> bool:
        """Delete one trace and its spans + explainability rows.

        Returns ``True`` if a row was removed, ``False`` if the trace
        was already absent. Destructive: the caller owns the retention
        decision — this store does not re-check policy.
        """
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM traces WHERE trace_id = ?",
                (trace_id,),
            )
            removed = cursor.rowcount > 0
            connection.execute(
                "DELETE FROM spans WHERE trace_id = ?",
                (trace_id,),
            )
            connection.execute(
                "DELETE FROM explainability WHERE trace_id = ?",
                (trace_id,),
            )
        return removed

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    workflow_name TEXT NOT NULL,
                    task_id TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS spans (
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
                    error_json TEXT,
                    FOREIGN KEY(trace_id) REFERENCES traces(trace_id)
                );
                CREATE TABLE IF NOT EXISTS explainability (
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
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(trace_id) REFERENCES traces(trace_id)
                );
                """
            )
            # S10: additive forensics columns — ALTER TABLE is idempotent via try/except
            for _ddl in (
                "ALTER TABLE explainability ADD COLUMN routing_confidence REAL",
                "ALTER TABLE explainability ADD COLUMN score_gap REAL",
                "ALTER TABLE explainability ADD COLUMN confidence_band TEXT",
                "ALTER TABLE explainability ADD COLUMN policy_effect TEXT",
                "ALTER TABLE explainability ADD COLUMN scored_candidates_json TEXT",
            ):
                try:
                    connection.execute(_ddl)
                except Exception:  # OperationalError: duplicate column
                    pass

    def _get_span(self, span_id: str) -> SpanRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM spans WHERE span_id = ?",
                (span_id,),
            ).fetchone()
        return self._row_to_span(row) if row is not None else None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_trace(self, row: sqlite3.Row) -> TraceRecord:
        return TraceRecord.model_validate(
            {
                "trace_id": row["trace_id"],
                "workflow_name": row["workflow_name"],
                "task_id": row["task_id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "status": row["status"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
        )

    def _row_to_span(self, row: sqlite3.Row) -> SpanRecord:
        return SpanRecord.model_validate(
            {
                "span_id": row["span_id"],
                "trace_id": row["trace_id"],
                "parent_span_id": row["parent_span_id"],
                "span_type": row["span_type"],
                "name": row["name"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "status": row["status"],
                "attributes": json.loads(row["attributes_json"] or "{}"),
                "events": json.loads(row["events_json"] or "[]"),
                "error": json.loads(row["error_json"]) if row["error_json"] else None,
            }
        )

    def _row_to_explainability(self, row: sqlite3.Row) -> ExplainabilityRecord:
        keys = row.keys()
        metadata = json.loads(row["metadata_json"] or "{}")
        legacy_routing = metadata.pop("routing_decision", None)
        if isinstance(legacy_routing, dict):
            metadata.setdefault("task_type", legacy_routing.get("task_type"))
            metadata.setdefault(
                "required_capabilities",
                list(legacy_routing.get("required_capabilities") or []),
            )
            diagnostics = legacy_routing.get("diagnostics") or {}
            selected_candidate = diagnostics.get("selected_candidate") or {}
            metadata.setdefault(
                "routing_model_source",
                diagnostics.get("neural_policy_source"),
            )
            metadata.setdefault(
                "selected_candidate_model_source",
                selected_candidate.get("model_source"),
            )
            metadata.setdefault(
                "selected_candidate_feature_summary",
                selected_candidate.get("feature_summary") or {},
            )

        scored_candidates = (
            json.loads(row["scored_candidates_json"] or "[]")
            if "scored_candidates_json" in keys
            else []
        )
        if not scored_candidates and isinstance(legacy_routing, dict):
            scored_candidates = [
                {
                    "agent_id": candidate.get("agent_id"),
                    "score": candidate.get("score"),
                    "capability_match_score": candidate.get("capability_match_score"),
                }
                for candidate in (legacy_routing.get("ranked_candidates") or [])
                if isinstance(candidate, dict)
            ]

        return ExplainabilityRecord.model_validate(
            {
                "trace_id": row["trace_id"],
                "step_id": row["step_id"],
                "selected_agent_id": row["selected_agent_id"],
                "candidate_agent_ids": json.loads(row["candidate_agent_ids_json"] or "[]"),
                "selected_score": row["selected_score"],
                "routing_reason_summary": row["routing_reason_summary"],
                "matched_policy_ids": json.loads(row["matched_policy_ids_json"] or "[]"),
                "approval_required": bool(row["approval_required"]),
                "approval_id": row["approval_id"],
                # S10 forensics columns — present on new rows, absent on old rows
                "routing_confidence": (
                    row["routing_confidence"]
                    if "routing_confidence" in keys and row["routing_confidence"] is not None
                    else (legacy_routing or {}).get("routing_confidence")
                ),
                "score_gap": (
                    row["score_gap"]
                    if "score_gap" in keys and row["score_gap"] is not None
                    else (legacy_routing or {}).get("score_gap")
                ),
                "confidence_band": (
                    row["confidence_band"]
                    if "confidence_band" in keys and row["confidence_band"] is not None
                    else (legacy_routing or {}).get("confidence_band")
                ),
                "policy_effect": row["policy_effect"] if "policy_effect" in keys else None,
                "scored_candidates": scored_candidates,
                "metadata": metadata,
            }
        )

    def _normalize_explainability_records(
        self,
        trace: TraceRecord,
        explainability: list[ExplainabilityRecord],
    ) -> list[ExplainabilityRecord]:
        """Lift legacy trace-level fields into the canonical explainability model."""
        policy_effect = trace.metadata.get("policy_effect")
        if not isinstance(policy_effect, str) or not policy_effect.strip():
            return explainability
        return [
            record
            if record.policy_effect is not None
            else record.model_copy(update={"policy_effect": policy_effect})
            for record in explainability
        ]

    def _build_replay_descriptor(
        self,
        trace: TraceRecord,
        explainability: list[ExplainabilityRecord],
    ) -> ReplayDescriptor | None:
        """Derive a replay-readiness descriptor from stored trace and explainability records.

        Returns ``None`` when there are no explainability records (traces with no
        routing decisions do not have meaningful replay context).
        """
        if not explainability:
            return None

        # Extract task_type: prefer trace metadata, fallback to explainability metadata.
        task_type: str | None = trace.metadata.get("task_type")
        if not task_type:
            first_metadata = explainability[0].metadata
            task_type = first_metadata.get("task_type") or None

        # Build per-step inputs
        step_inputs: list[ReplayStepInput] = []
        for exp in explainability:
            step_inputs.append(
                ReplayStepInput(
                    step_id=exp.step_id or "task",
                    task_type=exp.metadata.get("task_type") or task_type,
                    required_capabilities=list(exp.metadata.get("required_capabilities") or []),
                    selected_agent_id=exp.selected_agent_id,
                    candidate_agent_ids=list(exp.candidate_agent_ids),
                    routing_confidence=exp.routing_confidence,
                    confidence_band=exp.confidence_band,
                    policy_effect=exp.policy_effect,
                )
            )

        # can_replay: we have task_type and at least one decision step with candidates
        missing: list[str] = []
        if not task_type:
            missing.append("task_type")
        if not any(si.candidate_agent_ids for si in step_inputs):
            missing.append("candidate_agent_ids")

        return ReplayDescriptor(
            trace_id=trace.trace_id,
            workflow_name=trace.workflow_name,
            task_type=task_type,
            task_id=trace.task_id,
            started_at=trace.started_at.isoformat() if trace.started_at else None,
            step_inputs=step_inputs,
            can_replay=len(missing) == 0,
            missing_inputs=missing,
            metadata={
                "strategy": trace.metadata.get("strategy"),
                "plan_id": trace.metadata.get("plan_id"),
                "step_count": len(step_inputs),
            },
        )
