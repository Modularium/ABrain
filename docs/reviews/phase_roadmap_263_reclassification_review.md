# Phase 4 §263 / §6.5 — Roadmap status reclassification

**Branch:** `codex/phase_roadmap_263_reclassification`
**Date:** 2026-04-19
**Scope:** Documentation-only turn.  Rewords two `[ ]` lines in
`docs/ROADMAP_consolidated.md` (Phase 4 line 263, §6.5 line 428) with
honest status suffixes reflecting the split between
*infrastructure-landed* and *operator-side eval pending*.  Does **not**
flip either checkbox — "evaluieren" and "Pfad aufbauen" literally call
for an evaluation result and a live eval pipeline that no code turn
can deliver.

Follows the recommendation in
`phase6_brain_v1_inventory.md:§10 option 1`.

---

## 1. Roadmap position

Two lines were flagged in the Phase-6 inventory turn (`40c80c36`) as
the only remaining code-free architectural loose ends:

- `ROADMAP_consolidated.md:§Phase 4 line 263` — "Quantisierungs- und Distillationspfad für lokale Modelle aufbauen"
- `ROADMAP_consolidated.md:§6.5 line 428` — "Quantisierung/Distillation für lokale Spezialmodelle evaluieren"

Both are covered — *architecturally* — by the six-turn Phase-4 §263
series.  Neither is covered *operationally* (no benchmark run, no
measured `quality_delta_*` registered on any default descriptor).

---

## 2. Idempotency check

- `grep -n "Quantisierung" docs/ROADMAP_consolidated.md` before this
  turn — two hits, both unflipped `[ ]` lines.
- No pre-existing `phase_roadmap_263_reclassification*.md`.
- No parallel branch with the same scope.

Consequence: fully additive, doc-only edit.

---

## 3. Framing choice — honest suffix, not checkbox flip

Two options were considered (per the prior turn's §10 recommendation):

1. **Mark both `[x]` with cross-reference.**  Rejected: "evaluieren"
   asks for an eval *result*, not an eval *surface*.  Flipping the
   box would create a Schatten-Wahrheit — a checked line whose
   claim ("evaluiert") is false (nothing has been evaluated yet on
   real LOCAL hardware).
2. **Keep `[ ]` with a status suffix.**  Chosen.  Honest about what
   is landed (infrastructure) and what is not (eval execution).
   Preserves the `None`-delta honesty rule established in Turn 9 and
   re-asserted in the Turn-10 policy inventory.

---

## 4. Edits

### 4.1 Phase 4 line 263

Before:
```
- [ ] Quantisierungs- und Distillationspfad für lokale Modelle aufbauen — *deferred zusammen mit §6.5 Green-AI-Items*
```

After:
```
- [ ] Quantisierungs- und Distillationspfad für lokale Modelle aufbauen — *Infrastruktur gelandet (declaration/audit/CLI/defaults/policy-inventory/policy: `037b161e`, `a92b76e3`, `6dd5770b`, `80b6d6f9`, `a0c9486c`, `7d531220`); Eval-Ausführung bleibt operator-seitig (siehe `phase_quantization_inventory.md`, `phase_quantization_routing_policy_review.md`)*
```

### 4.2 §6.5 line 428

Before:
```
- [ ] Quantisierung/Distillation für lokale Spezialmodelle evaluieren
```

After:
```
- [ ] Quantisierung/Distillation für lokale Spezialmodelle evaluieren — *Eval-Infrastruktur gelandet (siehe §Phase 4 §263); offene Arbeit ist operator-seitig: reale Benchmarks laufen lassen und `quality_delta_vs_baseline` / `quality_delta_vs_teacher` in `QuantizationProfile` / `DistillationLineage` registrieren*
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — doc only |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — nothing touched |
| `None`-delta honesty rule preserved | ✅ — suffix framing matches the Turn-9 honesty rule |
| No Schatten-Wahrheit introduced | ✅ — boxes stay `[ ]` until an eval actually ships |
| No new runtime / store / heavy dependency | ✅ — doc only |
| Idempotency rule honoured | ✅ — no duplicate suffix; no silent [x] flip |

---

## 6. Artifacts

| File | Change |
|---|---|
| `docs/ROADMAP_consolidated.md` | two single-line suffix edits (lines 263, 428) |
| `docs/reviews/phase_roadmap_263_reclassification_review.md` | this doc |

No code change, no test change, no schema touch, no service/CLI
touch, no box-flip.

---

## 7. Test gates

Documentation-only turn.  Required regression guards:

- Mandatory canonical suite: unchanged from Turn 12 (`40c80c36`).
- Full suite (`tests/` with `test_*.py`): unchanged from Turn 12
  (1890 passed, 1 skipped).

No new tests; this turn writes no code.

---

## 8. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (matches `phase6_brain_v1_inventory.md:§10 option 1`) | ✅ |
| Framing choice documented (§3 — honest suffix, not box-flip) | ✅ |
| Idempotency rule honoured (no duplicate suffix) | ✅ |
| No parallel structure introduced | ✅ |
| No code change, no Schatten-Wahrheit introduced | ✅ |
| Mandatory suite unchanged (regression guard) | ✅ |
| Full suite unchanged (regression guard) | ✅ |
| **Merge-ready** | ✅ |

---

## 9. Next step

Per the Phase-6 inventory's remaining options:

- **(B) next turn:** `codex/phase_green_energy_per_decision_inventory`
  — analysis-only sub-inventory for EnergyEstimator per-decision
  metric integration.  Research-shaped §6.5 item; genuinely adds
  observability; not blocked on real traffic.
- **(C) non-code / operational:** running Brain-v1 in real-traffic
  shadow mode to produce a `promote`-verdict via
  `BrainOperationsReporter` — unblocks Phase 6 E1/E3 + Phase 7.
  Cannot be executed inside this session.

No immediate blockers on `main`.
