# Phase S11 — Replay Harness & Compliance Regression Baselines

**Branch:** `codex/phaseS11-replay-compliance-regression`
**Date:** 2026-04-15
**Reviewer:** automated phase gate

---

## Goal

Build a controlled evaluation layer on top of the existing ABrain
`TraceStore`/`RoutingEngine`/`PolicyEngine` canonical stack that allows:

1. Dry-run routing replay: re-route a stored trace against the current agent
   catalog and compare outcomes.
2. Policy compliance checking: re-evaluate stored traces against the current
   governance rules and detect regressions.
3. Regression baseline metrics: batch-compute health indicators across recent
   traces to establish reproducible baselines.

All three capabilities are **read-only and non-executing** — no live actions,
no new trace records, no approval creation.

---

## What changed

### `core/evaluation/` — new canonical evaluation module

Three files added:

#### `core/evaluation/__init__.py`
Public re-exports of `TraceEvaluator`, all result models, and both verdict
enums.

#### `core/evaluation/models.py`

| Model | Purpose |
|-------|---------|
| `RoutingReplayVerdict` | `exact_match` / `acceptable_variation` / `regression` / `non_replayable` |
| `RoutingReplayResult` | Per-step routing comparison: stored vs current selection + metrics |
| `PolicyReplayVerdict` | `compliant` / `tightened` / `regression` / `non_evaluable` |
| `PolicyReplayResult` | Per-step policy comparison: stored vs current effect + approval consistency |
| `StepEvaluationResult` | Combined routing + policy result for one stored explainability step |
| `TraceEvaluationResult` | Full evaluation of one stored trace: all steps + regression flags |
| `BatchEvaluationReport` | Aggregate baseline metrics over a batch of traces |

All models are `extra="forbid"` Pydantic BaseModels.  All fields have safe
defaults.

`classify_policy_delta(stored, current) → PolicyReplayVerdict` is a module-level
pure function implementing the strictness ordering:

```
allow(0) < require_approval(1) < deny(2)

current > stored  →  TIGHTENED   (safer; not a regression)
current < stored  →  REGRESSION  (more permissive; risky)
current == stored →  COMPLIANT
```

#### `core/evaluation/harness.py`

`TraceEvaluator` — the single canonical evaluation entry point.

```python
evaluator = TraceEvaluator(
    trace_store,        # canonical TraceStore — read-only
    routing_engine,     # dry-run only: route_intent() called, no execution
    policy_engine,      # dry-run only: evaluate() called, no side effects
    agent_descriptors=descriptors,  # live agent catalog for current routing
)
result  = evaluator.evaluate_trace("trace-abc123")    # → TraceEvaluationResult
baselines = evaluator.compute_baselines(limit=100)    # → BatchEvaluationReport
```

##### Routing dry-run (per step)

1. Extract `task_type` and `required_capabilities` from the stored
   `ExplainabilityRecord.metadata` (flat format, with legacy nested fallback).
2. If `task_type` is missing or no agent descriptors available → `NON_REPLAYABLE`.
3. Otherwise: build a minimal `TaskIntent` (domain=`"analysis"`, risk=`MEDIUM`
   as safe defaults) and call `routing_engine.route_intent(intent, descriptors)`.
4. Compare `stored_agent_id` vs `current_agent_id`.

Verdict rules:
- Same agent → `EXACT_MATCH`
- Different agent, same confidence band → `ACCEPTABLE_VARIATION`
- Different agent, confidence delta ≤ 0.15 → `ACCEPTABLE_VARIATION`
- Otherwise → `REGRESSION`

##### Policy compliance dry-run (per step)

1. Skip if `policy_effect is None AND matched_policy_ids == []` (no stored policy
   signal — returns `None`).
2. Extract `task_type` + `required_capabilities` from metadata (same dual-format
   fallback as routing).
3. If `task_type` missing → `NON_EVALUABLE`.
4. Build `TaskIntent` and reconstruct `PolicyEvaluationContext` via
   `policy_engine.build_execution_context()` (current agent descriptor from live
   catalog if available).
5. Call `policy_engine.evaluate(intent, agent_descriptor, context)`.
6. Compare stored vs current `effect` via `classify_policy_delta()`.
7. Also check `approval_required` consistency.

##### Regression flag semantics

| Flag | Meaning |
|------|---------|
| `has_routing_regression` | Any step has `REGRESSION` routing verdict |
| `has_policy_regression` | Any step has `REGRESSION` policy verdict |
| `has_any_regression` | Either of the above |

A `TIGHTENED` policy change is **not** a regression — it is a safer outcome.

### `services/core.py` — two new public helpers

```python
evaluate_trace(trace_id: str) → dict | None
compute_evaluation_baselines(*, limit: int = 100) → dict
```

Both build a `TraceEvaluator` from the same process-local runtime state used by
`run_task` and `run_task_plan`, then return `model_dump(mode="json")` dicts.
No new global state; no new engine instances beyond what the runtime already
holds.

### `scripts/abrain_control.py` — thin CLI surface

New subcommands:

```
abrain trace replay <trace_id>     # dry-run routing comparison for one trace
abrain compliance check <trace_id> # policy compliance check for one trace
abrain compliance baselines [--limit N]  # batch baseline metrics
```

All three are read-only, display results via existing `_emit()` helper, and
support `--json` for machine-readable output.

### `tests/core/test_evaluation_harness.py` — 29 new unit tests

Categories:
- `classify_policy_delta` pure function (8 cases)
- `_classify_routing_verdict` pure function (7 cases)
- `TraceEvaluator.evaluate_trace()` (9 cases: exact match, routing regression,
  policy regression, tightened, non-replayable, no execution, old records,
  no policy signal, approval consistency)
- `TraceEvaluator.compute_baselines()` (6 cases: empty store, single trace,
  mixed results, rates calculation, avg confidence, no side effects)
- Model and export tests (3 cases)

---

## Baseline metrics now available

| Metric | How computed |
|--------|-------------|
| `routing_match_rate` | `exact_match / (exact + variation + regression)` |
| `policy_compliance_rate` | `compliant / (compliant + tightened + regression)` |
| `approval_consistency_rate` | `consistent / (consistent + inconsistent)` |
| `avg_routing_confidence` | mean of stored `routing_confidence` values |
| `confidence_band_distribution` | counts per `"high"/"medium"/"low"` |
| `traces_with_regression` | traces where `has_any_regression=True` |

---

## Architecture check

### 1. No parallel implementation
`core/evaluation/` is a new module that wraps existing canonical engines.  It
does not duplicate any decision, governance, or audit logic.  There is still
one `RoutingEngine`, one `PolicyEngine`, and one `TraceStore`.

### 2. TraceStore remains the only audit/trace truth
`TraceEvaluator` reads from `TraceStore` via `get_trace()` and
`list_recent_traces()`.  No writes.  No second store.

### 3. No second replay/compliance world
The evaluation layer calls the same `route_intent()` and `evaluate()` methods
that the live pipeline uses — it is a controlled second call with stored inputs,
not a fork of the implementation.

### 4. No execution bypass
`RoutingEngine.route_intent()` is a pure decision function — it returns a
`RoutingDecision` without triggering any adapter, tool, or external service.
`PolicyEngine.evaluate()` is also a pure decision function.  Neither of these
functions creates approvals, writes traces, or calls external systems.

### 5. No approval bypass
No `ApprovalStore` interaction at all.  The policy evaluation produces a
`PolicyDecision`, and `has_any_regression` is computed from comparing stored vs
current decision values.  No approval is created, cancelled, or bypassed.

### 6. Value is additive
After S11, operators can answer:
- "Did last week's routing decisions still hold against today's agent catalog?"
- "Has any policy change inadvertently loosened access controls?"
- "What is our approval consistency across recent traces?"
- "What fraction of stored traces are exact-match replayable?"

---

## What follows from S11

- **S12 / Phase 1 exit**: add CI gates that fail if `has_any_regression=True`
  across a batch of golden-set traces. This converts the evaluation layer into
  a formal regression guard for policy and routing changes.
- **UI**: `replay_descriptor` + `TraceEvaluationResult` are already in
  TypeScript types; a trace detail panel can show the replay badge and
  step-level verdicts.
- **Phase 2**: per-tool / per-adapter compliance checks can reuse
  `classify_policy_delta` directly.

---

## Tests

**S11 tests only:** 29 passed, 0 failed  
**Full suite:** 381 passed, 1 skipped (pre-existing), 0 failures

---

## Merge-readiness

| Check | Status |
|-------|--------|
| No parallel implementation | PASS |
| Canonical engines reused | PASS |
| TraceStore single source of truth | PASS |
| No execution side effects | PASS |
| No approval bypass | PASS |
| All new tests green | PASS |
| Full suite green | PASS |
| Scope matches roadmap Phase 1 | PASS |

**Merge-ready: YES**
