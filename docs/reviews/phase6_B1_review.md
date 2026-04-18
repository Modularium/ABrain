# Phase 6 – Brain v1 B6-S1: State Representation and Target Variable Schema

**Branch:** `codex/phase6-brain-v1-state-schema`  
**Date:** 2026-04-18  
**Roadmap task opened:** "Phase 6 – Brain v1: Zielvariablen und Zustandsrepräsentation definieren"

---

## 1. Scope

Define the canonical input/output schema for the Brain decision network and
the encoder that converts existing ABrain routing primitives into that schema.
No neural network is introduced here — this step establishes the typed
foundation that the network, trainer, and shadow runner will build on.

New module: `core/decision/brain/` (new subpackage, additive only)

### Deliverables

| Symbol | File | Role |
|--------|------|------|
| `BrainBudget` | `state.py` | Budget constraints (USD, time, max_agents) |
| `BrainPolicySignals` | `state.py` | Policy match and approval gate signals |
| `BrainAgentSignal` | `state.py` | Per-candidate feature snapshot |
| `BrainState` | `state.py` | Complete network input (task + budget + policy + candidates) |
| `BrainTarget` | `state.py` | Supervision targets (selection + execution outcome) |
| `BrainRecord` | `state.py` | (state, target) training pair with trace provenance |
| `BrainStateEncoder` | `encoder.py` | Converts `TaskIntent` + `AgentDescriptor[]` + `PerformanceHistoryStore` → `BrainState` |

---

## 2. Idempotency check

| Component | Status before B6-S1 |
|-----------|-------------------|
| `core/decision/brain/` | **Did not exist** |
| Any Brain v1 state schema | Not found in codebase |
| `TaskIntent`, `AgentDescriptor`, `PerformanceHistoryStore` | ✅ on main — **reused unmodified** |
| `RoutingDecision` | ✅ on main — **reused unmodified** |
| `ShadowEvaluator` | ✅ on main (L5) — **integration layer for B6-S3+** |

---

## 3. Design

### BrainState — network input

`BrainState` captures all signals available *before* a routing decision is
finalised.  It is divided into four groups:

| Group | Fields | Source |
|-------|--------|--------|
| Task features | `task_type`, `domain`, `risk`, `required_capabilities`, `num_required_capabilities`, `description` | `TaskIntent` |
| Budget | `BrainBudget` (budget_usd, time_budget_ms, max_agents) | caller-supplied |
| Policy | `BrainPolicySignals` (has_policy_effect, approval_required, matched_policy_ids) | caller-supplied |
| Candidates | `list[BrainAgentSignal]`, `num_candidates` | `AgentDescriptor[]` + `PerformanceHistoryStore` |
| Routing confidence | `routing_confidence`, `score_gap`, `confidence_band` | optional `RoutingDecision` |

The `candidates` list is ordered best-first: by neural policy score when a
`RoutingDecision` is provided, otherwise by capability match score descending.

### BrainAgentSignal — per-candidate features

| Feature | Type | Derivation |
|---------|------|-----------|
| `capability_match_score` | `float [0,1]` | Required ∩ agent caps / required |
| `success_rate` | `float [0,1]` | `PerformanceHistoryStore` |
| `avg_latency_s` | `float ≥ 0` | `PerformanceHistoryStore.avg_latency` |
| `avg_cost_usd` | `float ≥ 0` | `PerformanceHistoryStore.avg_cost` |
| `recent_failures` | `int ≥ 0` | `PerformanceHistoryStore` |
| `execution_count` | `int ≥ 0` | `PerformanceHistoryStore` |
| `load_factor` | `float [0,1]` | `PerformanceHistoryStore` |
| `trust_level_ord` | `float [0,1]` | ordinal: UNKNOWN=0, SANDBOXED=1/3, TRUSTED=2/3, PRIVILEGED=1 |
| `availability_ord` | `float [0,1]` | ordinal: OFFLINE=0, DEGRADED=1/3, UNKNOWN=0.5, ONLINE=1 |

### BrainTarget — supervision targets

All fields are nullable — absent means "not observed for this trace".

| Field | Meaning |
|-------|---------|
| `selected_agent_id` | Agent actually chosen by production router |
| `outcome_success` | Execution succeeded / failed |
| `outcome_cost_usd` | Actual cost incurred |
| `outcome_latency_ms` | End-to-end latency |
| `approval_required` | Approval gate triggered |
| `approval_granted` | Approval outcome (None = no flow) |

### BrainRecord — training pair

`BrainRecord(trace_id, workflow_name, schema_version="1.0", state, target)` —
immutable, JSON-serialisable via `model_dump(mode="json")`.  Written by the
`BrainRecordBuilder` introduced in B6-S2.

### BrainStateEncoder — conversion layer

```python
encoder = BrainStateEncoder()
state = encoder.encode(
    intent,
    descriptors,
    performance_history,
    routing_decision=decision,   # optional
    budget=budget,               # optional
    policy=policy,               # optional
)
```

The encoder is read-only and stateless.  It reuses `PerformanceHistoryStore`
to get per-agent history and falls back to descriptor metadata when no runtime
history is available (consistent with `FeatureEncoder` behaviour).

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel production router | ✅ — encoder is read-only, no routing logic |
| No second TraceStore | ✅ — no TraceStore dependency at all |
| No modification of production RoutingDecision | ✅ — only read from it |
| No business logic in wrong layer | ✅ — all in `core/decision/brain/` |
| No new heavy dependencies | ✅ — stdlib + pydantic only |
| Additive only | ✅ — new subpackage; nothing in existing modules touched |

---

## 5. Tests

**File:** `tests/decision/test_brain_state_schema.py`  
**Count:** 46 tests (unit, no I/O)

Coverage by class:

| Test class | Tests | Coverage |
|-----------|-------|---------|
| `TestBrainBudget` | 4 | defaults, extra rejection, non-negative, max_agents ≥ 1 |
| `TestBrainPolicySignals` | 3 | defaults, extra rejection, policy_ids stored |
| `TestBrainAgentSignal` | 3 | extra rejection, cap score clamped, valid roundtrip |
| `TestBrainState` | 3 | extra rejection, sensible defaults, empty task_type |
| `TestBrainTarget` | 3 | all-None defaults, extra rejection, cost non-negative |
| `TestBrainRecord` | 3 | schema_version default, extra rejection, JSON roundtrip |
| `TestOrdinalMappings` | 6 | trust and availability ordinal ordering |
| `TestBrainStateEncoderBasic` | 8 | BrainState type, field copying, counts, budget/policy passthrough, no-routing defaults |
| `TestBrainStateEncoderWithRoutingDecision` | 4 | confidence fields, candidate ordering, cap_match from decision, confidence_band |
| `TestBrainStateEncoderAgentSignals` | 9 | trust/availability ordinals, perf history, cap match 0/0.5/1.0, sort without decision |

**Full suite:** 1354 passed, 1 skipped — all green.

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (schema + encoder only, no network) | ✅ |
| No production path touched | ✅ |
| No second router, store, or registry | ✅ |
| All Pydantic models use `extra="forbid"` | ✅ |
| Ordinal encodings semantically correct (higher = more desirable) | ✅ |
| Encoder read-only and deterministic | ✅ |
| Tests green (46/46 new + 1354/1354 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Next step

**B6-S2 – BrainRecordBuilder**: reads `LearningRecord` objects (from the
Phase 5 LearningOps pipeline) and converts them to `BrainRecord` training
pairs using `BrainStateEncoder` — closing the feedback loop from trace data
to Brain training material.
