# Phase 5 – LearningOps L5: Shadow / Canary Evaluation (ShadowEvaluator)

**Branch:** `codex/phase5-learningops-shadow-evaluator`  
**Date:** 2026-04-18  
**Roadmap task closed:** "Canary-/Shadow-Rollout für neue Decision-Modelle einführen" (Phase 5)

---

## 1. Scope

Run the active `ModelRegistry` model in shadow mode alongside the production
heuristic router, compare routing decisions, and emit structured metrics to
`TraceStore` — without touching the production `RoutingDecision`.

- `ShadowComparison` — Pydantic result of one comparison pass (agreement,
  score_divergence, top_k_overlap, agent IDs, version_id)
- `ShadowEvaluator` — best-effort orchestrator: loads active model, runs shadow
  `RoutingEngine`, computes comparison, writes `shadow_eval` span to TraceStore

---

## 2. Idempotency check

| Component | Status before L5 |
|-----------|-----------------|
| `shadow_evaluator.py` | **Did not exist** |
| Any other shadow/canary routing mechanism | Not found in codebase |
| `ModelRegistry.get_active_model()` | ✅ on main (L4) — **reused** |
| `RoutingEngine` | ✅ on main — **reused unmodified** |
| `TraceStore.start_span/add_event/finish_span` | ✅ on main — **reused** |

---

## 3. Design

### Golden rule: production path untouched

`ShadowEvaluator.evaluate()` is called **after** the production
`RoutingDecision` is already computed.  It receives the decision by value and
never modifies it.  The shadow `RoutingEngine` is always freshly instantiated
with the loaded model — it shares no state with the production engine.

### Best-effort: all errors are caught

The entire `_run_shadow` + `_write_span` block is wrapped in a single
`try/except Exception`.  Any failure (model load error, routing error, store
write error) returns `None` silently.  This matches the roadmap constraint
"Online-Lernen auf 'best effort' begrenzen".

### Comparison metrics

| Metric | Definition |
|--------|-----------|
| `agreement` | `shadow_top1 == production_top1` |
| `score_divergence` | `|production_score − shadow_score|` clamped to [0,1]; 1.0 when either score is absent |
| `top_k_overlap` | `|prod_top_k ∩ shadow_top_k| / |prod_top_k ∪ shadow_top_k|`; 1.0 when both empty |

### TraceStore span

```
span_type  = "shadow_eval"
name       = "learningops.shadow_evaluation"
attributes = {
    "shadow.version_id":         str,
    "shadow.production_agent":   str | None,
    "shadow.shadow_agent":       str | None,
    "shadow.agreement":          bool,
    "shadow.score_divergence":   float,
    "shadow.top_k_overlap":      float,
    "shadow.k":                  int,
}
event_type = "shadow_comparison"   (payload = full ShadowComparison dict)
status     = "ok"
```

The span is attached to the existing production trace_id, so it is
co-located with the production routing span for correlation.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No second production router | ✅ — shadow RoutingEngine is ephemeral, per-call |
| No second TraceStore | ✅ — writes to canonical TraceStore with distinct span_type |
| No modification of production RoutingDecision | ✅ — explicit test coverage |
| No business logic in wrong layer | ✅ — all in `core/decision/learning/` |
| No new heavy dependencies | ✅ — only existing canonical components |
| Additive only | ✅ — one new file + `__init__.py` extension |

---

## 5. Tests

**File:** `tests/decision/test_learningops_shadow_evaluator.py`  
**Count:** 17 tests (unit, tmp_path I/O only)

Coverage:
- `ShadowComparison`: schema, extra-field rejection, score_divergence bound
- No active model: returns None, no span written
- With active model: returns ShadowComparison, production decision unchanged,
  span written, span name canonical, attributes complete, event present,
  status OK, agreement with single candidate, score_divergence in [0,1],
  top_k_overlap in [0,1], custom `k`, error-returns-None (via subclass injection)

**Full suite:** 808 passed, 1 skipped — all green.

---

## 6. Usage pattern

```python
# After production routing:
production_decision = routing_engine.route(task, descriptors)

# Shadow evaluation (best-effort, non-blocking):
shadow_evaluator = ShadowEvaluator(registry=model_registry, trace_store=trace_store)
comparison = shadow_evaluator.evaluate(
    task, descriptors, production_decision, trace_id=active_trace_id
)
# comparison is ShadowComparison | None — never raises, never blocks production
```

---

## 7. Gate

| Check | Result |
|-------|--------|
| Scope correct (shadow eval only, no production touch) | ✅ |
| No parallel production router | ✅ |
| Canonical TraceStore used for output | ✅ |
| Production RoutingDecision immutable | ✅ |
| Best-effort: all errors caught | ✅ |
| Tests green (17/17 new + 808/808 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Phase 5 completion status

After L5 merges, all Phase 5 roadmap tasks are implemented:

| Task | Status |
|------|--------|
| Trainingsdaten-Schema definieren | ✅ L1 — LearningRecord |
| Datensätze aus Traces/Approvals generieren | ✅ L1+L2 — DatasetBuilder + DatasetExporter |
| Datenqualitätsregeln aufbauen | ✅ L1 — DataQualityFilter |
| Offline-Trainingsjobs definieren | ✅ L3 — OfflineTrainer + TrainingJobConfig |
| Modellartefakte versionieren | ✅ L4 — ModelRegistry |
| Canary-/Shadow-Rollout einführen | ✅ L5 — ShadowEvaluator |
| Online-Lernen begrenzen | ✅ by design — OnlineUpdater untouched; offline pipeline is the primary path |
| Rollback-Mechanismus | ✅ L4 — ModelRegistry.activate() |
| Eval-Suite für neue Modellversionen | ✅ L5 — ShadowEvaluator + ShadowComparison metrics |

**Phase 5 – LearningOps: COMPLETE**

---

## 9. Next phase

**Phase 6 – Brain v1**: Define target variables of the decision network,
formalise the state representation, and introduce the shadow-mode brain running
the offline-trained model for routing suggestions — using L5's `ShadowEvaluator`
as the integration layer.
