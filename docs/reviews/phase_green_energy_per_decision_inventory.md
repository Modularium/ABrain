---
name: §6.5 Green AI — per-decision energy signal inventory
description: Analysis-only spec for extending EnergyEstimator from a per-agent aggregate report to a per-decision signal emitted by the routing dispatcher/auditor.
type: inventory
---

# §6.5 Green AI — per-decision energy signal inventory

**Branch:** `codex/phase_green_energy_per_decision_inventory`
**Date:** 2026-04-19
**Scope:** Analysis-only.  Specifies how to wire the existing
`EnergyEstimator` (`core/decision/energy_report.py`, §6.5 *"Energie-
verbrauch pro Modellpfad messen"*) into the routing decision path as
a **per-decision** signal, mirroring the `cost_per_1k_tokens` /
`p95_latency_ms` treatment landed in the Phase-4 §263 series.

No code change.  Produces the specification a later
`codex/phase_green_energy_per_decision` turn will implement against.

---

## 1. Roadmap position

§6.5 currently contains one remaining architectural loose end that
is not operator-side: the `EnergyEstimator` landed in
`phase_green_energy_estimator_review.md` (commit referenced there) is
a **per-agent aggregate report** — it composes with
`PerformanceHistoryStore.snapshot()` to produce totals per agent
after the fact.

It does **not** participate in routing decisions.  The dispatcher
emits `cost_per_1k_tokens` and `p95_latency_ms` on every span, but
not `estimated_energy_joules`.  Operators can inspect energy *after*
execution, not *before* a dispatch decision.

This inventory specifies the missing hook: a per-decision energy
signal available (a) on `RoutingAuditor` spans and (b) as an optional
dispatch filter/rank term.

---

## 2. Idempotency check

- `grep -i 'energy\|watt\|joule' core/routing/` — **zero hits**.  No
  existing per-decision energy primitive.
- `grep -i 'energy' core/decision/energy_report.py` — existing
  aggregate report; untouched by this spec.
- No pre-existing `phase_green_energy_per_decision*.md` on `main`.
- No parallel branch with the same scope.

Consequence: additive, doc-only landing.  The implementation turn
would be genuinely new territory — not a rename, not a shim.

---

## 3. Candidate hook points (same pattern as §263)

### 3.1 Auditor-only (observability-shaped)

`RoutingAuditor` already emits a stable-schema attribute set:

```
routing.result.cost_per_1k_tokens
routing.result.p95_latency_ms
routing.result.quantization.*
routing.result.distillation.*
```

Adding:
```
routing.result.estimated_energy_joules   # null if wattage unknown
routing.result.energy_profile_source     # null | "measured" | "vendor_spec" | "estimated"
```

keeps the rule "always emit, null when absent" stable.  Pure
observability — no dispatcher behaviour change.  Mirrors the Turn-7
audit pattern from §263.

**Recommendation:** this is the *minimum* shape of the implementation
turn.  It is a proper subset of the full integration and can ship
alone if the policy layer (§3.3) turns out to be controversial.

### 3.2 Dispatcher filter — `max_energy_joules` request field

Parallel to `max_quality_regression` from Turn 11:

```python
max_energy_joules: float | None = Field(default=None, ge=0.0)
```

Behaviour:
- `None` (default): gate disabled; backwards-compatible.
- `>= 0.0`: reject candidates whose per-decision energy estimate
  exceeds the threshold.
- Unknown energy (`None` per-decision estimate) passes through —
  §6.5 honesty rule, identical to the `None`-delta rule of Turn 11.

Cascade: add a `no-energy` pass before `no-caps`, mirroring the
`no-quality` pass added in Turn 11.  Seven-pass cascade.

### 3.3 Dispatcher rank term — sixth tuple element

Extend `_sort_key` to:

```
(local_bonus, tier, cost, latency, quality_penalty, energy_penalty)
```

where `energy_penalty = estimated_joules if known else math.inf`.

Subordinate to latency/cost/quality (a cheap slow low-energy model
still beats an expensive fast low-energy model in cost-sensitive
deployments).  Honesty rule: unknown energy sorts last within its
bucket.

### 3.4 Combined (recommended for the implementation turn)

All three: auditor attributes + filter + rank term.  Same single-diff
shape as Turn 11 (`7d531220`).  One file: `core/routing/dispatcher.py`
(+ one file `core/routing/auditor.py` for §3.1).  Reason to combine:
split would require two separate cascades-updated test suites; all-in
keeps the invariant footprint identical to §263.

---

## 4. Per-decision energy formula

Per invocation:

```
joules = descriptor.p95_latency_ms / 1000.0 × energy_profile.avg_power_watts
```

Uses `p95_latency_ms` (not `avg_latency`) because dispatch decisions
are made **before** execution — the p95 budget is the published
worst-case latency operators have already agreed to, and the
dispatcher already filters on it (`_apply_latency`).  Matching the
filter signal to the energy signal avoids paradoxes where a model
passes `max_p95_latency_ms` but fails `max_energy_joules` due to a
different latency number.

Fallback rule: if `p95_latency_ms is None` → energy unknown (`None`).
No default-value invention; consistent with Turn 9 / Turn 10 honesty.

---

## 5. Wattage source — three design options

### 5.1 Embed on `ModelDescriptor`

```python
class ModelDescriptor(BaseModel):
    ...
    energy_profile: EnergyProfile | None = None
```

**Pros:** co-locates all dispatch signals (cost/latency/quantization/
energy) on one declaration; the registry is the single source of
truth; no cross-module lookups during dispatch.

**Cons:** couples `core/routing/` to `EnergyProfile` (defined in
`core/decision/energy_report.py`).  Import direction: routing imports
decision.  Acceptable per existing `core/decision/` → `core/routing/`
boundaries (`AgentPerformanceReporter` already sits on decision side
consuming routing history).

### 5.2 Dispatcher-side lookup table

```python
class ModelDispatcher(BaseModel):
    energy_profiles: dict[str, EnergyProfile] = Field(default_factory=dict)
```

**Pros:** no descriptor schema change; wattage can be operator-
supplied at service-wiring time in `services/core.py`.

**Cons:** creates a second source of truth parallel to the registry;
catalog descriptors and wattage can drift; lineage attributes on
spans would need both lookups.

### 5.3 Per-call lookup against `EnergyEstimatorConfig`

Pass an `EnergyEstimatorConfig` into `ModelDispatcher.dispatch(...)`.

**Pros:** zero coupling on declaration; EnergyEstimator remains the
sole energy-config owner.

**Cons:** dispatch signature bloat; every caller now needs the
config; violates "dispatch takes a request, not a service bag" rule.

**Recommendation (for the implementation turn):** option 5.1.
Co-location matches the Turn-10 `QuantizationProfile` precedent.  The
import-direction hit is minor and one-way; the alternative scattered
configs are worse for auditability.

---

## 6. Invariants the implementation turn must preserve

| Invariant | Spec position |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | Change lives on Decision side (dispatcher) + Audit side (auditor); no policy-escalation |
| `core/routing/` declares facts; dispatcher decides; auditor observes | Wattage is a declared fact on descriptor (option 5.1); dispatcher reads, auditor reports |
| Prefer-LOCAL default preserved | `local_bonus` stays first in `_sort_key`; energy is 6th |
| Fallback-cascade termination guaranteed | Final pass remains cap-free `no-caps`; `no-energy` added before it |
| `None`-signal not coerced to `0.0` or invented | Unknown wattage → unknown energy → pass-through (§3.2) / sort-last (§3.3) |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | None touched; registry is already the dispatcher's single truth |
| `RoutingAuditor` span schema stable | Two new `routing.result.*` keys, "always emit, null when absent" |
| Capability requirements never relax before quality/energy | Cascade ordering: caps → budget → quality → energy → caps-free |
| Backward compatibility with `DEFAULT_MODELS` | `energy_profile` default `None`; unknown energy passes through |
| No new runtime / store / heavy dependency | Stdlib + existing pydantic; `EnergyProfile` already exists |
| No business logic outside `core/routing/` + `core/decision/` | One dispatcher file, one auditor file, possibly one descriptor-schema file |

---

## 7. Non-goals (twelve explicit)

1. No automatic energy-from-cost inference (would invent a constant the operator never set).
2. No joules→Wh conversion on the dispatch path (Wh is for aggregate reports, joules for per-decision).
3. No token-based energy model (`J/token`) in v1 — latency × wattage is the only honest signal we have.
4. No wattage measurement primitive (that is `measured` profile source's job — operator instrumentation).
5. No energy-based demotion or degradation of hosted tiers outside the operator's `max_energy_joules` request.
6. No per-purpose default tolerance (parallel to §263's non-goal #6).
7. No Energy→Cost→Quality tri-objective optimisation (subordinate rank ordering is enough).
8. No new `abrain green` CLI surface in the implementation turn — `abrain routing models` already shows descriptor fields; energy lineage would appear there for free if co-located (option 5.1).
9. No policy for wattage profile drift (belongs to a later operator-ops turn).
10. No carbon-intensity (gCO₂/kWh) layer — that is a per-region op-time signal, not a per-decision signal.
11. No battery-state awareness (out of scope for `core/routing/`).
12. No retraining of `EnergyEstimator` on live traffic (it is a read-only aggregator; this inventory keeps that property).

---

## 8. Implementation turn spec (to be cited verbatim by `codex/phase_green_energy_per_decision`)

**Files changed:**
- `core/routing/models.py` — add `energy_profile: EnergyProfile | None = None` on `ModelDescriptor`; import from `core.decision.energy_report`.
- `core/routing/dispatcher.py` — add `max_energy_joules`, `_effective_energy_joules`, `_apply_energy`, `_apply_no_energy`, cascade entry, sixth `_sort_key` tuple element, updated module docstring.
- `core/routing/auditor.py` — add `routing.result.estimated_energy_joules` and `routing.result.energy_profile_source` attributes with "always emit, null when absent" semantics.
- `core/routing/catalog.py` — unchanged in v1 (leaving all defaults `None`, honesty rule per Turn 9 + Turn 13).

**Tests (new file `tests/routing/test_dispatcher_energy_policy.py`):**

1. Request validation (default None, accepts 0.0, rejects negative).
2. Backward compat on `DEFAULT_MODELS` — unchanged dispatch with `max_energy_joules=None`.
3. Per-decision formula — joules = p95 × watts / 1000.
4. Unknown p95 → unknown energy → filter pass-through.
5. Unknown wattage → unknown energy → filter pass-through.
6. Boundary: tolerance-exact candidate passes.
7. Sort tuple: measured < measured (better first).
8. Sort tuple: measured < unknown (unknown sorts last).
9. `no-energy` cascade pass — picks candidate over caps-only.
10. `no-energy` ordering — energy relaxes before caps.
11. Auditor emits both new keys always (measured and unknown cases).
12. Span attribute types — joules is `float | None`, source is `str | None`.

**Expected test-suite deltas:** +12 new tests.  Routing suite +12.
Mandatory canonical suite unchanged (routing isn't in the mandatory
list).  Full suite +12.

**Expected diff size:** ~60 lines dispatcher, ~30 lines auditor,
~5 lines model, ~200 lines tests — within the single-diff convention
of the §263 series.

---

## 9. Invariants preserved (by this inventory doc itself)

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — doc only |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — spec mirrors this layering |
| No new runtime / store / heavy dependency | ✅ — doc only; spec confirms the rule |
| `ModelDispatcher` stays the sole routing decision point | ✅ — spec locates all changes there + auditor |
| `None`-signal is not coerced to `0.0` or invented | ✅ — explicit §4 fallback rule |
| Prefer-LOCAL default preserved | ✅ — spec keeps `local_bonus` as first sort term |
| Backward compatibility with `DEFAULT_MODELS` | ✅ — §5.1 default `None`; §3.2 gate off by default |
| `EnergyEstimator` read-only property preserved | ✅ — §7 non-goal #12 |

---

## 10. Artifacts

| File | Change |
|---|---|
| `docs/reviews/phase_green_energy_per_decision_inventory.md` | new — this doc |
| `docs/reviews/phase_green_energy_per_decision_inventory_review.md` | new — wrapper |

No code change, no test change, no schema touch.

---

## 11. Test gates

Analysis-only turn.  Required regression guards:

- Mandatory canonical suite: unchanged from Turn 13 (`5014ec16`).
- Full suite (`tests/` with `test_*.py`): unchanged from Turn 13
  (1890 passed, 1 skipped).

No new tests; this turn writes no code.  The implementation turn
(§8) owns its own +12 test gate.

---

## 12. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (analysis-only, matches `phase6_brain_v1_inventory.md:§10 option 2`) | ✅ |
| Idempotency rule honoured (no duplicate inventory doc) | ✅ |
| No parallel structure introduced | ✅ |
| No code change, no Schatten-Wahrheit introduced | ✅ |
| Spec explicitly preserves every §263 invariant | ✅ |
| `None`-signal honesty rule recorded | ✅ |
| Three hook-point options enumerated honestly (§3) | ✅ |
| Three wattage-source options enumerated honestly (§5) | ✅ |
| Twelve non-goals listed (§7) — scope bounded | ✅ |
| Mandatory suite green (regression guard) | ✅ |
| Full suite green (regression guard) | ✅ |
| Documentation consistent with §263 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 13. Next step

1. **`codex/phase_green_energy_per_decision`** — implement §8 of this
   inventory as a single diff.  Owns `ModelDescriptor` +
   `ModelDispatcher` + `RoutingAuditor` changes and ~12 new tests.
   After landing, §6.5 gains its first per-decision observability
   signal.
2. **Operational (non-code):** real-traffic Brain-v1 shadow mode for
   `promote`-verdict via `BrainOperationsReporter` — unblocks
   Phase 6 E1/E3 and the deferred Phase 7.
3. **Optional follow-up:** wattage allow-list on `abrain routing
   models` so operators can audit which descriptors lack profiles.

No immediate blockers on `main`.
