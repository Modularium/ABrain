# Phase 5 – LearningOps L1: Canonical Training Data Schema

**Branch:** `codex/phase5-learningops-schema`  
**Date:** 2026-04-18  
**Roadmap step:** Phase 5, first deliverable — "Trainingsdaten-Schema für Decision-/Routing-Lernen definieren"

---

## 1. Scope

Define the canonical offline training data schema for LearningOps:

- `LearningRecord` — flat, denormalised Pydantic model capturing one routing
  decision and its downstream signals (approval outcome + execution outcome)
- `DatasetBuilder` — read-only assembler that joins TraceStore + ApprovalStore
  into a list of `LearningRecord` instances
- `DataQualityFilter` — configurable validation/filter layer that enforces
  data-quality rules before records reach training jobs

---

## 2. What already existed (idempotency check)

| Component | Status before this step |
|-----------|------------------------|
| `core/decision/learning/dataset.py` | Existed — `TrainingSample` for **online** neural policy updates |
| `core/decision/learning/persistence.py` | Existed — JSON save/load for online training data |
| `core/decision/learning/trainer.py` | Existed — `NeuralTrainer` for online batches |
| `core/decision/learning/online_updater.py` | Existed — records live executions |
| `core/decision/learning/reward_model.py` | Existed — scalar reward from execution result |
| `core/decision/learning/record.py` | **Did not exist** — created here |
| `core/decision/learning/dataset_builder.py` | **Did not exist** — created here |
| `core/decision/learning/quality.py` | **Did not exist** — created here |

The existing `TrainingSample` is designed for **online** learning from live
agent executions.  It encodes feature vectors and task embeddings computed
from live `AgentDescriptor` objects.  It is **not** a canonical offline schema.

`LearningRecord` fills the gap: it captures what happened (routing, approval,
outcome) from the canonical stores (TraceStore, ApprovalStore) in a flat,
training-job-agnostic format.

---

## 3. New files

### `core/decision/learning/record.py`

`LearningRecord(BaseModel)` with `extra="forbid"`:

- **Trace provenance:** `trace_id`, `workflow_name`, `task_type`, `task_id`,
  `started_at`, `ended_at`, `trace_status`
- **Routing decision:** `selected_agent_id`, `candidate_agent_ids`,
  `selected_score`, `routing_confidence`, `score_gap`, `confidence_band`,
  `policy_effect`, `matched_policy_ids`, `approval_required`
- **Approval outcome:** `approval_id`, `approval_decision`
- **Execution outcome:** `success`, `cost_usd`, `latency_ms`
- **Data-quality flags:** `has_routing_decision`, `has_outcome`,
  `has_approval_outcome` — set by `DatasetBuilder`, never by callers
- `quality_score() -> float` — fraction of quality flags that are True

### `core/decision/learning/dataset_builder.py`

`DatasetBuilder(trace_store, approval_store=None)`:

- `build(limit=1000) -> list[LearningRecord]`
- Reads `list_recent_traces(limit)` from TraceStore
- For each trace: fetches snapshot, maps first explainability record to
  routing fields, joins ApprovalStore for approval outcome, extracts outcome
  signals from trace metadata
- **Read-only** — never mutates either store
- Works without an ApprovalStore (approval fields left `None`)

### `core/decision/learning/quality.py`

`DataQualityFilter` with configurable rules:

- `require_routing_decision` (default: True)
- `require_outcome` (default: False)
- `require_approval_outcome` (default: False)
- `min_quality_score` (default: 0.0)
- `validate(record) -> list[QualityViolation]`
- `filter(records) -> list[LearningRecord]`
- `filter_with_report(records) -> (accepted, rejected_with_violations)`

`QualityViolation` is a frozen dataclass with `field` and `reason`.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel implementation | ✅ — `LearningRecord` is a new type; `TrainingSample` is unchanged and still used by online neural policy |
| No second runtime/router/orchestrator | ✅ — no runtime changes |
| No business logic in CLI/UI/API layer | ✅ — all logic in `core/decision/learning/` |
| No new shadow truth | ✅ — reads from canonical TraceStore and ApprovalStore only |
| Only additive changes | ✅ — new files only, no existing file logic modified (only `__init__.py` exports extended) |
| Offline vs online separation maintained | ✅ — `LearningRecord` / `DatasetBuilder` / `DataQualityFilter` are for offline use only |
| No heavy new dependencies | ✅ — only stdlib + pydantic |

---

## 5. Tests

**File:** `tests/decision/test_learningops_schema.py`  
**Count:** 23 tests (unit, no I/O except tmp SQLite)

Coverage:
- `LearningRecord`: schema validation, extra-field rejection, quality score calculation
- `DataQualityFilter`: each rule individually, combined filter, `filter_with_report`, frozen violation
- `DatasetBuilder`: empty store, invalid limit, trace without explainability, trace with routing, outcome metadata, approval join, no-approval-store path, limit enforcement, read-only guarantee

**Full suite:** 708 passed, 1 skipped — all green.

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (L1 schema only) | ✅ |
| No parallel structure | ✅ |
| Canonical store paths used (TraceStore, ApprovalStore) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green (23/23 new + 708/708 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Next step after merge

**Phase 5 – L2:** `DatasetExporter` — serialize a filtered list of
`LearningRecord` instances to JSONL / Parquet for offline training jobs, with
versioning (timestamp + schema-version field in the exported file header).
