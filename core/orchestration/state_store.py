"""SQLite-backed store for plan execution state.

Provides restart-resilient storage of PlanExecutionResult records keyed by
plan_id.  Follows the same pattern as core.audit.trace_store.TraceStore —
one connection per call, row_factory = sqlite3.Row, schema ensured on init.

Environment variable:
    ABRAIN_PLAN_STATE_DB_PATH  — override the default SQLite path
                                  (default: runtime/abrain_plan_state.sqlite3)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .result_aggregation import OrchestrationStatus, PlanExecutionResult, PlanExecutionState


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class PlanStateStore:
    """Persist plan execution results in SQLite for restart-safe plan queries.

    Each row corresponds to one plan execution keyed by ``plan_id``.  The row
    is upserted on every ``save_result`` call so the store always reflects the
    latest known state.

    Relationship to other stores:
    - ``trace_id`` column links to ``TraceStore`` — completing the
      Plan ↔ Trace linkage at rest.
    - Paused plans embed their resume context in ``ApprovalStore`` via
      ``approval_request.metadata["plan_state"]``.  This store holds the
      aggregated ``PlanExecutionResult`` that wraps that state.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def save_result(
        self,
        result: PlanExecutionResult,
        *,
        trace_id: str | None = None,
    ) -> None:
        """Upsert a plan execution result.

        Idempotent: if ``plan_id`` already exists the row is overwritten with
        the latest status and result payload.  ``created_at`` is preserved on
        conflict; ``updated_at`` is always refreshed.
        """
        now = _utcnow_iso()
        state_payload: str | None = None
        if result.state is not None:
            state_payload = json.dumps(result.state.model_dump(mode="json"), sort_keys=True)
        result_payload = json.dumps(result.model_dump(mode="json"), sort_keys=True)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO plan_runs (
                    plan_id, trace_id, status, success,
                    pending_approval_id,
                    state_json, result_json,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET
                    trace_id            = excluded.trace_id,
                    status              = excluded.status,
                    success             = excluded.success,
                    pending_approval_id = excluded.pending_approval_id,
                    state_json          = excluded.state_json,
                    result_json         = excluded.result_json,
                    updated_at          = excluded.updated_at
                """,
                (
                    result.plan_id,
                    trace_id,
                    result.status.value,
                    int(result.success),
                    result.state.pending_approval_id if result.state else None,
                    state_payload,
                    result_payload,
                    now,
                    now,
                ),
            )

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def get_result(self, plan_id: str) -> PlanExecutionResult | None:
        """Return the stored result for ``plan_id``, or ``None``."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM plan_runs WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            return None
        return PlanExecutionResult.model_validate(json.loads(row["result_json"]))

    def get_state(self, plan_id: str) -> PlanExecutionState | None:
        """Return the stored execution state for ``plan_id``, or ``None``."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM plan_runs WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        if row is None or not row["state_json"]:
            return None
        return PlanExecutionState.model_validate(json.loads(row["state_json"]))

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return summary rows for the most recently updated plans.

        Returns lightweight dicts — callers can use ``get_result`` for the
        full payload when needed.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    plan_id, trace_id, status, success,
                    pending_approval_id, updated_at, created_at
                FROM plan_runs
                ORDER BY updated_at DESC, plan_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "plan_id": row["plan_id"],
                "trace_id": row["trace_id"],
                "status": row["status"],
                "success": bool(row["success"]),
                "pending_approval_id": row["pending_approval_id"],
                "updated_at": row["updated_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_by_status(
        self,
        status: str | OrchestrationStatus,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return summary rows filtered by orchestration status."""
        status_value = status.value if isinstance(status, OrchestrationStatus) else str(status)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    plan_id, trace_id, status, success,
                    pending_approval_id, updated_at, created_at
                FROM plan_runs
                WHERE status = ?
                ORDER BY updated_at DESC, plan_id DESC
                LIMIT ?
                """,
                (status_value, limit),
            ).fetchall()
        return [
            {
                "plan_id": row["plan_id"],
                "trace_id": row["trace_id"],
                "status": row["status"],
                "success": bool(row["success"]),
                "pending_approval_id": row["pending_approval_id"],
                "updated_at": row["updated_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS plan_runs (
                    plan_id             TEXT PRIMARY KEY,
                    trace_id            TEXT,
                    status              TEXT NOT NULL,
                    success             INTEGER NOT NULL,
                    pending_approval_id TEXT,
                    state_json          TEXT,
                    result_json         TEXT NOT NULL,
                    created_at          TEXT NOT NULL,
                    updated_at          TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_plan_runs_updated
                    ON plan_runs (updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_plan_runs_status
                    ON plan_runs (status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_plan_runs_trace
                    ON plan_runs (trace_id)
                    WHERE trace_id IS NOT NULL;
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
