# Phase N — Persistent State Review

**Date:** 2026-04-11  
**Branch:** `codex/phaseN-persistent-state`  
**Review type:** Self-review — merge gate passed  
**Gate result:** 158 passed, 2 skipped (pre-existing) — 0 failures

---

## 1. What was identified

See `docs/reviews/phaseN_state_inventory.md` for the full analysis. Summary:

| Surface | Pre-Phase-N status |
|---------|--------------------|
| `TraceStore` | Already durable (SQLite) |
| `ApprovalStore` | In-memory only — restart gap |
| `PlanExecutionState` | Embedded in ApprovalStore → same gap |
| `PerformanceHistoryStore` | In-memory only — cold start after restart |
| `PlanStateStore` | Did not exist — plan queries required full trace scan |
| `PolicyRegistry` | Restart-safe — stateless load from YAML |
| `TrainingDataset` | In-memory only — minor gap |

---

## 2. What was canonically evolved (not replaced)

### `core/approval/store.py` — unchanged
The class already had `save_json` / `load_json` / `_auto_save`. No code change needed.

### `core/orchestration/__init__.py` — minor export addition
Added `PlanStateStore` to `__all__`.

### `core/orchestration/state_store.py` — new file
**Pattern:** Follows `TraceStore` exactly — SQLite, `row_factory = sqlite3.Row`, `_ensure_schema()` on init, one connection per call.  
**Purpose:** Queryable plan-execution state at O(1) per plan_id.  
**No new infrastructure:** stdlib `sqlite3` only, same pattern as the already-canonical `TraceStore`.

### `services/core.py` — targeted extensions

| Function | Change |
|----------|--------|
| `_get_approval_state()` | Wire `ABRAIN_APPROVAL_STORE_PATH` → load JSON if exists; create with path otherwise. ApprovalStore auto-saves on every mutation. |
| `_get_learning_state()` | Load `PerformanceHistoryStore` from `ABRAIN_PERF_HISTORY_PATH` if present; load `TrainingDataset` from `ABRAIN_TRAINING_DATASET_PATH` if present. No auto-save added. |
| `_get_plan_state_store()` | New helper. Same pattern as `_get_trace_state()`. |
| `run_task_plan()` | After `orchestrator.execute_plan()`, upsert result into `PlanStateStore`. Failure is logged and silently swallowed — plan execution is not gated on store availability. |
| `_decide_plan_step()` | After `resume_plan()`, upsert updated result into `PlanStateStore`. Same defensive pattern. |
| `list_recent_plans()` | Queries `PlanStateStore.list_recent()` first (O(1)). Falls through to legacy trace scan if store unavailable or query fails — backward compatible. |

---

## 3. Restart/Resume gaps closed

| Gap | Solution | Evidence |
|-----|----------|----------|
| Pending approvals lost on restart | `_get_approval_state()` loads from JSON file | `tests/state/test_approval_store_persistence.py` |
| Plan resume context lost on restart | Plan state embedded in ApprovalRequest.metadata — survives once approval store is persistent | `tests/state/test_resume_after_restart.py` |
| No queryable plan state for completed plans | `PlanStateStore` (SQLite) records every `PlanExecutionResult` | `tests/state/test_plan_state_persistence.py` |
| Routing engine starts cold after restart | `PerformanceHistoryStore` loaded from disk on `_get_learning_state()` | `tests/services/test_durable_runtime_flow.py` |
| Plan ↔ Trace linkage not queryable | `PlanStateStore.trace_id` column links every plan result to its canonical trace | `tests/state/test_trace_plan_linkage.py` |

---

## 4. How Approval / Plans / Trace now hang together (at rest)

```
ApprovalStore (JSON)
  └── ApprovalRequest.metadata["plan_state"]  ← PlanExecutionState (resume context)
  └── ApprovalRequest.metadata["trace_id"]    ─────────────────────────────┐
                                                                            ▼
PlanStateStore (SQLite)                                          TraceStore (SQLite)
  └── plan_runs.plan_id  (primary key)                          └── traces.trace_id
  └── plan_runs.trace_id ────────────────────────────────────►  └── explainability.approval_id
  └── plan_runs.status                                                   │
  └── plan_runs.pending_approval_id ─────────────────────────► ApprovalStore.get_request(id)
```

Resume path (after restart):
1. `_get_approval_state()` → loads JSON → finds pending `ApprovalRequest`.
2. Operator calls `approve_plan_step(approval_id)`.
3. `record_decision()` → auto-saved to JSON.
4. `resume_plan()` reads `plan_state` from `approval_request.metadata` → reconstructs `ExecutionPlan` + prior `StepExecutionResult` list.
5. `orchestrator.execute_plan(start_step_index=N, existing_step_results=[...])` — no re-execution of prior steps.
6. Result upserted into `PlanStateStore`.

---

## 5. Boundaries consciously held in Phase N

| Item | Status |
|------|--------|
| Auto-save PerformanceHistoryStore on every update | **Deferred to Phase O** — write amplification not justified yet |
| TrainingDataset incremental persistence | **Deferred to Phase O** |
| TTL / archival for TraceStore | **Deferred to Phase O** |
| Redis / Postgres | **Out of scope** — local durable runtime is sufficient |
| Policy management UI | **Deferred to Phase O/P** |
| Replay / forensics API | **Deferred to Phase O** |
| Distributed cluster state | **Out of scope for Phase N** |

---

## 6. No parallel implementation was built

- `ApprovalStore` class code was **not changed** — only its wiring in `services/core.py`.
- `TraceStore` was **not changed** — no new tables added, no schema migration.
- `resume_plan()` was **not changed** — it already reads from `approval_request.metadata`.
- `orchestrator.py` was **not changed** — plan state embedding was already correct.
- The new `PlanStateStore` **follows the TraceStore pattern verbatim** — no new dependencies or patterns.
- `api_gateway/main.py` was **not changed** — it already delegates to `services/core.py`.
- The frontend was **not changed** — `list_recent_plans()` improvements are transparent to the API.

---

## 7. Suggested next phase

**Phase O — State Analytics and Management:**
- Auto-save `PerformanceHistoryStore` after online updates (with debounce or periodic flush).
- Add TTL / retention policy to `TraceStore` (DELETE rows older than N days).
- Add `PlanStateStore.delete_before(cutoff_date)` for plan pruning.
- Policy mutation API (CRUD for `PolicyRegistry`).
- Replay / forensics endpoint: given `plan_id`, reconstruct full decision trail from Trace + Approval + ExplainabilityRecords.

**Phase P — Distributed Runtime (future):**
- PostgreSQL backend for `TraceStore` / `PlanStateStore` for multi-process deployments.
- Distributed approval queue (message broker).
