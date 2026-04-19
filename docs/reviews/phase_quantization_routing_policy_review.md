# Phase 4 — Quantization-aware routing policy

**Branch:** `codex/phase_quantization_routing_policy`
**Date:** 2026-04-19
**Scope:** Implements the specification in
`docs/reviews/phase_quantization_routing_policy_inventory.md:§8` —
the last open piece of Phase 4 §263.  Adds
``ModelRoutingRequest.max_quality_regression``, an ``_apply_quality``
filter, a dedicated ``no-quality`` pass in the fallback cascade, and
a five-element ``_sort_key``.  Single-file code diff in
`core/routing/dispatcher.py` + one new test file.

After this turn lands, Phase-4 §263 is fully closed: declaration +
audit + inspection + meaningful defaults + policy.

---

## 1. Roadmap position

Sixth and final Phase-4 §263 turn:

| Turn | Commit | Surface |
|---|---|---|
| §4 inventory | `e7c5cb90` | Three-way split (declaration / policy / pipeline) |
| §4 declaration | `037b161e` | `QuantizationProfile` + `DistillationLineage` |
| §4 audit | `a92b76e3` | Span attributes on `RoutingAuditor` |
| §4 operator surface | `6dd5770b` | `abrain routing models` CLI |
| §4 default catalog | `80b6d6f9` | LOCAL defaults declare real quant profiles |
| §4 policy inventory | `a0c9486c` | Spec for this turn |
| **§4 policy (this turn)** | — | Dispatcher consumes declared deltas |

The §263 Green-AI conversion pipeline (sub-concern §2.3) remains
deferred indefinitely per the original inventory; this turn does not
reopen that decision.

---

## 2. Idempotency check

- `grep -rn "max_quality_regression\|_apply_quality\|_effective_quality_delta\|no-quality"` before this turn — hits only in the inventory doc and its review wrapper (prose).  No code primitive to merge with.
- Existing dispatcher tests (`tests/routing/test_routing_dispatcher.py` + `tests/routing/test_routing_catalog.py`) relied on the four-pass cascade behaviour.  Running them against the updated dispatcher after implementation: 73 passed unchanged (additive change, `None`-default quality term is a no-op).
- No parallel branch.  No partial dispatcher change queued elsewhere.

Consequence: fully additive landing of the policy layer.  No
renames, no shimming, no migrations.

---

## 3. Design (as-built, matching inventory §8)

### 3.1 Request field

```python
max_quality_regression: float | None = Field(default=None, ge=0.0, le=1.0)
```

- `None` (default): quality gate disabled entirely.  Behaviour identical to the prior four-pass cascade.
- `0.0`: reject any regression (operator wants parity with baseline/teacher).
- `0.10`: reject regressions worse than 10%.
- Negative values rejected by pydantic; `>1.0` rejected by pydantic.

### 3.2 Effective-delta helper

```python
def _effective_quality_delta(descriptor) -> float | None:
    if descriptor.distillation is not None:
        return descriptor.distillation.quality_delta_vs_teacher
    if descriptor.quantization is not None:
        return descriptor.quantization.quality_delta_vs_baseline
    return None
```

Distillation-first ordering matches inventory §6.3: a distilled
student is a more fundamental transformation than a quantized
artefact, and the teacher is the semantic reference point.  Hosted
tiers never declare lineage (schema invariant in
`core/routing/models.py:_lineage_restricted_to_local_tier`), so this
always returns `None` for them.

### 3.3 Filter

```python
def _apply_quality(candidates, request):
    if request.max_quality_regression is None:
        return candidates
    threshold = -request.max_quality_regression
    return [
        d for d in candidates
        if _effective_quality_delta(d) is None        # unknown passes
        or _effective_quality_delta(d) >= threshold   # measured ≥ threshold
    ]
```

`None`-delta pass-through matches inventory §4.2.  Coercing to `0.0`
(§4.3) was explicitly rejected as a correctness bug.  Coercing to
"fail" (§4.1) was rejected as breaking the prefer-LOCAL invariant on
default deployments.

### 3.4 Cascade

```
Pass 1  strict      — caps + cost + latency + quality
Pass 2  no-latency  — caps + cost + quality
Pass 3  no-cost     — caps + latency + quality
Pass 4  no-budget   — caps + quality
Pass 5  no-quality  — caps only                        (new)
Pass 6  no-caps     — nothing
```

Capabilities are contracts (tool use, structured output); quality is
a preference.  Contracts must never relax before preferences — hence
the dedicated `no-quality` pass before `no-caps`.

`fallback_reason="relaxed quality tolerance"` when pass 5 wins;
`"relaxed capability requirements"` still when pass 6 wins.  Free-
text field; no audit-schema change.

### 3.5 Rank term

Fifth tuple element in `_sort_key`:

```python
quality_penalty = -delta if delta is not None else math.inf
return (local_bonus, tier, cost, latency, quality_penalty)
```

- Measured `-0.02` → penalty `0.02` (sorts ahead).
- Measured `-0.15` → penalty `0.15` (sorts after `-0.02`).
- `None` → penalty `+inf` (sorts last within a tier bucket).

Subordinate to `local_bonus`, `tier`, `cost`, and `latency` —
prefer-LOCAL default is preserved.

### 3.6 Non-changes

- `ModelDescriptor` / `QuantizationProfile` / `DistillationLineage` — schema unchanged.
- `ModelRegistry` — unchanged.
- `RoutingAuditor` — span schema unchanged; the `routing.result.quantization.*` / `routing.result.distillation.*` attributes landed in `a92b76e3` already carry the evidence.  `fallback_reason` is already free-text so the new "relaxed quality tolerance" string is additive.
- `services/core.py` / `scripts/abrain_control.py` — unchanged.
- `core/routing/catalog.py` — unchanged (Turn 9 already committed to `None` deltas).

---

## 4. Public-surface effect

**Opt-in.**  Callers who do not set `max_quality_regression` see
identical dispatch results.  Verified by regression tests on the real
`DEFAULT_MODELS` catalog (see §7, `TestBackwardCompat`).

New behaviour for operators who have run an eval and registered
measured deltas:

```python
# Reject LOCAL candidates regressing more than 10% vs teacher/baseline.
req = ModelRoutingRequest(
    purpose=ModelPurpose.LOCAL_ASSIST,
    prefer_local=True,
    max_quality_regression=0.10,
)
result = dispatcher.dispatch(req)
# result.fallback_reason == "relaxed quality tolerance" when every LOCAL
# candidate is below tolerance and the cascade falls through.
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — dispatcher change lives on the Decision side |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — policy reads declared deltas, never mutates them |
| Prefer-LOCAL default preserved | ✅ — `local_bonus` stays first in sort tuple |
| Fallback-cascade termination guaranteed | ✅ — final pass is still cap-free `no-caps` |
| `None`-delta not coerced to `0.0` or invented | ✅ — pass-through (§3.3) and sort-last (§3.5) |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | ✅ — none touched |
| `RoutingAuditor` span schema stable | ✅ — no new keys; existing lineage attrs already carry evidence |
| Capability requirements never relax before quality preference | ✅ — `no-quality` pass sits before `no-caps` |
| Backward compatibility with `DEFAULT_MODELS` | ✅ — `None`-default disables gate; `None`-delta defaults pass through |
| No new runtime / store / heavy dependency | ✅ — stdlib + existing `pydantic.Field` |
| No business logic outside `core/routing/` | ✅ — one file changed |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/routing/dispatcher.py` | +`max_quality_regression` field, +`_effective_quality_delta`, +`_apply_quality`, +`_apply_no_quality`, +`no-quality` cascade pass, +5th `_sort_key` term, updated module docstring |
| `tests/routing/test_dispatcher_quality_policy.py` | new — 22 tests |
| `docs/reviews/phase_quantization_routing_policy_review.md` | this doc |

No service change, no CLI change, no descriptor change, no registry
change, no auditor change, no catalog change.  Implementation lives
in a single file per the inventory's single-diff recommendation.

---

## 7. Test coverage

22 new tests across five classes in
`tests/routing/test_dispatcher_quality_policy.py`:

- **`TestRequestValidation` (5)** — default `None`, accepts `0.0`, accepts `1.0`, rejects negative, rejects `>1.0`.
- **`TestBackwardCompat` (3)** — default catalog dispatch unchanged for CLASSIFICATION / PLANNING / prefer-LOCAL with `max_quality_regression=0.0` (regression guard on real `DEFAULT_MODELS`).
- **`TestQualityFilter` (5)** — measured below tolerance filtered, boundary inclusive, `None`-delta passes, `0.0` tolerance rejects any regression, hosted non-LOCAL always passes.
- **`TestDeltaSourceOrdering` (2)** — distillation overrides quantization when both present, quantization consulted when distillation absent.
- **`TestCascadeOrdering` (4)** — `no-quality` pass wins with correct `fallback_reason`, rank term picks less-bad regression, `no-quality` reached before `no-caps` (capability requirements honoured), caps still relax only in the final pass, empty pool raises.
- **`TestRankTerm` (3)** — better measured delta beats worse, measured beats `None`, rank term subordinate to tier.

Plus: existing `tests/routing/test_routing_dispatcher.py` +
`test_routing_catalog.py` (73 tests) all pass unchanged — the
additive change does not affect the four-pass-equivalent behaviour
when `max_quality_regression=None`.

---

## 8. Test gates

- Focused: `tests/routing/test_dispatcher_quality_policy.py` — **22 passed**.
- Routing suite: `tests/routing/` — **221 passed** (+22; no pre-existing test touched).
- Mandatory canonical suite: **1241 passed, 1 skipped** (unchanged — `tests/routing/` is not in the mandatory list, so the +22 lives outside that count).
- Full suite (`tests/` with `test_*.py`): **1890 passed, 1 skipped** (+22).
- `py_compile core/routing/dispatcher.py` — clean.
- CLI smoke: no CLI change to smoke; the read-only `abrain routing models` surface is policy-unaware by design.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (matches inventory §8 exactly) | ✅ |
| Idempotency rule honoured (no duplicate primitive) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical dispatcher path reinforced | ✅ |
| No business logic outside `core/routing/` | ✅ |
| No Schatten-Wahrheit (policy reads declared deltas, never mutates) | ✅ |
| `None`-delta honesty rule preserved | ✅ |
| Capability requirements never relax before quality | ✅ |
| Backward compatibility with `DEFAULT_MODELS` verified | ✅ |
| Routing suite green (+22) | ✅ |
| Full suite green (+22) | ✅ |
| Documentation consistent with prior five §4 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Phase-4 §263 is now fully closed on `main`: declaration + audit +
inspection + meaningful defaults + policy.  No Phase-4 row remains
open.

Remaining candidates, roughly by leverage:

1. **Phase 6 (Brain v1)** — `ROADMAP_consolidated.md:§Phase 6`.  The
   roadmap has most Phase-6 rows open; the next meaningful step is
   whichever one ships first-class operator reachability to
   `brain` primitives.  Requires its own inventory turn to pick the
   entry point.
2. **Alternative §6.5 green-AI item** — EnergyEstimator per-decision
   metric integration.  Research-shaped; no cheap operator-surface
   win left according to the `phase_routing_models_cli_review.md:§10`
   survey.  Would need its own sub-inventory.
3. **Phase 7** — still blocked on a real-traffic `promote` verdict
   via `abrain brain status`.  Unaffected by this track.

Recommendation: Phase-6 inventory turn next.  Every Phase-4 row is
green; Phase-5 LearningOps rows have existing operator surfaces
shipped over earlier turns; Phase-6 is the next phase with
architectural leverage remaining.

No immediate blockers on `main`.
