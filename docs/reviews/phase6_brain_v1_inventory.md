---
name: Phase 6 — Brain v1 inventory
description: Status survey of Phase 6 (ABrain Brain v1). Confirms all six Aufgaben are landed on `main`; remaining work is exit-criterion-only and blocked on real traffic.
type: inventory
---

# Phase 6 — Brain v1 inventory

**Branch:** `codex/phase6_brain_v1_inventory`
**Date:** 2026-04-19
**Scope:** Analysis-only survey of Phase 6 (`ROADMAP_consolidated.md:§Phase 6`
lines 306–354).  Goal: pick the next meaningful entry point
(Brain-primitive landing, operator surface, KPI integration, …) for a
subsequent implementation turn, as recommended by the prior turn's
`phase_quantization_routing_policy_review.md:§10`.

This doc records the finding that no such entry point exists — every
Aufgabe under Phase 6 is already [x] on `main`, and the two remaining
exit criteria are blocked on the same real-traffic verdict that gates
Phase 7.

---

## 1. Roadmap position

Phase 6 (`ROADMAP_consolidated.md:§Phase 6`) is the "kleines neuronales
Entscheidungsnetzwerk" phase — Brain v1 as a proposal-only decision
model under governance, not a policy replacement.  The roadmap lists
six Aufgaben and three exit criteria (lines 331–354).

The prior turn's review doc
(`phase_quantization_routing_policy_review.md:§10`) recommended a
Phase-6 inventory turn as the next meaningful step after Phase 4 §263
closed.  This doc answers that recommendation.

---

## 2. Idempotency check

- `ls docs/reviews/ | grep phase6` — eight existing review docs on
  `main`: `phase6_B1_review.md`..`phase6_B6_review.md`,
  `phase6_brain_cli_review.md`, `phase6_obs_report_review.md`.
- No pre-existing `phase6_brain_v1_inventory.md` on `main`.
- No parallel branch with the same scope.

Consequence: additive, documentation-only landing.  The inventory
itself is new; the phase it inventories is mostly closed.

---

## 3. What the roadmap says (verbatim status quotes)

From `ROADMAP_consolidated.md` lines 331–354:

### Aufgaben (§Phase 6, lines 333–348)

| # | Aufgabe | Status | Review doc |
|---|---|---|---|
| A1 | Zielvariablen des Decision-Netzes formalisieren | [x] | `phase6_B1_review.md` |
| A2 | Zustandsrepräsentation definieren (Task / Kontext / Budget / Policy / Verlauf / Performance-Historie) | [x] | `phase6_B1_review.md`, `phase6_B4_review.md` |
| A3 | Trainingsziele definieren (Top-k Routing Accuracy / Policy-Compliance / Cost-aware / Escalation) | [x] | `phase6_B2_review.md` |
| A4 | Shadow-Mode für Brain-v1 einführen | [x] | `phase6_B5_review.md`, `phase6_B6_review.md` |
| A5 | Brain-v1 gegen heuristische Baseline evaluieren | [x] | `phase6_B6_review.md`, `phase6_obs_report_review.md` |
| A6 | Brain-v1 nur als Vorschlagsmodell ausrollen, nicht als Policy-Ersatz | [x] | `phase6_B5_review.md` |

**All six Aufgaben are [x] on `main`.**

### Exit-Kriterien (§Phase 6, lines 352–354)

| # | Exit-Kriterium | Status |
|---|---|---|
| E1 | Decision-Netzwerk reproduzierbar besser als Baseline in klar definierten Metriken | [ ] — *pending: Real-Traffic `promote`-Verdict durch `BrainOperationsReporter`* |
| E2 | keine Verletzung von Safety- oder Governance-Invarianten | [x] |
| E3 | reduziert Fehlrouting, unnötige Kosten oder unnötige Genehmigungen messbar | [ ] — *pending: Real-Traffic-Daten* |

E1 and E3 are both gated on the same signal: a real-traffic
`promote`-verdict from `BrainOperationsReporter`.  That is a *data*
dependency, not an architectural one.  No code turn can close it.

### Phase 7 (§Phase 7, line 360)

> **Status (2026-04-19):** Deferred. Erst eröffnet, wenn der Real-Traffic-`promote`-Verdict aus `BrainOperationsReporter` (Phase 6 Exit) vorliegt.

Phase 7 shares the identical blocker.

---

## 4. Candidate entry points — honest assessment

The Turn-12 request proposed three candidate scopes.  Each is dead:

### 4.1 Brain-primitive landing

**Dead.**  A1/A2/A3 are [x].  The targets, state representation, and
training objectives are already formalised under
`phase6_B1_review.md`/`phase6_B2_review.md`/`phase6_B4_review.md`.  No
primitive remains to land.

### 4.2 Operator surface

**Dead.**  `phase6_brain_cli_review.md` already exists on `main` and
covers operator reachability to the Brain-v1 surface.  A4 (shadow
mode) and A5 (baseline evaluation) are [x].  Operators can already
invoke and inspect Brain-v1 through `abrain brain …`.

### 4.3 KPI integration

**Dead.**  A5 (baseline eval) and `phase6_obs_report_review.md` ship
Brain-v1 vs baseline metrics through `BrainOperationsReporter`.
`ROADMAP_consolidated.md:§6.3 line 414` records the dashboard
integration as [x].  Further KPI work waits on *data*, not code.

---

## 5. Adjacent finding — §6.5 line 428

`ROADMAP_consolidated.md:§6.5 line 428`:

> [ ] Quantisierung/Distillation für lokale Spezialmodelle evaluieren

This is the only [ ] cross-cutting row remaining under §6.  It is
also the exact subject of the six-turn Phase-4 §263 series that just
closed on `main`:

| Turn | Commit | Surface |
|---|---|---|
| inventory | (pre-series) | three-way split |
| declaration | `037b161e` | `QuantizationProfile` + `DistillationLineage` |
| audit | `a92b76e3` | span attributes on `RoutingAuditor` |
| operator surface | `6dd5770b` | `abrain routing models` CLI |
| default catalog | `80b6d6f9` | LOCAL defaults declare real quant profiles |
| policy inventory | `a0c9486c` | spec for policy layer |
| policy | `7d531220` | dispatcher consumes declared deltas |

Strictly, the §6.5 line says "evaluieren" (evaluate).  The §263
series delivered **declaration + audit + inspection + default data +
policy** — every architectural surface required to support an
evaluation.  The evaluation itself (i.e. running LOCAL models against
a benchmark and registering measured `quality_delta_vs_*` values) is
an *operator-side* activity per the Turn-9 honesty rule and the
Turn-10 inventory (`None`-delta pass-through).

**Honest read:** §6.5 line 428 is now an *operator task*, not an
*architectural task*.  Every hook the operator needs is landed.  The
line should either be tagged [x] with a cross-reference to the §263
series, or reworded to "Evaluationsinfrastruktur für
Quantisierung/Distillation bereitstellen" and then tagged [x].  A
tiny doc-only turn could make this edit — lowest leverage available,
but available.

---

## 6. Invariants preserved (by this inventory doc itself)

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — doc only |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — nothing touched |
| No new runtime / store / heavy dependency | ✅ — doc only |
| `ModelDispatcher` stays the sole routing decision point | ✅ — nothing touched |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | ✅ — nothing touched |
| Idempotency rule honoured | ✅ — no duplicate primitive; this is the first Phase-6 inventory |

---

## 7. Artifacts

| File | Change |
|---|---|
| `docs/reviews/phase6_brain_v1_inventory.md` | new — this doc |
| `docs/reviews/phase6_brain_v1_inventory_review.md` | new — wrapper |

No code change, no test change, no service/CLI touch, no schema
touch, no roadmap edit.  An optional follow-up doc turn could update
§6.5 line 428 (see §5); that decision is left to the next turn.

---

## 8. Test gates

Analysis-only turn.  Required regression guards:

- Mandatory canonical suite: unchanged from Turn 11 (`7d531220`).
- Full suite (`tests/` with `test_*.py`): unchanged from Turn 11
  (1890 passed, 1 skipped).

No new tests; this turn writes no code.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (analysis-only survey of Phase 6) | ✅ |
| Idempotency rule honoured (no duplicate inventory doc) | ✅ |
| No parallel structure introduced | ✅ |
| No code change, no Schatten-Wahrheit introduced | ✅ |
| Every prior Phase-6 review doc accounted for | ✅ |
| §6.5 line 428 overlap with §263 series flagged, not silently edited | ✅ |
| Mandatory suite unchanged (regression guard) | ✅ |
| Full suite unchanged (regression guard) | ✅ |
| Documentation consistent with prior turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Phase 6 is architecturally closed.  Phase 7 is deferred on the same
blocker (real-traffic `promote`-verdict).  Phase 5 LearningOps rows
are all [x].  Phase 4 §263 closed in the just-completed six-turn
series.

Remaining candidates, roughly by leverage:

1. **Tiny doc turn — §6.5 line 428 reclassification.**  Update
   `ROADMAP_consolidated.md:§6.5 line 428` to [x] with cross-reference
   to the §263 commits, OR reword to reflect the
   architectural-vs-operator split.  Lowest leverage on the board,
   but the only code-free architectural loose end.
2. **EnergyEstimator per-decision metric integration.**  Research-
   shaped §6.5 item (cited by `phase_routing_models_cli_review.md:§10`
   and `phase_quantization_routing_policy_review.md:§10`).  Would
   need its own sub-inventory.  Genuinely adds new observability; not
   blocked on real traffic.
3. **Real-traffic unblock for Phase 6 E1/E3 + Phase 7 opening.**  Not
   a code turn — an operational turn requiring live traffic routed
   through Brain-v1 shadow mode.

**Recommendation:** option 1 (tiny doc turn) if consistency matters,
option 2 (EnergyEstimator integration inventory) if architectural
leverage matters.  Either is legitimate.  Neither is urgent.

No immediate blockers on `main`.
