# Persistent State and Durable Runtime — ABrain Phase N

**Status:** Active design document  
**Phase:** N — Persistent State  
**Canonical basis:** Evolution of existing `ApprovalStore`, `TraceStore`, `PlanExecutionState`, `PerformanceHistoryStore`

---

## Principle

ABrain's durable runtime is **not** a new distributed workflow engine. It is the existing execution stack — approval, orchestration, trace, and learning — made restart-resilient by wiring existing persistence primitives that were already present but not fully connected.

> Persistence is a property of the existing canonical stack, not a new parallel system.

---

## 1. Approval State

**Owner:** `core/approval/store.py` — `ApprovalStore`  
**Backed by:** JSON file (auto-saved on every write when `path` is set)

### What persists:

| Field | Description |
|-------|-------------|
| `approval_id` | Stable UUID — survives restart |
| `plan_id` | Identifies the paused plan |
| `step_id` | Identifies the paused step |
| `status` | `pending` / `approved` / `rejected` / `expired` / `cancelled` |
| `requested_at` | ISO timestamp |
| `metadata.plan_state` | Full `PlanExecutionState` — all prior step results + next step index |
| `metadata.plan` | Full `ExecutionPlan` — all steps and strategy |
| `metadata.trace_id` | Links to the canonical trace |
| `metadata.decision` | Written by `record_decision()` when operator acts |

### Restart behaviour:
- `_get_approval_state()` loads the JSON file on first call if it exists.
- All pending approvals are available immediately after restart.
- `resume_plan()` reads `plan_state` from `approval_request.metadata` — works identically before and after restart.

### What is NOT stored:
- Approval policy configuration (stateless, loaded from env/YAML).
- Runtime secrets or credentials.

---

## 2. Plan / Orchestration State

**Owner:** `core/orchestration/state_store.py` — `PlanStateStore`  
**Backed by:** SQLite (`runtime/abrain_plan_state.sqlite3` via `ABRAIN_PLAN_STATE_DB_PATH`)

### What persists:

| Column | Description |
|--------|-------------|
| `plan_id` | Primary key |
| `trace_id` | Foreign reference to the canonical trace |
| `status` | `completed` / `paused` / `rejected` / `denied` |
| `success` | Boolean outcome |
| `state_json` | Full `PlanExecutionState` — step results, next_step_index, pending_approval_id |
| `result_json` | Full `PlanExecutionResult` — aggregated output, warnings, metadata |
| `created_at` / `updated_at` | ISO timestamps |

### Restart behaviour:
- Paused plans: `state_json` contains the full resume context. Combined with ApprovalStore, restart → resume works without data loss.
- Completed plans: `result_json` is the authoritative record. No re-execution after restart.
- `list_recent_plans()` queries this store directly — O(1) plan-level retrieval without full trace scans.

### Invariants:
- No double-execution: `PlanStateStore.save_result()` upserts on `plan_id` — idempotent.
- Plan status transitions: `run_task_plan` writes initial result → `_decide_plan_step` overwrites after approve/reject.
- Trace linkage: `trace_id` column references the canonical TraceStore.

---

## 3. Trace / Explainability State

**Owner:** `core/audit/trace_store.py` — `TraceStore`  
**Backed by:** SQLite (`runtime/abrain_traces.sqlite3` via `ABRAIN_TRACE_DB_PATH`)

### Already durable (no changes required to core logic):
- Every `create_trace`, `start_span`, `finish_span`, `add_event`, `store_explainability` call commits to SQLite immediately.
- `list_recent_traces(limit)` supports bounded retrieval.
- `get_trace(trace_id)` and `get_explainability(trace_id)` are point lookups.

### Linkage additions (Phase N):
- `ExplainabilityRecord.approval_id` already references the approval — no new column needed.
- `PlanStateStore.trace_id` references the trace — completing the triangle: Plan ↔ Approval ↔ Trace.

### Retention policy:
- Phase N does not introduce TTL or archival. The SQLite file grows until manual pruning. Phase O scope.

---

## 4. Learning-Relevant State

**Owner:** `core/decision/performance_history.py` — `PerformanceHistoryStore`  
**Backed by:** JSON file (load on startup, explicit save only)

### What persists:

| Field | Description |
|-------|-------------|
| `success_rate` | Rolling success fraction per agent |
| `avg_latency` | Rolling average response time |
| `avg_cost` | Rolling average cost |
| `recent_failures` | Recent failure count |
| `execution_count` | Total executions seen |

### Restart behaviour:
- On startup, `_get_learning_state()` loads `ABRAIN_PERF_HISTORY_PATH` (default `runtime/abrain_perf_history.json`) if it exists.
- The routing engine starts with the last-known performance snapshot instead of neutral defaults.
- Auto-saving on every `FeedbackLoop.update_performance()` call is **not** added in Phase N — the data volume and update frequency do not justify write amplification at this stage. Explicit save can be triggered via a future management endpoint.

### Training Dataset:
- `ABRAIN_TRAINING_DATASET_PATH` (default `runtime/abrain_training_dataset.json`) is loaded on startup if present.
- The `OnlineUpdater` accumulates new samples in memory. Persistence of incremental updates is Phase O scope.

### What is NOT added:
- No ML data lake or dataset versioning.
- No automatic training pipeline trigger from the persistence layer.
- No new training-specific API endpoints.

---

## 5. Governance / Approval Traceability

The triangle **Plan ↔ Approval ↔ Trace** is now complete at rest:

```
PlanStateStore.plan_id  ──── PlanStateStore.trace_id ───► TraceStore.trace_id
       │                                                          │
       │                                               ExplainabilityRecord.approval_id
       │                                                          │
       └──────── ApprovalRequest.plan_id ◄──────────────────────┘
                 ApprovalRequest.metadata.trace_id
```

No duplicate audit model. No competing explainability store.

---

## 6. Non-Goals for Phase N

| Item | Reason excluded |
|------|----------------|
| Distributed cluster state | Local durable runtime first |
| Event sourcing / CQRS | No operational need identified |
| Redis / Postgres | SQLite + JSON is sufficient and dependency-free |
| Frontend-side state cache | UI reads from Gateway → services/core → stores |
| Full ML training loop persistence | Phase O scope |
| Policy mutation API | Phase O/P scope |
