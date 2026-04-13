# Phase S4.2 — Soft Fallback & Routing Preferences: Implementation Review

**Branch:** `codex/phaseS4-2-soft-fallback-and-routing-preference`
**Date:** 2026-04-13
**Reviewer:** Implementation self-review

---

## 1. Scope

Phase S4.2 adds *pre-execution* routing intelligence to the canonical ABrain routing path.
It operates entirely inside `route_intent()`, after neural MLP scoring and before
`RoutingDecision` construction.  No new runtime, no second orchestrator, no S4 hard-fallback
replacement.

---

## 2. Invariants Verified

| # | Invariant | Status |
|---|---|---|
| 1 | No Governance bypass | ✓ S4.2 selects the agent *before* governance; governance runs normally for the chosen agent |
| 2 | No second Orchestrator | ✓ All logic is inside `route_intent()` — a single method call in the existing path |
| 3 | No new Retry logic | ✓ One selection pass; no while-loop, no recursion |
| 4 | Bounded | ✓ `_apply_degraded_penalty` and `_apply_cost_tiebreak` each make a single O(n) pass |
| 5 | S4 Hard-Fallback unaffected | ✓ S4.2 helpers live in `route_intent()`; S4's `_attempt_fallback_step` is in `_execute_step()` — orthogonal paths |
| 6 | Feedback semantics unchanged | ✓ S4.2 changes only the agent selection; feedback recording paths (S3/S4) are unmodified |
| 7 | Backwards compatible | ✓ `RoutingPreferences` has safe defaults; new `RoutingDecision` fields are `None` when no candidates |
| 8 | No MLP mutation | ✓ DEGRADED penalty is applied *after* `score_candidates()` — model weights are never touched |

---

## 3. Architecture

### 3.1 Insertion Point

```
route_intent()
  ├─ CandidateFilter.filter_candidates()       [hard policy: OFFLINE, caps, trust]
  ├─ NeuralPolicyModel.score_candidates()      [MLP scoring]
  │
  ├─ _apply_degraded_penalty()   ← S4.2 NEW   [re-sort after DEGRADED penalty]
  ├─ _apply_cost_tiebreak()      ← S4.2 NEW   [prefer cheaper within score band]
  ├─ _compute_routing_metrics()  ← S4.2 NEW   [confidence, score_gap, confidence_band]
  │
  └─ RoutingDecision(... routing_confidence, score_gap, confidence_band)
```

### 3.2 Data Flow

- **`_apply_degraded_penalty(scored, descriptors_by_id, multiplier)`**
  - Creates new `ScoredCandidate` instances via `model_copy(update={...})` — never mutates input
  - Re-sorts descending after penalty application
  - Early-exit (`return scored`) if `multiplier >= 1.0` (no-op path; original list returned)
  - Missing descriptor → no penalty (safe default)

- **`_apply_cost_tiebreak(scored, descriptors_by_id, band)`**
  - Partitions candidates into `in_band` (score ≥ top − band) and `out_of_band`
  - Sorts `in_band` by `_COST_PREFERENCE_ORDER[cost_profile]` ascending, then by `-score` for tie-within-tier
  - `out_of_band` appended unchanged
  - Early-exit if `band <= 0.0` or only one candidate

- **`_compute_routing_metrics(scored)`**
  - `routing_confidence = top_score` (honest, directly observable)
  - `score_gap = top_score − second_score` (0.0 for single candidate)
  - `confidence_band`: high ≥ 0.65, medium ≥ 0.35, low < 0.35
  - Returns `(None, None, None)` for empty list

### 3.3 Preferences

`RoutingPreferences` is a Pydantic `BaseModel` (extra="forbid") stored as `self.preferences`
on `RoutingEngine` at construction time.  Not threaded through `route_step()` or
`route_intent()` signatures — avoids breaking existing `RecordingRoutingEngine` and
`ControlledRoutingEngine` test overrides.

Default values are conservative:
- `degraded_availability_penalty = 0.85` (15 % reduction)
- `cost_tie_band = 0.05` (5 % band)
- `low_confidence_threshold = 0.0` (reserved; unused in v1)

### 3.4 Orchestrator Integration

In `_execute_step()`, the `finish_span()` call for `routing_span` now includes three
additional attributes when populated (`routing_confidence`, `score_gap`, `confidence_band`).

A `"routing_low_confidence"` span event is emitted immediately after `finish_span` when
`decision.confidence_band == "low"`.  This is purely observational — it does not alter
execution or trigger any approval escalation.

---

## 4. Files Changed

| File | Change |
|---|---|
| `core/decision/routing_engine.py` | `RoutingPreferences` model; three new `RoutingDecision` fields; `RoutingEngine.__init__` `preferences` kwarg; `_COST_PREFERENCE_ORDER` dict; `_apply_degraded_penalty`, `_apply_cost_tiebreak`, `_compute_routing_metrics` helper functions; `route_intent()` extended to call helpers |
| `core/decision/__init__.py` | `RoutingPreferences` imported and added to `__all__` |
| `core/orchestration/orchestrator.py` | `routing_span` `finish_span` attributes extended with confidence metrics; `add_span_event("routing_low_confidence")` on low-band |
| `tests/decision/test_routing_s42_preferences.py` | 28 new tests |

---

## 5. Test Coverage

| Area | Tests |
|---|---|
| `_apply_degraded_penalty`: DEGRADED reordered, multiplier=1.0 no-op, ONLINE untouched, empty, missing descriptor, no mutation | 6 |
| `_apply_cost_tiebreak`: LOW wins in band, out-of-band preserved, band=0 no-op, single candidate, full cost order | 5 |
| `_compute_routing_metrics`: empty→None, single (gap=0), high/medium/low bands, boundary values | 6 |
| `RoutingPreferences`: defaults, custom values, out-of-range validation, extra fields rejected | 4 |
| `RoutingEngine.__init__`: default preferences, custom preferences accepted | 2 |
| `RoutingDecision` new fields: populated end-to-end, None when no candidates | 2 |
| End-to-end: DEGRADED penalty via route(), cost tie-break via route() | 3 |
| **Total** | **28** |

---

## 6. What S4.2 Does NOT Do

- No background health monitor or registry mutation at runtime
- No budget or billing subsystem
- No automatic approval escalation on low confidence (that is S2 Governance territory)
- No MLP weight changes — DEGRADED penalty is a post-scoring correction
- No replacement of S4 hard-fallback
- No additional retry or parallel execution paths

---

## 7. Verdict

Implementation is architecturally clean:
- Single injection point, bounded, no side effects on other layers
- All 28 new tests pass; all 27 S4 tests pass; existing routing engine tests pass
- Backwards-compatible defaults; new `RoutingDecision` fields are additive (`| None`)
- Invariants 1–8 verified
