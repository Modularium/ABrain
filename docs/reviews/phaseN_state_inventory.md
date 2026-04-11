# Phase N — Persistent State Inventory

**Date:** 2026-04-11  
**Branch:** `codex/phaseN-persistent-state`  
**Scope:** Identify all existing state and persistence surfaces in ABrain, rate their durability, and define which are canonical and which have restart gaps.

---

## 1. Existing State / Persistence Surfaces

### 1.1 TraceStore — `core/audit/trace_store.py`

| Attribute | Value |
|-----------|-------|
| Backend | SQLite (`runtime/abrain_traces.sqlite3` via `ABRAIN_TRACE_DB_PATH`) |
| Schema | `traces`, `spans`, `explainability` tables with FK relationships |
| Auto-persist | Yes — every write is committed immediately |
| Restart-safe | **Yes** — durable by design |
| Canonical | **Yes** — the authoritative audit and explainability surface |

**Assessment:** Already the most robust store in the codebase. Correctly wired in `_get_trace_state()` in `services/core.py`. Default path falls back gracefully if creation fails (logged warning). No changes needed to the core schema.

**Gap:** No explicit index on `(workflow_name, started_at)` for plan-filtered queries. Minor optimisation only — not a blocker.

---

### 1.2 ApprovalStore — `core/approval/store.py`

| Attribute | Value |
|-----------|-------|
| Backend | In-memory `dict[str, ApprovalRequest]` + optional JSON file |
| Auto-persist | Yes **if** `path` is provided to constructor |
| Restart-safe | **NO** — `_get_approval_state()` in `services/core.py` constructs `ApprovalStore()` with **no path** |
| Canonical | **Yes** — the authoritative pending-approval and decision surface |

**Assessment:** The store class itself supports JSON persistence via `save_json` / `load_json` and auto-saves when a `path` is provided. The critical gap is that `services/core.py` never passes a path, making it purely in-memory. All pending approvals are **lost on restart**, which breaks the resume flow entirely.

**Gap (BLOCKER):** Wire `_get_approval_state()` to an environment-configurable path (`ABRAIN_APPROVAL_STORE_PATH`, default `runtime/abrain_approvals.json`) and load from disk on startup.

---

### 1.3 PlanExecutionState — `core/orchestration/result_aggregation.py`

| Attribute | Value |
|-----------|-------|
| Backend | Embedded as `metadata["plan_state"]` inside `ApprovalRequest` |
| Auto-persist | **Only if** ApprovalStore is persisted |
| Restart-safe | **NO** — inherits ApprovalStore's restart gap |
| Canonical | Yes — `resume.py` reads plan, state, decision from `approval_request.metadata` |

**Assessment:** The plan serialisation is correct — `PlanExecutionState`, `ExecutionPlan`, and completed `StepExecutionResult` are all Pydantic models with `model_dump(mode="json")` serialisation. Once ApprovalStore is wired to disk, paused plan state survives restart automatically.

**Additional gap:** There is no queryable store for *completed* plan results. Completed plans can only be found by scanning `traces` for `workflow_name == "run_task_plan"`. A dedicated `plan_runs` table makes plan-level queries O(1) instead of O(recent-traces × 5).

---

### 1.4 PerformanceHistoryStore — `core/decision/performance_history.py`

| Attribute | Value |
|-----------|-------|
| Backend | In-memory `dict[str, AgentPerformanceHistory]` + `save_json` / `load_json` |
| Auto-persist | **No** — save is never called automatically |
| Restart-safe | **No** — reset to zero on every process start |
| Canonical | Yes — feeds the neural policy scoring model |

**Assessment:** The class has persistence primitives but they are never wired. `_get_learning_state()` in `services/core.py` creates a fresh `TrainingDataset()` and `PerformanceHistoryStore()` from scratch every time. After restart the routing engine starts with no history.

**Gap:** Wire `_get_learning_state()` to load PerformanceHistoryStore from `ABRAIN_PERF_HISTORY_PATH` (default `runtime/abrain_perf_history.json`) on startup.

---

### 1.5 Learning Dataset / Neural Policy Weights — `core/decision/learning/persistence.py`

| Attribute | Value |
|-----------|-------|
| Backend | JSON file (`save_dataset` / `load_dataset`) + model weights file |
| Auto-persist | **No** — functions exist but never called from `services/core.py` |
| Restart-safe | **No** — training state reset on restart |
| Canonical | Yes — `NeuralTrainer` uses these to train the routing policy |

**Assessment:** Persistence helpers exist and are correct. `_get_learning_state()` creates a fresh `TrainingDataset()` without consulting disk. Wiring load-on-startup for the dataset is low-risk. Auto-saving the training dataset after online updates requires a hook into `OnlineUpdater` — deferred to Phase O.

**Gap (minor):** Wire dataset load-on-startup from `ABRAIN_TRAINING_DATASET_PATH`. Do NOT add ML-data-lake semantics.

---

### 1.6 PlanStateStore — DOES NOT EXIST YET

**Gap:** There is no dedicated SQLite table for plan execution results. Completed, rejected, and denied plans are discoverable only through trace scans. A `plan_runs` table makes plan-level state a first-class queryable artifact.

**Action:** Create `core/orchestration/state_store.py` — a SQLite store that upserts `PlanExecutionResult` rows keyed by `plan_id`. Same pattern as `TraceStore`. Single DB path (`runtime/abrain_plan_state.sqlite3` via `ABRAIN_PLAN_STATE_DB_PATH`).

---

### 1.7 GovernanceState / PolicyRegistry — `core/governance/`

| Attribute | Value |
|-----------|-------|
| Backend | Optional YAML/JSON file via `ABRAIN_POLICY_PATH` |
| Auto-persist | Stateless — policies are loaded at startup, never mutated at runtime |
| Restart-safe | **Yes** — loaded from disk each startup if path is configured |
| Canonical | Yes |

**Assessment:** Already restart-safe for read-only policy evaluation. No changes needed.

---

### 1.8 Memory Store — `core/memory_store.py`

Not examined in depth — out of scope for Phase N. Phase N focuses on execution-critical state (approvals, plans, traces).

---

## 2. Summary: Restart Gaps

| Surface | Gap | Priority |
|---------|-----|----------|
| ApprovalStore | No persistent path wired | **BLOCKER** — breaks resume |
| PlanExecutionState | Tied to ApprovalStore gap | **BLOCKER** (follows from above) |
| PlanStateStore | Does not exist | **HIGH** — plan queries O(N) today |
| PerformanceHistoryStore | Load not wired on startup | **MEDIUM** — routing starts cold |
| TrainingDataset | Load not wired on startup | **LOW** — only affects routing quality |
| TraceStore | None | Already durable |
| PolicyRegistry | None | Already restart-safe |

---

## 3. Canonical Path Forward

The following changes are canonical evolutions of existing code — no new parallel systems:

1. **Wire `ApprovalStore` to disk** in `_get_approval_state()` — one-line path fix.
2. **Add `PlanStateStore`** in `core/orchestration/state_store.py` — follows the exact `TraceStore` pattern.
3. **Wire `PlanStateStore`** in `_get_plan_state_store()` in `services/core.py`.
4. **Persist plan results** in `run_task_plan()` and `_decide_plan_step()`.
5. **Wire `PerformanceHistoryStore` load** in `_get_learning_state()`.
6. **Update `list_recent_plans()`** to query `PlanStateStore` first (faster, correct).

### What is NOT built:
- No second SQLite DB running alongside the trace DB for approval state (JSON file is sufficient).
- No event-sourcing or distributed workflow engine.
- No Redis or Postgres dependency.
- No ML data lake or training pipeline automation.
- No new API or frontend surface.
