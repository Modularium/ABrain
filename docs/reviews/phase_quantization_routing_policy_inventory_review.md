# Phase 4 — Quantization-aware routing policy inventory (review)

**Branch:** `codex/phase_quantization_routing_policy_inventory`
**Date:** 2026-04-19
**Scope:** Analysis-only turn.  Produces
`docs/reviews/phase_quantization_routing_policy_inventory.md` — the
specification the future `codex/phase_quantization_routing_policy`
turn will implement against.  No code change, no test change.

---

## 1. Roadmap position

Phase 4 §263 sub-concern §2.2 (policy layer) from the original
`phase_quantization_inventory.md`.  Prior four turns landed
declaration (`037b161e`), audit (`a92b76e3`), operator-surface
(`6dd5770b`), and default catalog data (`80b6d6f9`).  The catalog turn
committed to `quality_delta_*=None` on every default LOCAL entry,
which forces the policy layer to make an explicit decision on how to
treat unknown deltas — hence the inventory-first split.

---

## 2. Idempotency check

- `grep -rn "quality_delta" core/routing/dispatcher.py` — zero hits.
  No existing dispatcher consumption of the delta fields.
- No pre-existing `phase_quantization_routing_policy_inventory.md` on
  main.  This is the first analysis doc on the policy layer.
- No parallel branch with the same scope.
- The original `phase_quantization_inventory.md` flagged this as "for
  a later turn" and deferred policy specifics — this doc is the
  promised follow-up.

Consequence: additive, documentation-only landing.

---

## 3. What the inventory establishes

See `phase_quantization_routing_policy_inventory.md` — summarised
here:

- **Three candidate hook points** in the dispatcher (filter, rank,
  combined).  Recommendation: combined.
- **`None`-delta rule**: pass-through on the filter, sort-last on the
  rank term.  The catalog's honesty rule (Turn 9) is preserved —
  default deployments behave identically to today.
- **Fallback-cascade extension**: new `no-quality` pass inserted
  before `no-caps`, so capability requirements never relax before a
  quality preference.
- **Request-side field**: `max_quality_regression: float | None =
  None` with `ge=0.0, le=1.0`.  Naming mirrors the existing budget
  fields.
- **Delta source ordering**: distillation → quantization → `None`
  when both declarations are absent.
- **Eval harness prerequisite**: explicitly none.  Policy consumes
  declared deltas; evaluation is operator-side and remains deferred.
- **Sub-turn split**: not required unless the rank term surprises
  existing dispatcher tests.
- **Invariant honour table**: every existing invariant (prefer-LOCAL
  default, fallback termination, stable audit schema, no new runtime)
  has an explicit justification.
- **Test shape**: 12 enumerated test cases covering the pass-through
  rule, tolerance boundaries, distillation-vs-quantization preference,
  cascade ordering, rank-term ordering, and pydantic validation.
- **Twelve explicit non-goals** (eval harness, per-purpose tolerance,
  automatic demotion, etc.) — keeps the follow-up turn bounded.

---

## 4. Invariants preserved (by the inventory doc itself)

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — doc only |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — spec mirrors this layering |
| No new runtime / store / heavy dependency | ✅ — doc only; spec confirms the rule |
| `ModelDispatcher` stays the sole routing decision point | ✅ — spec locates all changes there |
| `None`-delta is not coerced to `0.0` or invented | ✅ — explicit §4 rule |
| Prefer-LOCAL default preserved | ✅ — spec keeps `local_bonus` as first sort term |
| Backward compatibility with `DEFAULT_MODELS` | ✅ — §4.2 pass-through rule means defaults dispatch identically |

---

## 5. Artifacts

| File | Change |
|---|---|
| `docs/reviews/phase_quantization_routing_policy_inventory.md` | new, 13 sections, ~320 lines |
| `docs/reviews/phase_quantization_routing_policy_inventory_review.md` | this doc |

No code change, no test change, no service/CLI touch, no schema
touch.

---

## 6. Test gates

Analysis-only turn.  Required regression guards:

- Mandatory canonical suite: **1241 passed, 1 skipped** (unchanged
  from Turn 9).
- Full suite (`tests/` with `test_*.py`): **1868 passed, 1 skipped**
  (unchanged from Turn 9).

No new tests; this turn writes no code.  The implementation turn
owns its own test gate against §8 of the inventory doc.

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (analysis-only, matches `phase_quantization_inventory.md:§2.2`) | ✅ |
| Idempotency rule honoured (no duplicate inventory doc) | ✅ |
| No parallel structure introduced | ✅ |
| No code change, no Schatten-Wahrheit introduced | ✅ |
| Spec explicitly preserves every prior §4 invariant | ✅ |
| `None`-delta handling decided honestly (§4.2 pass-through) | ✅ |
| Mandatory suite green (regression guard) | ✅ |
| Full suite green (regression guard) | ✅ |
| Documentation consistent with prior four §4 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

1. **`codex/phase_quantization_routing_policy`** — implement
   `phase_quantization_routing_policy_inventory.md:§8` as a single
   diff.  Owns `ModelDispatcher` + `ModelRoutingRequest` changes and
   ~12 new tests.  After landing, Phase 4 §263 is fully closed.
2. After that: Phase-6 or a §6 green-AI research-shaped step per the
   prior review doc.
3. Phase 7 blocker (real-traffic `promote` verdict) is unaffected.

No immediate blockers on `main`.
