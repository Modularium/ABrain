# Phase 6 – Brain v1 B6-S5: Brain-vs-Heuristic Baseline Aggregator

**Branch:** `codex/phase6-brain-v1-baseline-eval`
**Date:** 2026-04-19
**Roadmap task:** *Phase 6 / "Brain-v1 gegen heuristische Baseline evaluieren"* — closes the Phase 6 loop by giving operators a structured, threshold-driven verdict over recorded shadow evaluations.

---

## 1. Scope

Aggregate `brain_shadow_eval` spans (written by `BrainShadowRunner` in B6-S4)
from the canonical `TraceStore` into a structured comparison report:

- overall metrics (`agreement_rate`, mean / median `score_divergence`, mean
  `top_k_overlap`, sample/coverage counts);
- per-version and per-workflow breakdowns;
- a threshold-based promotion recommendation (`promote` / `observe` /
  `reject`) with an explicit reason string.

Read-only against `TraceStore` — no writes, no second store, no model loading.

New file: `core/decision/brain/baseline_aggregator.py`
Updated: `core/decision/brain/__init__.py`

---

## 2. Idempotency check

| Component | Status before B6-S5 |
|-----------|-------------------|
| `baseline_aggregator.py` in `brain/` | **Did not exist** |
| Anything reading `brain_shadow_eval` spans into a report | **Did not exist** |
| `BrainShadowRunner` emits `brain_shadow_eval` spans | ✅ on main (B6-S4) — **read-only input** |
| `TraceStore.list_recent_traces` / `get_trace` | ✅ on main — **canonical reader** |
| `ModelRegistry.register_brain` / `model_kind="brain_v1"` | ✅ on main (B6-S4) — provides `version_id` axis |

No parallel aggregator existed — additive single-file step.

---

## 3. Design

### Pipeline

```
list_recent_traces(trace_limit)
  → for each trace: get_trace(trace_id)
  → spans where span_type == "brain_shadow_eval"
  → _summary_from_span(attrs) → BrainShadowEvalSummary | None
  → optional workflow_filter / version_filter
  → _compute_metrics(...) overall + grouped per version_id, workflow_name
  → _recommend(overall) → (label, reason)
  → BrainBaselineReport
```

### Pydantic schema (all `extra="forbid"`)

| Type | Purpose |
|------|---------|
| `BrainShadowEvalSummary` | flattened span row used for aggregation |
| `BrainBaselineMetrics` | metrics for one slice (overall or grouped) |
| `BrainBaselineReport` | full report with overall + breakdowns + recommendation |

### Recommendation logic

| Condition | Verdict |
|-----------|---------|
| `sample_count == 0` | `observe` — "no brain_shadow_eval spans found" |
| `sample_count ≥ min_samples_for_reject` AND `agreement_rate < reject_agreement_below` | **`reject`** |
| `sample_count < min_samples_for_promote` | `observe` — not enough samples |
| `agreement_rate < min_agreement_for_promote` | `observe` — agreement too low |
| `mean_score_divergence > max_divergence_for_promote` | `observe` — divergence too high |
| else | **`promote`** |

Defaults: `min_agreement_for_promote=0.7`, `max_divergence_for_promote=0.2`,
`min_samples_for_promote=30`, `reject_agreement_below=0.3`,
`min_samples_for_reject=10`. The active thresholds are serialised into the
report (`promotion_thresholds`) so the verdict is fully reproducible.

### Defensive parsing

`_summary_from_span` returns `None` rather than raising when a
`brain_shadow_eval` span has missing or wrong-typed attributes — span schema
drift cannot crash the aggregator.

### Why a separate aggregator (not extended in `BrainShadowRunner`)?

`BrainShadowRunner` is an event producer (one decision → one span); the
aggregator is an event consumer (many spans → one report). Splitting them
keeps the runner cheap on the request path and lets the aggregator be invoked
on demand or scheduled. No second TraceStore, no second runner, no model
load — just a structured read.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel router / runtime / orchestrator | ✅ — pure read consumer |
| No second TraceStore / ModelRegistry | ✅ — `TraceStore` injected, only `list_recent_traces` + `get_trace` used |
| No business logic in CLI/UI/OpenAPI layer | ✅ — logic lives in `core/decision/brain/` |
| Read-only against canonical state | ✅ |
| Additive only | ✅ — one new file + `__init__.py` extension |
| No new heavy dependencies | ✅ — stdlib (`statistics`, `collections.defaultdict`) + pydantic |
| Defensive against span drift | ✅ — malformed spans skipped, never raised |

---

## 5. Tests

**File:** `tests/decision/test_brain_baseline_aggregator.py`
**Count:** 29 tests

| Test class | Tests | Focus |
|-----------|-------|-------|
| `TestSummaryFromSpan` | 4 | extraction, missing attribute → None, type errors → None, None production_agent preserved |
| `TestComputeMetrics` | 6 | empty, all-agree, all-disagree, mixed rates, distinct coverage, median |
| `TestRecommendation` | 6 | observe/promote/reject across sample counts, divergence guard, low-sample reject suppressed |
| `TestAggregateAgainstTraceStore` | 11 | empty store, non-shadow spans skipped, real shadow aggregation, workflow/version filters, per-version isolation across two registered Brain models, threshold serialisation, sample-count promotion gates, trace_limit cap, malformed shadow span skipped |
| `TestReportSchema` | 2 | extra-fields rejection on report and metrics |

**Aggregator suite:** 29/29 green.
**Full suite:** 1501 passed, 1 skipped — all green (21s).

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (read-only aggregation only) | ✅ |
| No production path touched | ✅ |
| No second TraceStore / ModelRegistry | ✅ |
| No model loaded by aggregator | ✅ |
| Recommendation thresholds explicit and serialised | ✅ |
| Defensive against malformed spans | ✅ |
| Tests green (29/29 new + 1501/1501 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Phase 6 status after B6-S5

The Phase 6 *Brain v1* loop is now end-to-end on main:

```
LearningRecord
  → BrainRecordBuilder        (B6-S2)
  → BrainRecord JSONL
  → BrainOfflineTrainer       (B6-S3)
  → ModelRegistry.register_brain (B6-S4)
  → BrainShadowRunner.evaluate → brain_shadow_eval span (B6-S4)
  → BrainBaselineAggregator   (B6-S5) → promote / observe / reject
```

Phase 6 roadmap tasks `Shadow-Mode für Brain-v1 einführen` and
`Brain-v1 gegen heuristische Baseline evaluieren` are both closed on main.
Outstanding Phase 6 task: `Brain-v1 nur als Vorschlagsmodell ausrollen` —
require a positive `promote` verdict on a real-traffic baseline run before
wiring suggestions into operator surfaces.

---

## 8. Next step

With Phase 6 evaluation surface in place, the natural next move is one of:

- **Phase 6 / suggestion surface (B6-S6)**: surface a Brain top-1 suggestion
  alongside the production decision in `TraceStore` (still no decision
  ownership), gated by an explicit `promote` verdict — keeps the
  *suggestion-only* contract from the roadmap exit criteria.
- **Phase 0/1/2 backfill**: revisit any open consolidation, replay or plugin
  items from earlier phases that still block production-grade Brain
  promotion.

Recommend B6-S6 only after a real-traffic baseline run produces a `promote`
verdict; otherwise prioritise raising shadow coverage so the aggregator can
reach `min_samples_for_promote`.
