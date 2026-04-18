# Phase 6 – Brain v1 B6-S2: BrainRecordBuilder

**Branch:** `codex/phase6-brain-v1-record-builder`  
**Date:** 2026-04-18  
**Roadmap task:** "Trainingsziele definieren — bridge from LearningOps data to Brain training pairs"

---

## 1. Scope

Convert ``LearningRecord`` objects (Phase 5 LearningOps pipeline) into
``BrainRecord`` training pairs for the Brain decision network.

New file: `core/decision/brain/record_builder.py`  
Updated: `core/decision/brain/__init__.py` (adds `BrainRecordBuilder` to `__all__` + lazy import)

---

## 2. Idempotency check

| Component | Status before B6-S2 |
|-----------|-------------------|
| `record_builder.py` | **Did not exist** |
| `BrainRecord`, `BrainState`, `BrainTarget` | ✅ on main (B6-S1) — **reused** |
| `LearningRecord` | ✅ on main (P5-L1) — **read-only input** |
| `PerformanceHistoryStore` | ✅ on main — **reused** |

---

## 3. Design

### LearningRecord → BrainRecord mapping

A `LearningRecord` is a post-hoc flat snapshot.  It contains routing *results*
but not the full routing *context* (AgentDescriptor list, TaskIntent details,
capabilities, descriptor-level trust/availability).  The builder uses a
best-effort approach with documented neutral defaults for irrecoverable signals:

| Signal | Source | Default when absent |
|--------|--------|-------------------|
| `task_type` | `record.task_type` | `"unknown"` |
| `domain` | — not in LearningRecord — | `"unknown"` |
| `required_capabilities` | — not in LearningRecord — | `[]` |
| `routing_confidence` | `record.routing_confidence` | `None` |
| `score_gap` | `record.score_gap` | `None` |
| `confidence_band` | `record.confidence_band` | `None` |
| `policy.has_policy_effect` | `record.policy_effect is not None` | `False` |
| `policy.approval_required` | `record.approval_required` | — |
| `policy.matched_policy_ids` | `record.matched_policy_ids` | — |
| `capability_match_score` | — not in LearningRecord — | `0.0` (all candidates) |
| `trust_level_ord` | — not in LearningRecord — | `0.0` (UNKNOWN ordinal) |
| `availability_ord` | — not in LearningRecord — | `0.5` (UNKNOWN ordinal) |
| Per-agent performance signals | `PerformanceHistoryStore.get(agent_id)` | neutral defaults |

### Candidate ordering

The `selected_agent_id` is placed first in the candidate list.  If it is
absent from `candidate_agent_ids`, it is prepended.  This preserves the
production selection signal in a consistent position without modifying the
`BrainTarget.selected_agent_id` field.

### Approval decoding

`BrainTarget.approval_granted`:
- `True` when `has_approval_outcome=True` and `approval_decision == "approved"`
- `False` when `has_approval_outcome=True` and `approval_decision == "rejected"`
- `None` otherwise (no approval flow, or outcome not yet resolved)

### Guard: `require_routing_decision`

Default `True` — refuses to build a `BrainRecord` from a `LearningRecord`
without routing decision data, since such a record carries no actionable
routing signal.  Settable to `False` for use cases that accept weaker records.

### `build_batch`

Batch conversion with `skip_invalid=True` (default) silently drops records
that fail conversion (routing guard or Pydantic validation).  With
`skip_invalid=False`, the first error propagates — useful for strict pipeline
validation.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel production router | ✅ — read-only conversion, no routing |
| No second TraceStore | ✅ — no TraceStore dependency |
| No mutation of LearningRecord | ✅ — purely functional |
| No business logic in wrong layer | ✅ — all in `core/decision/brain/` |
| No new heavy dependencies | ✅ — only existing canonical components |
| Additive only | ✅ — one new file + `__init__.py` extension |

---

## 5. Tests

**File:** `tests/decision/test_brain_record_builder.py`  
**Count:** 52 tests (unit, no I/O)

| Test class | Tests | Focus |
|-----------|-------|-------|
| `TestBrainRecordBuilderBuild` | 8 | type contract, trace fields, routing guard |
| `TestBrainStatePopulation` | 10 | task_type, domain default, routing signals, candidates count |
| `TestPolicySignals` | 6 | policy_effect mapping, approval_required, matched_policy_ids |
| `TestAgentSignals` | 11 | candidate ordering, capability_match=0.0, sentinel ordinals, perf history, edge cases |
| `TestBrainTargetPopulation` | 11 | selection, outcome, approval_granted decoding |
| `TestBrainRecordBuilderBatch` | 7 | empty, valid batch, skip_invalid, raise mode, order, JSON roundtrip |

**Full suite:** 1406 passed, 1 skipped — all green.

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (conversion only, no routing/training) | ✅ |
| No production path touched | ✅ |
| No second router, store, or registry | ✅ |
| LearningRecord read-only | ✅ |
| Neutral defaults documented in code | ✅ |
| Tests green (52/52 new + 1406/1406 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Next step

**B6-S3 – Brain offline trainer**: loads exported JSONL datasets of
`BrainRecord` objects, converts them to a flat feature matrix, and runs a
training pass using the existing `NeuralPolicyModel` / `MLPScoringModel`
infrastructure — producing a Brain model artefact that can be registered in
`ModelRegistry` and evaluated via `ShadowEvaluator`.
