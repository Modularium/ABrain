# §6.5 Green AI — per-decision energy signal inventory (review)

**Branch:** `codex/phase_green_energy_per_decision_inventory`
**Date:** 2026-04-19
**Scope:** Analysis-only wrapper for
`docs/reviews/phase_green_energy_per_decision_inventory.md`.  No
code change, no test change.

---

## 1. Roadmap position

Follows `phase_roadmap_263_reclassification_review.md:§9 option B`:
after reclassifying the §263 / §6.5 "evaluieren" lines with an
honest status suffix, the remaining architectural leverage on the
§6.5 track is to promote the existing `EnergyEstimator` from a
per-agent aggregate report to a per-decision signal on
`RoutingAuditor` spans and (optionally) a dispatcher sort/filter
input.  This doc specifies that turn.

---

## 2. Idempotency check

- `grep -i 'energy\|watt\|joule' core/routing/` — zero hits.  No
  existing per-decision energy primitive.
- `phase_green_energy_estimator_review.md` landed the per-agent
  aggregate surface; `phase_ops_energy_cli_review.md` landed the
  operator-facing `abrain ops energy` read surface.  Neither touches
  the dispatch path.
- No pre-existing `phase_green_energy_per_decision*.md` on `main`.
- No parallel branch.

Consequence: additive, doc-only landing.

---

## 3. What the inventory establishes

See `phase_green_energy_per_decision_inventory.md` — summarised:

- **Three candidate hook points** (auditor-only, dispatcher filter,
  dispatcher rank).  Recommendation: combined, mirroring Turn 11.
- **Per-decision formula**: `joules = p95_latency_ms/1000 × watts`.
  Uses `p95_latency_ms` (not `avg_latency`) so the dispatcher
  filters on the same latency signal as the energy estimate.
- **Three wattage-source options** (embed on descriptor, dispatcher
  table, per-call config).  Recommendation: embed on
  `ModelDescriptor` (option 5.1) for single-source-of-truth.
- **`None`-wattage / `None`-p95 rule**: unknown energy → filter
  pass-through, sort-last.  Same honesty rule as Turn 9 and Turn 11.
- **Cascade extension**: `no-energy` pass inserted before `no-caps`,
  mirroring the Turn-11 `no-quality` pass.  Seven-pass cascade.
- **Twelve non-goals** keep scope bounded (no gCO₂/kWh, no
  J/token model, no auto-demotion, etc.).
- **Single-diff implementation spec** (§8) enumerates exact file
  touches, test cases, and expected diff size (~60 dispatcher +
  ~30 auditor + ~5 model + ~200 tests).

---

## 4. Invariants preserved (by the inventory doc itself)

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — doc only |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — spec mirrors layering |
| No new runtime / store / heavy dependency | ✅ — doc only |
| `ModelDispatcher` stays the sole routing decision point | ✅ |
| `None`-signal not coerced to `0.0` or invented | ✅ — §4 + §3.2 + §3.3 rules |
| Prefer-LOCAL default preserved | ✅ — `local_bonus` stays first |
| Backward compatibility with `DEFAULT_MODELS` | ✅ — gate off by default |
| `EnergyEstimator` read-only property preserved | ✅ — §7 non-goal #12 |
| Idempotency rule honoured | ✅ — no duplicate inventory doc |

---

## 5. Artifacts

| File | Change |
|---|---|
| `docs/reviews/phase_green_energy_per_decision_inventory.md` | new, 13 sections |
| `docs/reviews/phase_green_energy_per_decision_inventory_review.md` | this doc |

No code change, no test change, no schema touch, no service/CLI
touch.

---

## 6. Test gates

Analysis-only turn.  Required regression guards:

- Mandatory canonical suite: unchanged from Turn 13 (`5014ec16`).
- Full suite (`tests/` with `test_*.py`): unchanged — 1890 passed,
  1 skipped.

No new tests; this turn writes no code.

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (analysis-only, per `phase6_brain_v1_inventory.md:§10 option 2`) | ✅ |
| Idempotency rule honoured | ✅ |
| No parallel structure introduced | ✅ |
| No code change, no Schatten-Wahrheit introduced | ✅ |
| Spec explicitly preserves every §263 invariant | ✅ |
| `None`-signal honesty rule recorded | ✅ |
| Three hook-point options and three wattage-source options enumerated | ✅ |
| Mandatory suite green | ✅ |
| Full suite green | ✅ |
| Documentation consistent with §263 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

Per `phase_green_energy_per_decision_inventory.md:§13`:

1. `codex/phase_green_energy_per_decision` — implement the §8 spec
   as a single diff.
2. Operational (non-code): real-traffic Brain-v1 shadow mode to
   produce `promote`-verdict via `BrainOperationsReporter` —
   unblocks Phase 6 E1/E3 and the deferred Phase 7.
3. Optional follow-up: wattage allow-list in `abrain routing models`
   CLI.

No immediate blockers on `main`.
