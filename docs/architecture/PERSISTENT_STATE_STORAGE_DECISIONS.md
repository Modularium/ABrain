# Persistent State — Storage Decisions

**Phase:** N  
**Date:** 2026-04-11

---

## Decision 1: Keep SQLite for trace and plan state; JSON file for approvals

**Options considered:**
1. SQLite for everything (traces, plans, approvals)
2. JSON files for everything
3. SQLite for traces + plans, JSON for approvals ← **chosen**

**Reasoning:**

- `TraceStore` is already SQLite. Switching it would break backward compatibility.
- `ApprovalStore` already has a proven JSON persistence path (`save_json` / `load_json` / `_auto_save`). Migrating it to SQLite would require schema migration logic with no benefit — approval volumes are low (100s, not millions).
- `PlanStateStore` benefits from SQL-level indexing for status and recency queries. SQLite is the right fit.
- No Redis or Postgres dependency: both require external services and operational overhead that is not justified at this scale.

**Conclusion:** Extend existing patterns. Do not introduce a second SQLite file for approvals.

---

## Decision 2: One SQLite file per store, not one shared DB

**Options considered:**
1. One shared `abrain.db` with all tables
2. Separate files per store ← **chosen**

**Reasoning:**

- `TraceStore` and `PlanStateStore` are independently initialised and have independent failure modes.
- A shared DB means a schema migration failure in one store blocks the other.
- Separate files allow independent backup, rotation, and TTL policies.
- SQLite WAL mode is process-safe when files are not shared across processes.

**Files:**
| Store | Default path | Env var |
|-------|-------------|---------|
| TraceStore | `runtime/abrain_traces.sqlite3` | `ABRAIN_TRACE_DB_PATH` |
| PlanStateStore | `runtime/abrain_plan_state.sqlite3` | `ABRAIN_PLAN_STATE_DB_PATH` |

---

## Decision 3: JSON file for ApprovalStore

**Reasoning:**

- Approval payload sizes are bounded (a few KB per request).
- Approval volume is low — human approvals require human latency.
- The existing `ApprovalStore` already writes atomically via `target.write_text(...)` — sufficient for single-process use.
- No concurrent writers expected (one process holds the store).

**File:**
| Store | Default path | Env var |
|-------|-------------|---------|
| ApprovalStore | `runtime/abrain_approvals.json` | `ABRAIN_APPROVAL_STORE_PATH` |

---

## Decision 4: JSON file for PerformanceHistoryStore (load only in Phase N)

**Reasoning:**

- Load-on-startup gives the routing engine warm priors after restart.
- Write-on-every-update would add significant I/O overhead (every task completion triggers an update).
- Explicit save (Phase O or via management API) is the right boundary.
- No new ORM or migration tooling needed.

**File:**
| Store | Default path | Env var |
|-------|-------------|---------|
| PerformanceHistoryStore | `runtime/abrain_perf_history.json` | `ABRAIN_PERF_HISTORY_PATH` |
| TrainingDataset | `runtime/abrain_training_dataset.json` | `ABRAIN_TRAINING_DATASET_PATH` |

---

## Decision 5: Plan state embedded in ApprovalRequest is canonical for paused plans

**Reasoning:**

The existing `resume.py` reads `plan`, `state`, and `decision` from `approval_request.metadata`. This coupling is intentional — it ensures the resume path has exactly the state it needs. Duplicating plan state into a separate table for paused plans would create two truths.

The `PlanStateStore` stores the `PlanExecutionResult` (aggregate result object) — it does NOT replace the plan state embedded in the approval. The relationship is:

- **Paused plan resume path:** ApprovalStore (has embedded plan_state) → `resume_plan()` → PlanStateStore (updated after resume)
- **Plan result query path:** PlanStateStore (first) → TraceStore scan (fallback)

---

## Decision 6: No new API surface or frontend changes in Phase N

**Reasoning:**

- The `api_gateway/main.py` control-plane endpoints already delegate to `services/core.py`.
- `list_recent_plans()` in `services/core.py` will transparently use the new `PlanStateStore` — no gateway changes needed.
- The frontend reads plans through the existing `/control-plane/plans` endpoint — no UI changes needed.
- Introducing new endpoints for "plan state management" would duplicate the existing approval endpoints.
