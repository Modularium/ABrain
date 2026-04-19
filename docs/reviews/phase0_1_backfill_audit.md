# Phase 0 / Phase 1 Backfill Audit

**Branch:** `codex/phase0-doc-backfill-audit`
**Date:** 2026-04-19
**Scope:** Confirm that every roadmap task under *Phase 0 – Konsolidierung abschließen* and *Phase 1 – Evaluierbarkeit als Produktfeature* from `docs/ROADMAP_consolidated.md` is closed on `main` before continuing Brain work in Phase 7 or any Querschnitts-Workstream.

---

## 1. Why this audit now

Phase 6 (`B6-S1` … `B6-S6`) is end-to-end on main (commit `922dac3d`). The roadmap priority order (§7) is strict:

> 1. Phase 0 – Konsolidierung abschließen
> 2. Phase 1 – Evaluierbarkeit / Replay / Compliance
> ...
> 8. Phase 7 – fortgeschrittenes Entscheidungsnetzwerk

Before opening Phase 7 or moving to a cross-cutting workstream, the earlier phases must be confirmed complete. This audit maps every checklist item in Phase 0 and Phase 1 to its canonical implementation on main, or flags a concrete gap.

**No new production code changed.** This turn only fixed a small set of dead documentation pointers that remained as a Phase-0 cleanup residue (see §4).

---

## 2. Phase 0 – Konsolidierung abschließen

### Task-by-task mapping

| Roadmap task | Canonical implementation on main | Source of truth |
|---|---|---|
| Kanonische Kernarchitektur dokumentieren | `docs/architecture/CANONICAL_REPO_STRUCTURE.md`, `CANONICAL_RUNTIME_STACK.md`, `PROJECT_OVERVIEW.md` | `docs/architecture/` |
| Parallele Routing-/Decision-/Approval-/Execution-Pfade inventarisieren | Phase O full-repo inventory + canonicalization cleanup | `docs/reviews/phaseO_full_repo_inventory.md`, `phaseO_canonicalization_cleanup_review.md` |
| Pending Approvals persistent | `ApprovalStore` SQLite backend | `core/approval/`, `tests/state/test_approval_store_persistence.py` |
| PlanState persistent | `PlanState` SQLite backend | `core/orchestration/plan_state.py`, `tests/state/test_plan_state_persistence.py` |
| Performance-/Feedback-/Training-Daten versioniert | `PerformanceHistoryStore` + LearningOps dataset exporter | `core/decision/performance_history.py`, `core/decision/learning/dataset_exporter.py` (P5-L2) |
| Sicherheitsrelevante Defaults vereinheitlichen | Phase S21 security boundary + enforcement tests | `tests/governance/test_security_enforcement.py`, `docs/reviews/phaseS21_security_tests_review.md` |
| Konfigurationspfade vereinheitlichen (`.env`, YAML, runtime) | `core/config.py` central loader | `core/config.py` |
| Logging, Trace-IDs, Audit-Korrelation vereinheitlichen | `TraceStore` + `TraceContext` as single audit source of truth | `core/audit/trace_store.py`, `core/audit/context.py` |
| Historische Roadmap-/README-Aussagen gegen realen Code abgleichen | **This turn** — see §4 | `ROADMAP.md`, `Roadmap.md`, `README.md` |
| "Coming soon"-/Pseudocode-/Placebo-Doku entfernen oder markieren | Clean (`grep` over `core/`, `services/`, `api_gateway/`, `scripts/` finds none) | repo-wide scan |
| CI-Minimum (lint, typecheck, unit, integrations, smoke) | `.github/workflows/core-ci.yml` (Phase S13) | `docs/reviews/phaseS13_ci_gates_review.md` |

### Exit-Kriterien check

| Exit criterion | Status |
|---|---|
| Keine unbekannten parallelen Kernpfade | ✅ — Phase O consolidation closed, `services/core.py` is the single wiring point |
| Kein kritischer Laufzeitstate nur im RAM | ✅ — `ApprovalStore`, `PlanState`, `PerformanceHistoryStore`, `TraceStore` all SQLite-backed (Phase N) |
| Alle sicherheitsrelevanten Kernpfade testbar und dokumentiert | ✅ — `tests/governance/`, `tests/approval/`, `tests/execution/` cover policy catalog, approval transitions, adapter manifests, budgets |
| Klare Trennung zwischen historischer und aktueller Doku | ✅ after this turn — dead pointer `docs/roadmap.md` replaced with `docs/ROADMAP_consolidated.md` in `ROADMAP.md` + `Roadmap.md`; `README.md` roadmap section re-pointed |

**Phase 0 verdict: CLOSED on main.**

---

## 3. Phase 1 – Evaluierbarkeit als Produktfeature

### Task-by-task mapping

| Roadmap task | Canonical implementation on main | Source of truth |
|---|---|---|
| Replay-Harness auf Basis gespeicherter Traces | `core/evaluation/harness.py` (`TraceEvaluator`) | `docs/reviews/phaseS11_replay_compliance_review.md`, commit `a4acd16b` |
| "expected vs actual" für Routing-Entscheide | `RoutingReplayVerdict` enum + `RoutingReplayResult` model | `core/evaluation/models.py` |
| Policy-Testkatalog (deny / approval_required / allow) | `tests/governance/test_policy_catalog.py` — 57 parametrized tests | `docs/reviews/phaseS12_policy_catalog_review.md` |
| Approval-Transition-Tests | full state-machine coverage in `tests/state/` + `tests/approval/` | `docs/reviews/phaseS12_policy_catalog_review.md` |
| Adapter-Output-Snapshots für Regressionstests | `tests/execution/test_execution_result_contracts.py` — 45 tests | `docs/reviews/phaseS13_ci_gates_review.md` |
| Routing-Baseline-Metriken (Erfolgsrate, Fehlrouting, P95-Latenz, Kosten, Fallbacks) | `BatchEvaluationReport` + Phase S14 safety-metrics / routing KPIs | `core/evaluation/models.py`, `docs/reviews/phaseS14_safety_metrics_routing_kpis_review.md` |
| Safety-Metriken (Compliance-Rate, unerlaubte Side-Effects, falsche Tool-Aufrufe, Approval-Bypass) | Phase S14 batch-baseline safety metrics + Phase S21 enforcement tests | `docs/reviews/phaseS14_safety_metrics_routing_kpis_review.md`, `phaseS21_security_tests_review.md` |
| CI-Gates für Replay und Compliance | `.github/workflows/core-ci.yml` gates `tests/state`, `tests/governance`, `core/evaluation/*` on every PR | `docs/reviews/phaseS13_ci_gates_review.md` |

### Exit-Kriterien check

| Exit criterion | Status |
|---|---|
| Jede relevante Kernänderung kann gegen gespeicherte Fälle geprüft werden | ✅ — `TraceEvaluator` replays stored traces against current `RoutingEngine` + `PolicyEngine` |
| Policy-Regressionen werden vor Merge sichtbar | ✅ — `core/evaluation/` is syntax-checked and `tests/governance/` runs in `core-ci.yml` on every PR |
| Belastbarer Vorher-/Nachher-Vergleich für spätere ML-Schritte | ✅ — `BatchEvaluationReport` + `BrainBaselineAggregator` (B6-S5) provide this for the Brain pipeline |

**Phase 1 verdict: CLOSED on main.**

---

## 4. Concrete gap found in this audit — and closed

Three stale documentation pointers remained as a Phase-0 residue:

| File | Line(s) | Problem | Fix in this turn |
|---|---|---|---|
| `ROADMAP.md` | 3–4, 6 | Referenced `docs/roadmap.md` as the "kompakte Übersicht" — **file no longer exists** | Re-pointed to `docs/ROADMAP_consolidated.md` |
| `Roadmap.md` | 2–4 | Same dead `docs/roadmap.md` reference | Re-pointed to `docs/ROADMAP_consolidated.md` |
| `README.md` | 291–297 | "Roadmap" section listed five unchecked boxes for features that have shipped (persistent state, governance engine, UI, plugin system) | Replaced the stale checklist with a pointer to the canonical roadmap + archival pointers to the two historical files |

All three changes are pure documentation. No production code or tests touched. The historical review docs under `docs/reviews/phaseM_ui_inventory_and_selection.md`, `phaseR/phaseR_sources_and_scope.md`, `repo_harmonization_audit.md` that still mention `docs/roadmap.md` are **frozen history** and intentionally left untouched — their validity is bounded to their review date.

---

## 5. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel router / runtime / orchestrator introduced | ✅ — doc-only change |
| No second TraceStore / ModelRegistry / policy stack | ✅ |
| No business logic in CLI/UI/OpenAPI | ✅ |
| No hidden Legacy-Reaktivierung | ✅ — stale pointers re-routed forward, not resurrected |
| Additive only | ✅ — one audit doc + three pointer fixes |
| No new dependencies | ✅ |

---

## 6. Test gate

No code changed; re-ran the mandatory suite to confirm no incidental regression from doc edits:

- Mandatory suite (`tests/state tests/mcp tests/approval tests/orchestration tests/execution tests/decision tests/adapters tests/core tests/governance tests/services tests/integration/test_node_export.py`): green.
- Full suite (`tests/`): 1524 passed, 1 skipped — unchanged from post-B6-S6 baseline.

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (audit + minimal doc-gardening) | ✅ |
| No parallel structure | ✅ |
| Canonical paths reinforced | ✅ |
| No new shadow source-of-truth | ✅ |
| Tests green | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Recommendation for next step

With Phase 0 and Phase 1 confirmed closed on main, and Phase 6 (Brain v1) end-to-end, the next candidates by roadmap priority are:

1. **Phase 2, 3, 4, 5 — spot-check audit** (analogous to this one) before opening Phase 7. Based on commit history (`S15`–`S21` Phase 2, `R1`–`R6` Phase 3, `M1`–`M4` Phase 4, `L1`–`L5` Phase 5, `B1`–`B6` Phase 6), all core phases appear closed — but a short confirmation audit per phase is prudent.

2. **Querschnitts-Workstreams (§6)** — the roadmap lists security (§6.1), documentation (§6.2), observability (§6.3), data governance (§6.4), efficiency / Green AI (§6.5) as cross-cutting workstreams. A good first pick is **§6.3 Observability**: a small operator surface that aggregates Brain baseline + suggestion feed output into a single report, since Phase 6 is now the newest moving part.

3. **Phase 7 – Fortgeschrittenes Brain** — only after (a) a real-traffic baseline run produces a `promote` verdict and (b) all earlier-phase audits are clean.

**Recommendation:** proceed with a Phase 2–5 spot-check audit in the next turn (short, doc-producing, read-only), then pick the first Querschnitts-Workstream. Phase 7 stays deferred until Brain has real-traffic validation.
