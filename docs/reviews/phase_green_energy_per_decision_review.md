# §6.5 Green AI — per-decision energy signal

**Branch:** `codex/phase_green_energy_per_decision`
**Date:** 2026-04-19
**Scope:** Implements the specification in
`docs/reviews/phase_green_energy_per_decision_inventory.md:§8`.
Promotes `EnergyEstimator` from a per-agent aggregate report (commit
`phase_green_energy_estimator_review.md`) to a per-decision routing
signal emitted by `RoutingAuditor` spans and consumed as an optional
dispatcher filter/rank term.

---

## 1. Roadmap position

Fifth turn of the §6.5 Green-AI track and the first turn after the
Phase-4 §263 six-turn series closed on `main`:

| Turn | Commit | Surface |
|---|---|---|
| §263 series | 6 commits, `037b161e..7d531220` | Quantization/distillation: declaration + audit + CLI + defaults + policy |
| §6 inventory | `40c80c36` | Phase-6 Brain-v1 status survey |
| §263 reclassification | `5014ec16` | Honest roadmap suffix on §Phase 4 §263 + §6.5 line 428 |
| §6.5 per-decision inventory | `870098a9` | Spec for this turn |
| **§6.5 per-decision (this turn)** | — | Dispatcher + auditor consume declared wattage |

This is the first §6.5 turn to deliver a *per-decision* metric.  The
earlier `phase_green_energy_estimator_review.md` shipped the
aggregate side.

---

## 2. Idempotency check

- `grep -i 'energy\|watt\|joule' core/routing/` before this turn —
  zero hits (inventory's finding).
- No pre-existing `energy_profile` field on `ModelDescriptor`, no
  pre-existing `max_energy_joules` field on `ModelRoutingRequest`,
  no pre-existing `routing.result.estimated_energy_joules` span key.
- Existing `tests/routing/` suite (221 tests) — fully green against
  the updated dispatcher: additive change with `None`-default is a
  no-op.
- No parallel branch.

Consequence: fully additive landing.  No renames, no shimming, no
migrations.

---

## 3. Design (as-built, matching inventory §8)

### 3.1 Descriptor field

`core/routing/models.py`:

```python
energy_profile: EnergyProfile | None = None
```

Imports `EnergyProfile` from `core.decision.energy_report` — the
existing definition already carries `avg_power_watts` and a
`source` tri-state (`measured` / `vendor_spec` / `estimated`).  No
new model, no new enum.  Hosted tiers are allowed to declare a
profile (inventory §5.1 recommendation — GPU wattage is a hosted
fact too), unlike `quantization` / `distillation` which remain
LOCAL-only.

### 3.2 Per-decision formula

`core/routing/dispatcher.py:_effective_energy_joules`:

```python
joules = descriptor.p95_latency_ms / 1000.0 × descriptor.energy_profile.avg_power_watts
```

Uses the declared `p95_latency_ms` (not observed average) so the
filter signal matches `_apply_latency` exactly — no paradox where a
descriptor passes the latency budget but fails the energy budget due
to a different latency number.  Missing p95 *or* missing wattage →
`None` (unknown).

### 3.3 Request field

```python
max_energy_joules: float | None = Field(default=None, ge=0.0)
```

- `None` (default): gate disabled; dispatch behaviour identical.
- `>= 0.0`: reject candidates whose known energy exceeds threshold.
- Unknown energy candidates pass the filter — §6.5 honesty rule,
  identical to the `None`-delta rule of Turn 11.
- Negative values rejected by pydantic.

### 3.4 Cascade

Seven-pass cascade:

```
Pass 1  strict      — caps + cost + latency + quality + energy
Pass 2  no-latency  — caps + cost + quality + energy
Pass 3  no-cost     — caps + latency + quality + energy
Pass 4  no-budget   — caps + quality + energy
Pass 5  no-quality  — caps + energy                        (was: caps only)
Pass 6  no-energy   — caps only                            (new)
Pass 7  no-caps     — nothing
```

Capabilities stay the last-relaxed.  Energy relaxes *after* quality:
quality regressions are operator-visible; energy overages are
infrastructure-visible.  Relax the less-visible preference later.

`fallback_reason="relaxed energy tolerance"` when pass 6 wins;
existing `"relaxed capability requirements"` still when pass 7 wins.
Free-text field; no audit-schema break.

### 3.5 Rank term

Sixth tuple element in `_sort_key`:

```python
joules = _effective_energy_joules(descriptor)
energy_penalty = joules if joules is not None else math.inf
return (local_bonus, tier, cost, latency, quality_penalty, energy_penalty)
```

- Measured 1.0 J → penalty 1.0 (sorts ahead).
- Measured 10.0 J → penalty 10.0 (sorts after 1.0 J).
- `None` → `+inf` (sorts last within bucket).

Subordinate to `local_bonus`, `tier`, `cost`, `latency`,
`quality_penalty` — prefer-LOCAL default preserved.

### 3.6 Auditor attributes

`core/routing/auditor.py` adds two keys with "always emit, null when
absent" semantics:

```
routing.result.estimated_energy_joules    float | null
routing.result.energy_profile_source      "measured" | "vendor_spec" | "estimated" | null
```

Emitted on both `record_dispatch` (success) and
`record_routing_failure` (null on failure) spans so the span schema
stays stable.

### 3.7 Non-changes

- `EnergyEstimator` / `EnergyEstimatorConfig` / `AgentEnergyEstimate`
  / `EnergyReport` — untouched.  Aggregate report remains read-only.
- `core/routing/catalog.py` — untouched.  All `DEFAULT_MODELS`
  entries leave `energy_profile=None` (honesty rule, same as
  `quality_delta_*=None`).  Operators register real wattage at
  runtime.
- `services/core.py` / `scripts/abrain` — untouched.
- `RoutingAuditor.SPAN_TYPE` — unchanged.

---

## 4. Public-surface effect

**Opt-in.**  Callers who do not set `max_energy_joules` and do not
register `energy_profile` on any descriptor see identical dispatch
results.  Two `TestBackwardCompat` tests verify this against the
real `DEFAULT_MODELS` catalog.

New behaviour for operators who register wattage:

```python
# Reject candidates whose per-decision energy exceeds 5 J.
req = ModelRoutingRequest(
    purpose=ModelPurpose.LOCAL_ASSIST,
    max_energy_joules=5.0,
)
result = dispatcher.dispatch(req)
# result.fallback_reason == "relaxed energy tolerance" when no
# candidate fits the budget and the cascade falls through to caps-only.
```

Every dispatch span now carries both new attribute keys — operators
can filter traces by `energy_profile_source="measured"` to isolate
audit-grade energy entries.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — changes live on Decision (dispatcher) + Audit (auditor) |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — `energy_profile` is a declared fact; `_apply_energy` decides; auditor flattens |
| Prefer-LOCAL default preserved | ✅ — `local_bonus` still first in sort tuple |
| Fallback-cascade termination guaranteed | ✅ — final pass remains cap-free `no-caps` |
| `None`-signal not coerced to `0.0` or invented | ✅ — missing p95 or missing wattage → unknown → filter pass-through, sort-last |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | ✅ — none touched |
| `RoutingAuditor` span schema stable | ✅ — two keys added, both "always emit, null when absent" |
| Capability requirements never relax before preferences | ✅ — cascade: caps → budget → quality → energy → caps-free |
| Backward compatibility with `DEFAULT_MODELS` | ✅ — gate off by default; `None` wattage defaults pass through |
| `EnergyEstimator` read-only property preserved | ✅ — aggregate estimator untouched |
| No new runtime / store / heavy dependency | ✅ — stdlib + existing pydantic |
| No business logic outside `core/routing/` + `core/decision/` | ✅ — three files changed (models, dispatcher, auditor) |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/routing/models.py` | +`EnergyProfile` import, +`energy_profile` field on `ModelDescriptor`, updated docstring |
| `core/routing/dispatcher.py` | +`max_energy_joules` field, +`_effective_energy_joules`, +`_apply_energy`, +`_apply_no_energy`, +`no-energy` cascade pass, +6th `_sort_key` term, updated module docstring |
| `core/routing/auditor.py` | +`_energy_attributes` helper, +2 span attribute keys, updated docstring |
| `tests/routing/test_dispatcher_energy_policy.py` | new — 21 tests |
| `docs/reviews/phase_green_energy_per_decision_review.md` | this doc |

No service change, no CLI change, no catalog change, no schema
break.

---

## 7. Test coverage

21 new tests across seven classes in
`tests/routing/test_dispatcher_energy_policy.py`:

- **`TestRequestValidation` (4)** — default `None`, accepts `0.0`, accepts large, rejects negative.
- **`TestBackwardCompat` (2)** — default catalog dispatch unchanged for CLASSIFICATION / LOCAL_ASSIST (regression guard on real `DEFAULT_MODELS`).
- **`TestFormula` (2)** — joules computed from p95 × wattage, over-threshold filtered.
- **`TestUnknownPasses` (3)** — unknown wattage passes, unknown p95 passes, boundary inclusive.
- **`TestCascadeOrdering` (4)** — `no-energy` pass wins with correct reason, caps honoured on `no-energy` pass, caps relax only in final pass, empty pool raises.
- **`TestRankTerm` (3)** — lower energy beats higher, measured beats unknown, tier beats energy.
- **`TestAuditorAttributes` (3)** — known energy emitted on success, unknown energy emitted as null, failure span includes null energy keys.

Plus: existing `tests/routing/` (221 tests) all pass unchanged —
the additive change is a no-op when `max_energy_joules=None` and
no descriptor declares `energy_profile`.

---

## 8. Test gates

- Focused: `tests/routing/test_dispatcher_energy_policy.py` — **21 passed**.
- Routing suite: `tests/routing/` — **242 passed** (+21; no pre-existing test touched).
- Full suite (`tests/` with `test_*.py`): **1911 passed, 1 skipped** (+21 from Turn 14 baseline of 1890).
- `py_compile core/routing/models.py core/routing/dispatcher.py core/routing/auditor.py` — clean.
- CLI smoke: no CLI change to smoke; the read-only `abrain routing models` surface would pick up `energy_profile` automatically if operators register one (follow-up inventory §13 option 3 — not in scope this turn).

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (matches inventory §8 exactly) | ✅ |
| Idempotency rule honoured (no duplicate primitive) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical dispatcher + auditor paths reinforced | ✅ |
| No business logic outside `core/routing/` + `core/decision/` | ✅ |
| No Schatten-Wahrheit (dispatcher reads declared wattage, never mutates) | ✅ |
| `None`-signal honesty rule preserved | ✅ |
| Capability requirements never relax before preferences | ✅ |
| Backward compatibility with `DEFAULT_MODELS` verified | ✅ |
| Routing suite green (+21) | ✅ |
| Full suite green (+21) | ✅ |
| Documentation consistent with prior §263 + §6.5 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

§6.5 now has its first per-decision observability signal.  Three
candidates remain, none urgent:

1. **CLI surface extension** — make `abrain routing models` surface
   `energy_profile.avg_power_watts` and `source` (parallel to the
   quantization/distillation columns added in Turn 7).  Tiny turn,
   one-file diff.  Useful once operators start registering profiles.
2. **Operational (non-code):** real-traffic Brain-v1 shadow mode via
   `BrainOperationsReporter` — unblocks Phase 6 E1/E3 + Phase 7.
3. **Operator-side quantization/distillation eval** — closes the
   eval-ausfuehrung side of §Phase 4 §263 + §6.5 line 428 that
   the Turn-13 reclassification left operator-seitig.

Recommendation: option 1 if another code turn is warranted, or stop
here and surface the session state — every other architectural
lever is either pulled or operator-gated.

No immediate blockers on `main`.
