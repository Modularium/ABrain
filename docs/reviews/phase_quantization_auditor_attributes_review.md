# Phase 4 — RoutingAuditor quantization/distillation span attributes

**Branch:** `codex/phase_quantization_auditor_attributes`
**Date:** 2026-04-19
**Scope:** Extend `RoutingAuditor` to flatten the declared quantization
and distillation lineage from the selected `ModelDescriptor` onto the
routing span.  Pure observation — no routing-policy change, no
dispatcher touch, no CLI touch.  Completes the "audit-sichtbar" side of
the Phase-4 §263 roadmap row for operators who want to query TraceStore
for LOCAL-variant usage without joining back to the registry.

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md:263` remains formally deferred, but the
three sub-concerns from `phase_quantization_inventory.md §2` are now
covered in two of three layers:

| Layer | Status after this turn |
|---|---|
| Declaration (fields on `ModelDescriptor`) | ✅ landed in `037b161e` |
| **Audit (auditor span attributes)** | ✅ **this turn** |
| Routing policy (dispatcher awareness) | ⏳ deferred — needs own sub-inventory |
| Conversion pipeline (llama.cpp/optimum/GGUF) | ⏳ deferred indefinitely |

An operator can now (a) declare a quantized/distilled LOCAL artefact
via `ModelDescriptor.quantization` / `.distillation`, (b) query
`TraceStore` for `routing.result.quantization.method` /
`routing.result.distillation.teacher_model_id` across every dispatch
span, and (c) compute LOCAL-vs-hosted KPIs split by quant/distill
variant.  Dispatcher semantics are still untouched — that step is
explicitly sequenced after this one.

---

## 2. Idempotency check

- `grep -n "quantization\." core/routing/auditor.py` — zero hits on main before this turn.
- `grep -n "lineage_attributes" core/routing/` — zero hits.
- No parallel branch, no partial auditor extension in any working tree.
- `tests/routing/test_routing_auditor.py` (the 35-test original suite) has **zero** lineage assertions; the new test file is strictly additive.
- The declaration layer from the prior turn supplies all lookup data — this turn only reads fields that already exist on main.

Consequence: purely additive, one file touch plus one new test file.

---

## 3. Design

### 3.1 New span attribute keys

Six keys, **always emitted** (value `None` when absent) so the span
schema stays stable and queryable — same convention as
`routing.result.cost_per_1k_tokens` / `routing.result.p95_latency_ms`:

```
routing.result.quantization.method                    # str | None
routing.result.quantization.bits                      # int | None
routing.result.quantization.quality_delta_vs_baseline # float | None
routing.result.distillation.teacher_model_id          # str | None
routing.result.distillation.method                    # str | None
routing.result.distillation.quality_delta_vs_teacher  # float | None
```

Keys emitted on both `record_dispatch` and `record_routing_failure`
finish-attr payloads.  On failure all six are `None` because no
descriptor is selected — same shape as `model_id` / `provider` / `tier`
already use.

### 3.2 `_lineage_attributes(descriptor)` helper

Factored into a private function alongside `_request_attributes` /
`_result_attributes`.  Always returns six keys; degrades cleanly to
`None` when `descriptor is None` or when the descriptor carries no
lineage (e.g., hosted models, or LOCAL models without declared
provenance).  Called from `_result_attributes` via `attrs.update(...)`
to keep the existing cost/latency code path untouched.

### 3.3 Why flatten onto the span rather than nest

Two reasons:

1. **Queryability.**  TraceStore span-attribute queries are flat
   key-lookups; a nested `dict` attribute would require custom JSON
   extraction.  Flattening with dotted namespace keys is the
   established S19 convention.
2. **Schema stability.**  If lineage were a nested `dict` attribute,
   the presence/absence of sub-keys would vary by descriptor — making
   downstream dashboards depend on optional keys.  Flattening with
   `None` defaults gives a **fixed** 6-key schema on every span.

### 3.4 Non-changes

- `ModelDispatcher` — untouched.  Prefer-LOCAL semantics unchanged.
- `ModelDescriptor` — untouched.  Fields from the prior turn only
  consumed.
- `ModelRegistry` — untouched.  Advisory warnings identical.
- `services/core.py` / `scripts/abrain_control.py` — untouched.
- `core/audit/trace_store.py` — untouched.  Span-attribute API reused
  as-is.
- Existing `tests/routing/test_routing_auditor.py` (35 tests) — zero
  assertion changes; all still green.

---

## 4. Public surface

No new imports, no new symbols.  The only observable change is on the
span attribute payload emitted by the existing `RoutingAuditor` API.
Operators querying TraceStore gain six new queryable keys.

Example query pattern (operator-side):

```
-- count LOCAL dispatches split by quantization method
SELECT
    json_extract(attributes, '$."routing.result.quantization.method"') AS method,
    COUNT(*) AS n
FROM span_records
WHERE span_type = 'routing'
  AND json_extract(attributes, '$."routing.result.tier"') = 'local'
GROUP BY 1;
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — extension lives on the Audit side of the routing layer |
| `TraceStore` sole audit truth | ✅ — attributes go to the existing store via the existing API |
| `RoutingAuditor` is a pure observation layer | ✅ — no routing-policy code touched |
| Span attributes follow the `<subsystem>.<operation>.<attribute>` convention | ✅ — keys are dotted under `routing.result.<lineage>.<field>` |
| Errors in audit emission swallowed, never interrupt dispatch | ✅ — `_emit()` try/except unchanged |
| Prefer-LOCAL routing unchanged | ✅ — dispatcher not touched |
| `ModelDescriptor` / `ModelRegistry` invariants from the prior turn | ✅ — only read, never mutated |
| No new runtime, store, or heavy dependency | ✅ — stdlib only |
| Schema stability for downstream queries | ✅ — six keys always emitted, no conditional key presence |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/routing/auditor.py` | +module-docstring keys; +6 keys in `record_routing_failure` finish payload; +`_lineage_attributes(descriptor)` helper; call site extended in `_result_attributes` |
| `tests/routing/test_routing_auditor_lineage.py` | new — 14 tests |
| `docs/reviews/phase_quantization_auditor_attributes_review.md` | this doc |

All other files unchanged.

---

## 7. Test coverage

14 new tests in `tests/routing/test_routing_auditor_lineage.py`:

- **TestLineageSchemaStability** (3): all six keys always present —
  without descriptor, with hosted descriptor, on failure span.  Asserts
  the stable-schema invariant directly.
- **TestQuantizationAttributes** (3): full QuantizationProfile
  populates three keys; partial profile (no quality_delta) keeps that
  key as None; LOCAL descriptor without quant keeps all three as None.
- **TestDistillationAttributes** (3): full DistillationLineage
  populates three keys; partial lineage (no quality_delta) keeps that
  key as None; both lineages together populate both triples.
- **TestExistingAttributesPreserved** (2): cost/latency still emitted
  alongside lineage (LOCAL tier cost=None by invariant; latency=800);
  model_id/tier/provider unchanged.

Every new test hits a real `TraceStore` (sqlite in `tmp_path`) — no
mocks — so the round-trip through the store is validated too.

---

## 8. Test gates

- Focused: `tests/routing/test_routing_auditor_lineage.py` — **14 passed**.
- Routing suite: `tests/routing/` — **194 passed** (85 existing model/registry/catalog + 35 existing auditor + 25 declaration + 14 new lineage + 35 dispatcher).
- Mandatory canonical suite: **1217 passed, 1 skipped** (unchanged — `tests/routing/` sits outside it; upstream consumers still green).
- Full suite (`tests/` with `test_*.py`): **1839 passed, 1 skipped** (+14 new).
- `py_compile core/routing/auditor.py` — clean.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (observation-only, reads declaration layer) | ✅ |
| Idempotency rule honoured (no duplicate attribute emission) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical audit path reinforced (same `TraceStore`, same `RoutingAuditor`) | ✅ |
| No routing-policy change | ✅ |
| Schema stability preserved (6 keys always emitted) | ✅ |
| Existing auditor tests all green unchanged | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+14 new) | ✅ |
| Documentation consistent with inventory + declaration turn | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

With declaration + audit both green, the remaining Phase-4 §263
concerns are:

1. **`codex/phase_quantization_routing_policy`** — teach
   `ModelDispatcher` to treat `quality_delta_vs_teacher` /
   `quality_delta_vs_baseline` as an additional signal in the
   prefer-LOCAL check.  Larger scope because prefer-LOCAL is central
   to Phase 4; needs its own sub-inventory first (what tolerance
   semantics?  how does it interact with the existing fallback
   cascade?).  Not a one-file turn.
2. **Conversion pipeline** — stays deferred indefinitely per
   `phase_quantization_inventory.md §5`.

Smaller sibling surfaces available if a non-policy turn is preferred
next:

- `abrain routing models` read-only CLI — now that the audit trail
  carries lineage, an operator surface that dumps the registry with
  lineage metadata would round out the §4 operator-reach story.
  Small scope, single `services.core.get_routing_models` + one
  handler + one renderer.
- Default-catalog descriptors in `core/routing/catalog.py` could be
  annotated with their real-world quant/distill profiles, which would
  exercise the advisory and populate the audit trail for existing
  LOCAL entries.  Even smaller scope — one file change and a
  documentation update.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`.  No immediate blockers on main.
