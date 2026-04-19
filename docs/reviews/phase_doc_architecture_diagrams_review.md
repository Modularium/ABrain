# §6.2 Documentation — Architecture diagrams review

**Branch:** `codex/phase_doc_architecture_diagrams`
**Date:** 2026-04-19
**Scope:** Pure doc turn. One new page
(`docs/architecture/ARCHITECTURE_DIAGRAMS.md`) with three Mermaid
diagrams for the three canonical flows — Kernpfad, Plugin-Pfad,
LearningOps — plus the ROADMAP ☑.

Closes the §6.2 *"Architekturdiagramme für Kernpfad, Plugin-Pfad,
LearningOps"* line item.

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md` §6.2 before this turn:

- [x] klare Trennung: historisch / aktuell / experimentell
- [ ] **Architekturdiagramme für Kernpfad, Plugin-Pfad, LearningOps** ← this turn
- [x] Dokumentation pro kanonischem Pfad (`docs/architecture/*`, …)
- [x] Experimente explizit als solche kennzeichnen
- [x] falsche oder veraltete Implementierungsbehauptungen entfernen

The prior turn's recommendation was verbatim:

> "§6.2 *'Architekturdiagramme für Kernpfad, Plugin-Pfad, LearningOps'*
>  — a pure doc turn using the same inventory pattern as the
>  `phase_doc_audit_*` series. Low risk, high onboarding value."

That is exactly this turn.

### Idempotency check

- `grep -i 'mermaid|flowchart|sequenceDiagram'` across
  `docs/architecture/` before this turn: **zero hits**. Every existing
  architecture doc was prose-only; no parallel diagram file to
  reconcile.
- Prose per-layer docs already exist:
  `DECISION_LAYER_AND_NEURAL_POLICY.md`, `HITL_AND_APPROVAL_LAYER.md`,
  `EXECUTION_LAYER_AND_AGENT_CREATION.md`,
  `AUDIT_AND_EXPLAINABILITY_LAYER.md`, `MULTI_AGENT_ORCHESTRATION.md`.
  This turn adds the missing visual index page; it does not rewrite or
  parallelise the prose.
- No parallel branch tracks this scope.

---

## 2. Approach

One page, three `flowchart LR` diagrams, each with:

- node labels that name the **actual** module path + class the flow
  passes through (not an idealised sketch);
- cylinder nodes (`[(...)]`) for the four canonical stores
  (`TraceStore`, `PerformanceHistoryStore`, `ApprovalStore`,
  `PlanStateStore`) so the "single source of truth" invariants are
  visually obvious;
- an invariants subsection after each diagram that spells out which
  architectural rule the diagram is pinning.

Mermaid was chosen because the existing `mkdocs.yml` already renders
GitHub-flavoured markdown and Mermaid sources diff cleanly in
code-review — no binary image drift, no separate asset pipeline.

All file paths and class names were verified against `main`:

```
core/decision/planner.py      Planner.plan()              ✓
core/decision/routing_engine.py RoutingEngine             ✓
core/decision/neural_policy.py NeuralPolicyModel          ✓
core/approval/policy.py       ApprovalPolicy.evaluate()   ✓
core/approval/store.py        ApprovalStore               ✓
core/execution/execution_engine.py ExecutionEngine        ✓
core/execution/dispatcher.py  Dispatcher                  ✓
core/execution/adapters/registry.py ExecutionAdapterRegistry ✓
core/execution/adapters/{6 adapters}                      ✓
core/execution/adapters/{manifest,validation,budget,policy_bindings}.py ✓
core/execution/provider_capabilities.py ProviderCapabilities ✓
core/audit/trace_store.py     TraceStore                  ✓
core/audit/context.py         create_trace_context()      ✓
core/audit/pii.py             PiiDetector                 ✓
core/audit/retention.py       RetentionScanner            ✓
core/retrieval/provenance.py  ProvenanceScanner           ✓
core/decision/learning/*.py   LearningRecord, DatasetBuilder,
                              DataQualityFilter, DatasetExporter,
                              DatasetSplitter, OfflineTrainer,
                              ModelRegistry, ShadowEvaluator ✓
core/decision/performance_history.py PerformanceHistoryStore ✓
core/decision/performance_report.py  AgentPerformanceReporter ✓
core/decision/energy_report.py       EnergyEstimator          ✓
core/orchestration/orchestrator.py PlanExecutionOrchestrator ✓
core/orchestration/state_store.py  PlanStateStore            ✓
```

If any of these rename or move, this doc ships with the same commit
that renames them — the diagrams are code, not wallpaper.

---

## 3. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel architecture docs | ✅ — single visual index page; prose per-layer docs unchanged |
| Canonical file paths referenced | ✅ — every class/path verified against `main` |
| No new source-of-truth | ✅ — diagrams point to existing stores only |
| No code changes | ✅ — doc-only turn |
| No new dependencies | ✅ — inline Mermaid in markdown |
| Additive only | ✅ — one new `.md`, one ROADMAP line |

---

## 4. Artifacts

| File | Purpose |
|---|---|
| `docs/architecture/ARCHITECTURE_DIAGRAMS.md` | 3 Mermaid diagrams + invariants + maintenance note |
| `docs/ROADMAP_consolidated.md` | §6.2 diagram line ☑ |
| `docs/reviews/phase_doc_architecture_diagrams_review.md` | this doc |

No code files were modified; no tests were added. The suite is
unaffected by design.

---

## 5. Suites

Although this is a doc-only turn, the mandatory canonical suite was
re-run to confirm no regression crept in from the prior turn:

- Mandatory canonical (`tests/state tests/mcp tests/approval
  tests/orchestration tests/execution tests/decision tests/adapters
  tests/core tests/governance tests/services
  tests/integration/test_node_export.py`): **1184 passed / 1 skipped**
  — unchanged vs. the §6.5 energy-estimator turn.

No new tests were added: there is nothing new to assert at runtime.

---

## 6. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (three diagrams for three flows) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical paths referenced | ✅ |
| No hidden legacy reactivation | ✅ |
| No second source-of-truth | ✅ |
| Tests green (baseline unchanged) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Next step

§6.2 Dokumentation is now closed — all five sub-items are ☑.

**Recommendation for the next turn:** Phase 6 Brain-v1 **B6-S4** — the
next canonical LearningOps step on top of the pipeline that §6.4 closed
(builder → splitter → trainer → registry → shadow). Phase 6 is the
highest-leverage open phase; Phase 7 still stays deferred until a
real-traffic `promote` verdict from `BrainOperationsReporter` is on
record.

Alternatives of comparable weight:

- §6.1 / §6.6 open governance items that need another pass;
- §6.5 *"Quantisierung/Distillation evaluieren"* — an evaluation
  document rather than canonical code; better timed once Phase 6 has a
  real-traffic footprint.
