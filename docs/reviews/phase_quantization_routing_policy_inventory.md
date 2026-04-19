# Phase 4 — Quantization-aware routing policy — inventory

**Branch:** `codex/phase_quantization_routing_policy_inventory`
**Date:** 2026-04-19
**Scope:** Inventory-only pass. Establishes the exact shape, tolerance
semantics, fallback-cascade interaction, and `None`-delta handling of
a future quantization-aware routing policy before any code lands.  No
`ModelDispatcher` change, no `ModelRoutingRequest` change, no test
change.  This document is the specification the eventual
`codex/phase_quantization_routing_policy` turn will implement against.

---

## 1. Roadmap position

Continuation of Phase 4 §263 (Quantisierungs-/Distillationspfad für
lokale Modelle).  Four prior turns landed the data plane:

| Turn | Commit | Artefact |
|---|---|---|
| §4 inventory | `e7c5cb90` | Three-way split: declaration / policy / pipeline |
| §4 declaration | `037b161e` | `QuantizationProfile` + `DistillationLineage` + advisory |
| §4 audit | `a92b76e3` | Span attributes on `RoutingAuditor` |
| §4 operator surface | `6dd5770b` | `abrain routing models` read-only CLI |
| §4 default catalog | `80b6d6f9` | LOCAL entries declare real quant profiles |

This turn inventories the **policy layer** — the second of three sub-
concerns from the §4 inventory `phase_quantization_inventory.md:§2.2`.
The inventory listed this as "target for a later turn, after §2.1
lands".  Declaration, audit, inspection, and default data are now live
on `main`, so the policy layer is next in line.

The third sub-concern (`§2.3 conversion pipeline`) remains deferred
indefinitely per that inventory; this document does not re-litigate
that decision.

---

## 2. Idempotency check

- `grep -rn "quality_delta_vs_baseline\|quality_delta_vs_teacher"` over
  `core/routing/`, `services/`, `scripts/` — the fields appear only in
  **declaration** (`models.py`, `catalog.py`), **audit**
  (`auditor.py`), and **CLI inventory** (`services/core.py`,
  `scripts/abrain_control.py`).  **No dispatcher consumption**.  Clean
  slate for a policy primitive.
- `grep -rn "prefer_local\|fallback_used"` — dispatcher logic is
  centralised in `core/routing/dispatcher.py` (`_sort_key`,
  `_rank`, the five-pass cascade).  No shadow policy lives
  elsewhere.
- No parallel branch.  No pre-existing half-built policy code.
- `abrain-routing-eval-v3` is referenced only in docstrings, review
  docs, and tests as a **placeholder eval slug**.  There is no real
  eval harness in the repo producing measured `quality_delta_*`
  values; every LOCAL descriptor on `main` either has no delta
  (defaults) or an operator-supplied one.

Consequence: a policy turn would be genuinely new code.  The
inventory-first split is appropriate — unlike the prior four turns,
there is no shape to mechanically follow-through from.

---

## 3. Dispatcher anatomy — where policy could hook in

`core/routing/dispatcher.py` executes a five-pass cascade (`strict` →
`no-latency` → `no-cost` → `no-budget` → `no-caps`) over the purpose-
matching available pool.  Inside each pass, ranking is:

```python
def _sort_key(descriptor, prefer_local):
    local_bonus = 0 if (prefer_local and descriptor.tier == LOCAL) else 1
    tier       = _TIER_ORDER[descriptor.tier]
    cost       = descriptor.cost_per_1k_tokens  or inf
    latency    = descriptor.p95_latency_ms      or inf
    return (local_bonus, tier, cost, latency)
```

Three candidate hook points:

### 3.1 Filter hook (new pre-filter or per-pass filter)

Quality delta treated as a **hard gate** — candidates below tolerance
are dropped from the pool entirely.  Shape analogous to `_apply_cost`
/ `_apply_latency`.

- **Pro**: symmetrical with existing budget filters; easy to unit-
  test; explainable ("candidate removed because
  `quality_delta_vs_teacher=-0.25 < -0.10`").
- **Con**: if the filter drops every LOCAL candidate, the cascade
  falls through to SMALL/MEDIUM, losing the prefer-LOCAL intent.
  Needs a relaxed pass in the cascade (like `no-cost`) to recover.

### 3.2 Rank hook (extend `_sort_key` tuple)

Quality delta treated as a **soft tie-breaker** — added as an extra
term in the sort tuple, so better-quality LOCAL candidates beat
worse-quality LOCAL candidates but the pool is not reduced.

- **Pro**: does not interact with the fallback cascade at all; never
  empties the candidate set; backward compatible when every LOCAL
  descriptor has the same (or `None`) delta.
- **Con**: cannot prevent routing to a LOCAL model whose declared
  regression is unacceptable — the ranker would still pick a
  `quality_delta_vs_teacher=-0.35` LOCAL over a hosted SMALL because
  `local_bonus=0` dominates the tuple.

### 3.3 Combined hook (filter + rank)

Hard tolerance floor removes unacceptable candidates; within the
surviving pool the rank term prefers the less-regressed one.  This is
what the roadmap inventory language ("treat
`quality_delta_vs_teacher` as an additional signal") actually
implies.

- **Pro**: combines the safety of §3.1 with the graceful behaviour of
  §3.2.
- **Con**: more surface area; two knobs to expose on the request.

**Recommendation**: §3.3, but land it in two sub-turns if the diff
grows — first the filter at a relaxed pass in the cascade, then the
rank term.

---

## 4. `None`-delta handling — the central question

The `80b6d6f9` catalog turn committed to `quality_delta_vs_baseline =
None` on every default LOCAL entry, with a notes field telling
operators to re-register with a measured value.  This is a deliberate
honesty decision: ABrain has no CI eval producing measured deltas.

Any policy layer therefore has to decide what to do when the delta is
`None`.  Three options:

### 4.1 Gate on measured values (strict)

`None` → candidate fails the quality filter.

- **Effect on default deployments**: every default LOCAL entry
  disappears from prefer-LOCAL dispatch until an operator re-
  registers with a measured delta.  Rolls back the work of
  `80b6d6f9` and the §4 operator-reachability story for defaults.
- **Verdict**: **rejected**.  Silently demoting three LOCAL entries
  on policy-layer landing breaks the prefer-LOCAL invariant every
  prior review asserted.

### 4.2 Pass-through (permissive)

`None` → candidate passes the quality filter as if tolerance were not
checked.  Policy only gates when a measured delta is present.

- **Effect on default deployments**: behaviour identical to today.
  Operators who *have* run an eval and registered a poor delta get
  the new safety; nobody else is affected.
- **Verdict**: **recommended**.  Matches the catalog's honesty rule
  and the fallback-cascade invariant "unknown budget passes" from
  `_apply_cost`, which already treats unknown cost as passing when
  no budget is set.

### 4.3 Treat as neutral (0.0)

`None` → coerce to `0.0` for comparison purposes.

- **Effect**: indistinguishable from §4.2 for the filter (since
  tolerance is always ≤0.0), but affects the rank term — an
  `None`-delta LOCAL candidate would sort ahead of a measured
  `-0.03` LOCAL candidate, incorrectly preferring the less-known
  artefact.
- **Verdict**: **rejected**.  Coercing unknown to "equal to
  baseline" is a correctness bug, not a policy choice.

**Policy rule**: `None`-delta candidates pass every quality filter
(§4.2) and are ranked *after* measured candidates in the quality term
(opposite convention to cost: unknown cost sorts last because
unknown-cost is a risk; unknown-quality sorts last because measured-
better-quality is preferred).  This is consistent with the §6 ops
layer's treatment of unknown performance samples.

---

## 5. Fallback-cascade interaction

The dispatcher cascade relaxes constraints in a fixed order: latency,
cost, budget, caps.  A new quality constraint must slot in without
breaking the invariant that **the strict pass is the default and the
last pass never raises unless the purpose is genuinely uncovered**.

Proposed cascade after landing the policy:

| Pass | Constraints applied |
|---|---|
| 1  strict  | purpose + avail + caps + cost + latency + **quality** |
| 2  no-latency | purpose + avail + caps + cost + **quality** |
| 3  no-cost | purpose + avail + caps + latency + **quality** |
| 4  no-budget | purpose + avail + caps + **quality** |
| 5  **no-quality** | purpose + avail + caps (new, before `no-caps`) |
| 6  no-caps | purpose + avail |

The new pass 5 relaxes only the quality gate.  Rationale:

- Capability requirements (tool use, structured output) are **safety
  properties** — relaxing them before quality would route a
  classification task to a model that cannot emit the structured
  output the caller requested.  Quality tolerance is a
  *preference*; capabilities are a contract.  Quality must relax
  first.
- Putting quality in a dedicated pass (not folded into `no-budget`)
  keeps the `fallback_reason` text actionable: "relaxed quality
  tolerance" vs "relaxed budget constraints" are very different
  operator signals.

**Auditor impact**: `fallback_reason` strings are already free-text
on `ModelRoutingResult`.  A new `"relaxed quality tolerance"` string
is additive and requires no audit-schema change; the `RoutingAuditor`
already carries `routing.result.fallback_used` and
`routing.result.fallback_reason`.

---

## 6. Request-side shape

The policy needs one new field on `ModelRoutingRequest`.  Two
candidates:

### 6.1 `max_quality_regression: float | None` (recommended)

- Semantic: accept LOCAL candidates whose
  `quality_delta_vs_teacher` (or `.._vs_baseline` when no
  distillation is declared) is ≥ `-max_quality_regression`.
- `None` → no quality gate (default, preserves today's behaviour).
- `0.0` → reject any regression (operator wants parity with
  baseline/teacher).
- `0.1` → reject regressions worse than -10%.
- Naming mirrors the existing `max_cost_per_1k_tokens` /
  `max_p95_latency_ms` budget fields.

### 6.2 `min_quality_delta: float | None` (alternative)

- Semantic: accept candidates with `quality_delta_* ≥
  min_quality_delta`.
- Negative values allowed (e.g., `-0.10` = accept up to 10%
  regression).
- Closer to the underlying field semantics; less mnemonic for
  operators who think in terms of "budget" / "tolerance".

**Recommendation**: §6.1 (`max_quality_regression`).  Matches the
budget-field mental model, keeps `None` as the no-op default, and
produces intuitive values (`0.10` = "tolerate 10% regression").

### 6.3 Which delta field is consulted?

A LOCAL descriptor may declare **both** `quantization.quality_delta_vs_baseline`
and `distillation.quality_delta_vs_teacher`.  Policy rule:

- If `distillation` is present, consult
  `distillation.quality_delta_vs_teacher`.  Distillation is a more
  fundamental transformation than quantization and its teacher is
  the semantic reference point.
- Else if `quantization` is present, consult
  `quantization.quality_delta_vs_baseline`.
- Else (neither declared): treat as `None`-delta (§4.2 rule).

This ordering avoids multi-delta aggregation (which would need a
composition model we do not have) and matches the declaration-layer
invariant that both fields are independently optional.

### 6.4 Non-LOCAL candidates

Hosted SMALL/MEDIUM/LARGE descriptors **must not** declare lineage
(model validator in `core/routing/models.py:_lineage_restricted_to_local_tier`
rejects this).  The policy therefore treats them as `None`-delta and
§4.2 applies — they always pass the quality filter.  This is correct:
hosted models are the reference point, not a regression candidate.

---

## 7. Eval-infrastructure prerequisite

The policy operates on *declared* deltas.  It does **not** compute
them and does **not** require ABrain to run an eval harness.  This is
deliberate:

- Building an eval harness in `core/` would violate "no new runtime".
- Every prior §263 turn explicitly deferred the eval story to an
  operator-side runbook.
- The catalog honesty rule (Turn 9) — "don't commit invented eval
  numbers" — means in practice default deployments run with
  `None`-delta LOCAL models.  Under the §4.2 pass-through rule this
  means the policy has no effect until an operator deploys a
  measured eval, which is the intended workflow.

Therefore: **no eval harness is a prerequisite for the policy turn**.
The policy is a no-op on default deployments and a gate for operators
who have invested in measuring their LOCAL artefacts.  This is
exactly the invariant the catalog turn committed to.

A future, entirely separate turn could add a `abrain routing eval`
harness that populates deltas via a registered eval set — but that is
a §6 green-AI sibling, not a prerequisite for landing this policy.

---

## 8. Proposed minimal policy primitive (spec for the follow-up turn)

**Scope**:
- Add `max_quality_regression: float | None = None` to
  `ModelRoutingRequest` with `ge=0.0, le=1.0`.
- Add `_apply_quality` filter parallel to `_apply_cost` /
  `_apply_latency`.
- Insert `no-quality` pass at position 5 in the cascade.
- Extend `_sort_key` with a fifth term `(quality_penalty)` that
  makes measured-better-quality rank before measured-worse-quality
  and `None`-delta last within each tier.
- Free-text `fallback_reason="relaxed quality tolerance"` when the
  `no-quality` pass wins.
- `RoutingAuditor` unchanged (already emits lineage attributes +
  fallback_reason).
- `RoutingAuditor` span schema unchanged — the existing
  `routing.result.quality_delta_*` keys (landed `a92b76e3`) already
  carry the evidence.

**Non-changes**:
- `ModelDescriptor` / registry / catalog / CLI — untouched.
- `services/core.py` — untouched (read-only CLI surface unaffected).
- `TraceStore` schema — untouched.
- Every prior §4 turn's public surface — untouched.

**Test shape** (target 10–14 new tests in
`tests/routing/test_routing_dispatcher.py` or a new
`test_dispatcher_quality_policy.py`):

1. Default `max_quality_regression=None` → behaviour identical to
   today on the full `DEFAULT_MODELS` catalog (regression guard).
2. Measured-delta candidate below tolerance is filtered out at
   strict pass.
3. Measured-delta candidate equal to `-max_quality_regression`
   passes (boundary inclusive).
4. `None`-delta candidate passes every quality filter (§4.2).
5. Distillation delta overrides quantization delta when both present
   (§6.3).
6. Cascade falls through to `no-quality` when every LOCAL candidate
   is below tolerance; `fallback_reason="relaxed quality tolerance"`
   is set.
7. `no-quality` pass is reached before `no-caps` (order guard).
8. Rank term: measured `-0.02` sorts ahead of measured `-0.15` at
   equal tier/cost/latency.
9. Rank term: measured `-0.02` sorts ahead of `None` at equal
   tier/cost/latency.
10. Hosted non-LOCAL candidate always passes the quality filter
    regardless of `max_quality_regression` (§6.4).
11. Capability requirements never relax before quality (invariant
    guard).
12. `ModelRoutingRequest` pydantic validation rejects
    `max_quality_regression` outside `[0.0, 1.0]`.

---

## 9. Sub-turn split

The diff for §8 is ~80 lines of code + ~200 lines of tests.  Below
the threshold where splitting adds value; recommend landing as a
single `codex/phase_quantization_routing_policy` turn with the full
spec in one commit.

If the filter + rank split becomes necessary (e.g., the rank term's
interaction with `prefer_local` produces surprising ordering in
existing `test_routing_dispatcher.py` tests), split into:

- **5a** `codex/phase_quantization_routing_policy_filter` — filter
  only, no rank-term change.  Preserves every existing
  dispatcher test.
- **5b** `codex/phase_quantization_routing_policy_rank` — adds the
  rank term.

This split decision belongs to the implementation turn, not this
inventory.

---

## 10. Invariants the proposed policy must preserve

| Invariant | How the policy honours it |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | Only the Decision/routing dispatcher changes; no layer boundary crossed |
| `core/routing/` declares facts; dispatcher decides; auditor observes | Policy lives in the dispatcher, not the descriptor; delta values remain declared facts |
| Prefer-LOCAL default preserved | `local_bonus` term stays first in the sort tuple; quality is a subordinate signal |
| Fallback-cascade guarantees termination | New `no-quality` pass inserted before `no-caps`; last pass remains cap-free |
| `None`-delta is not coerced to `0.0` or invented | §4.2 pass-through rule; ranked last instead |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | None touched |
| No new runtime, no new store, no new heavy dependency | Stdlib + pydantic field + existing descriptors |
| No eval harness in `core/` | Policy consumes declared deltas; evaluation is operator-side |
| Backward compatible with existing `DEFAULT_MODELS` | `None`-delta pass-through means defaults dispatch identically |
| `RoutingAuditor` span schema stable | No new keys; `fallback_reason` is already free-text |

---

## 11. Explicit non-goals of the policy turn

| Concern | Status | Reason |
|---|---|---|
| Eval harness populating `quality_delta_*` automatically | Deferred — separate `abrain routing eval` turn | Violates "no new runtime"; operator-side concern |
| Composition of quantization + distillation deltas | Deferred | No composition model exists; §6.3 single-source rule covers the common case |
| `max_quality_regression` surfacing on `api_gateway/` public schema | Deferred — add when first HTTP caller exists | Router is CLI-/internal-only today |
| `abrain routing models --quality-delta-min X` filter | Deferred — low operator value until evals exist | Premature; `--json` already exposes the raw data |
| Per-purpose tolerance (e.g., tighter gate for PLANNING than CLASSIFICATION) | Deferred | Adds a governance policy surface not justified by any current caller |
| Automatic demotion of repeatedly-bad LOCAL artefacts | Deferred to Phase 6/7 | Belongs in the brain's self-reflection layer, not the dispatcher |
| Quality *delta* metric on `RoutingAuditor` fallback traces | Already covered by `a92b76e3` | Span already carries `routing.result.quality_delta_*` |

---

## 12. Test gates for **this inventory turn**

Pure analysis doc.  No code, no new tests.  Required gates:

- Mandatory canonical suite still green (regression guard — no
  accidental side-effects from the catalog turn or earlier).
- Full routing suite still green.
- Markdown renders without broken anchors / tables.

The implementation turn will own its own test gate per the standard
template.

---

## 13. Next step

After this inventory lands on `main`:

1. **`codex/phase_quantization_routing_policy`** — implement §8
   against this specification.  Single diff unless §9's split
   trigger fires.
2. After that: Phase-4 §263 is fully closed; remaining candidates
   per §10 of `phase_default_catalog_lineage_review.md` are a §6
   green-AI research-shaped step (EnergyEstimator per-decision
   metric integration) or Phase-6 (Brain v1).
3. Phase 7 remains blocked on a real-traffic `promote` verdict via
   `abrain brain status` — unaffected by this track.

No immediate blockers on `main`.
