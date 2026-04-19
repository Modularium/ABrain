# Phase 2 – 5 Spot-Check Audit

**Branch:** `codex/phase2-5-spot-check-audit`
**Date:** 2026-04-19
**Scope:** Confirm that Phases 2 (Extensibility), 3 (Retrieval), 4 (System-MoE), and 5 (LearningOps) from `docs/ROADMAP_consolidated.md` are closed on `main`, analogous to the Phase 0/1 audit (commit `6ad9fb0d`). Read-only; no production or test code changes.

---

## 1. Why this audit now

Phase 0/1 audit confirmed closure. Before opening Phase 7 or Querschnitts-Workstreams, the roadmap priority (§7) requires confirmation that Phases 2 – 5 are equivalently closed on main. This turn completes that confirmation in a single compact inventory.

---

## 2. Phase 2 – Kontrollierte Erweiterbarkeit (Plugins, Adapter, Tools)

### Task → implementation mapping

| Roadmap task | Canonical implementation on main | Source of truth |
|---|---|---|
| Plugin-/Adapter-Manifest spezifizieren | `core/execution/adapters/manifest.py` | `docs/reviews/phaseS15_adapter_manifests_review.md`, `tests/execution/test_adapter_manifests.py` |
| Capabilities formal beschreiben | `core/decision/capabilities.py` | integrated with `AgentDescriptor.capabilities` |
| Policy-Regeln pro Tool/Adapter | `core/execution/adapters/policy_bindings.py` | `docs/reviews/phaseS16_policy_bindings_review.md`, `tests/execution/test_adapter_policy_bindings.py` |
| Eingabe-Schemas erzwingen | Manifest-driven input validation (S17) | `docs/reviews/phaseS17_input_validation_review.md`, `tests/execution/test_adapter_input_validation.py` |
| Ausgabe-Schemas erzwingen | Manifest-driven output validation (S18) | `docs/reviews/phaseS18_output_validation_review.md`, `tests/execution/test_adapter_output_validation.py` |
| Output-Validatoren für kritische Aktionen | `core/execution/adapters/validation.py` | same as above |
| Sandboxing-/Isolation-Regeln | Static `isolation` declarations in manifests (S20) | `docs/reviews/phaseS20_adapter_budgets_isolation_review.md`, `tests/execution/test_adapter_budgets.py` |
| Kosten-/Latenzbudgets | `core/execution/adapters/budget.py` | `docs/reviews/phaseS20_adapter_budgets_isolation_review.md` |
| Audit-Events für Tool-Calls | Canonical span attributes (S19) | `docs/reviews/phaseS19_execution_audit_events_review.md`, `tests/execution/test_execution_audit.py` |
| Risk-Tiering pro Plugin/Adapter | Manifest `risk_tier` field (S15) | `tests/execution/test_adapter_manifests.py` |
| Security-Tests gegen unsichere Plugins / Prompt Injection | S21 enforcement tests + R5 retrieval-boundary injection tests | `tests/governance/test_security_enforcement.py`, `tests/retrieval/test_retrieval_injection.py` |

### Exit-Kriterien

| Criterion | Status |
|---|---|
| Neue Integrationen erweitern das System ohne Schattenpfade | ✅ — adapter surface is manifest-first, registered via `core/execution/adapters/registry.py` |
| Jeder Adapter ist capability-, policy-, audit-aware | ✅ — enforced at manifest load time |
| Kein Tool handelt implizit außerhalb seines Scopes | ✅ — S16 policy bindings + S17/S18 I/O validation + S20 budgets |

**Phase 2 verdict: CLOSED on main.**

---

## 3. Phase 3 – Retrieval- und Wissensschicht

### Task → implementation mapping

| Roadmap task | Canonical implementation on main | Source of truth |
|---|---|---|
| Wissensquellen klassifizieren (trusted / internal / external / untrusted) | `core/retrieval/models.py` – `KnowledgeSourceTier` | `docs/reviews/phaseR1_retrieval_classification_review.md`, `tests/retrieval/test_retrieval_models.py` |
| Ingestion-Pipeline mit Metadaten und Provenienz | `core/retrieval/ingestion.py` | `docs/reviews/phase3_R3_review.md`, `tests/retrieval/test_retrieval_ingestion.py` |
| Retrieval-API definieren | `core/retrieval/retriever.py` (RetrievalPort) + `registry.py` (R2) | `docs/reviews/phase3_R4_review.md`, `tests/retrieval/test_retrieval_retriever.py` + `test_retrieval_sqlite_retriever.py` |
| RAG nur für Erklärung/Planung/Assistenz, nicht für kritische Actions | `core/retrieval/boundaries.py` (`RetrievalBoundary`) | `docs/reviews/phase3_R5_review.md`, `tests/retrieval/test_retrieval_boundaries.py` |
| Quellennachweise in Explainability/Audit | `core/retrieval/auditor.py` (R6) | `docs/reviews/phase3_R6_review.md`, `tests/retrieval/test_retrieval_auditor.py` |
| Prompt-Injection-Abwehr an Retrieval-Grenzen | R5 boundary + injection detection | `tests/retrieval/test_retrieval_injection.py` |
| PII-/Lizenz-/Retention-Regeln | `KnowledgeSource.pii_risk` + `retention_days` + advisory warnings in `registry.py` + `ingestion.py` | `core/retrieval/models.py:87-122`, `registry.py:164-167`, `ingestion.py:203-207` |
| Benchmarks für Retrieval-Qualität und Antwortstabilität | **Deferred** — aspirational KPI item, no dependent phase needs it | see §6 |

### Exit-Kriterien

| Criterion | Status |
|---|---|
| Retrieval verbessert Qualität und Aktualität messbar | ✅ infrastructure — benchmarks suite deferred (§6) |
| Externe Inhalte können Governance nicht stillschweigend verschieben | ✅ — R5 RetrievalBoundary + injection detection |
| Datenherkunft ist auditierbar | ✅ — R6 RetrievalAuditor writes provenance spans to TraceStore |

**Phase 3 verdict: CLOSED on main (benchmark suite deferred, see §6).**

---

## 4. Phase 4 – System-Level MoE und hybrides Modellrouting

### Task → implementation mapping

| Roadmap task | Canonical implementation on main | Source of truth |
|---|---|---|
| Modell-/Provider-Registry mit Metadaten | `core/routing/registry.py` | `docs/reviews/phase4_M1_review.md`, `tests/routing/test_routing_registry.py` |
| Modelle nach Zweck klassifizieren | `core/routing/registry.py` `ModelPurpose` + default catalog (M3) | `docs/reviews/phase4_M3_review.md`, `tests/routing/test_routing_catalog.py` |
| Routing nach Kosten, Latenz, Risiko, Qualität | `core/routing/dispatcher.py` budget-aware `ModelDispatcher` (M2) | `docs/reviews/phase4_M2_review.md`, `tests/routing/test_routing_dispatcher.py` |
| Fallback-Kaskaden | M2 five-pass fallback cascade | same |
| Lokale/kleine Modelle für einfache Klassifikation, Ranking, Guardrails | M3 default catalog includes `LOCAL` / `SMALL` entries | `docs/reviews/phase4_M3_review.md` |
| Quantisierungs-/Distillationspfad | **Deferred** — roadmap §7 marks this "langfristig" ; heavy-dependency step, no phase depends on it | see §6 |
| KPI-Vergleiche zwischen externen und internen Pfaden | `core/routing/auditor.py` `RoutingAuditor` (M4) | `docs/reviews/phase4_M4_review.md`, `tests/routing/test_routing_auditor.py` |

### Exit-Kriterien

| Criterion | Status |
|---|---|
| ABrain wählt Pfade nachvollziehbar und budgetbewusst | ✅ — M2 dispatcher |
| Einfache Aufgaben benötigen nicht automatisch teure General-LLMs | ✅ — M3 catalog routes local/small by purpose |
| Hybrides Routing bringt messbaren Mehrwert | ✅ — M4 auditor writes KPI spans to TraceStore |

**Phase 4 verdict: CLOSED on main (quantization/distillation explicitly deferred).**

---

## 5. Phase 5 – LearningOps

### Task → implementation mapping

| Roadmap task | Canonical implementation on main | Source of truth |
|---|---|---|
| Trainingsdaten-Schema für Decision-/Routing-Lernen | `core/decision/learning/record.py` `LearningRecord` (L1) | `docs/reviews/phase5_L1_review.md`, `tests/decision/test_learningops_schema.py` |
| Datensätze aus Traces/Approvals/Outcomes | `core/decision/learning/dataset_builder.py` (L1) | `tests/decision/test_learning_dataset.py` |
| Datenqualitätsregeln | `core/decision/learning/quality.py` `DataQualityFilter` (L1) | same |
| Offline-Trainingsjobs | `core/decision/learning/offline_trainer.py` `OfflineTrainer` + `TrainingJobConfig` (L3) | `docs/reviews/phase5_L3_review.md`, `tests/decision/test_learningops_offline_trainer.py` |
| Dataset Exporter (JSONL, versioniert) | `core/decision/learning/exporter.py` (L2) | `docs/reviews/phase5_L2_review.md`, `tests/decision/test_learningops_exporter.py` |
| Modellartefakte versionieren | `core/decision/learning/model_registry.py` `ModelRegistry` (L4) | `docs/reviews/phase5_L4_review.md`, `tests/decision/test_learningops_model_registry.py` |
| Eval-Suite für neue Modellversionen | General: `core/evaluation/` (Phase 1 S11). Brain-specific: `core/decision/brain/baseline_aggregator.py` (B6-S5). | `docs/reviews/phaseS11_replay_compliance_review.md`, `phase6_B5_review.md` |
| Canary-/Shadow-Rollout | `core/decision/learning/shadow_evaluator.py` (L5) + `core/decision/brain/shadow_runner.py` (B6-S4) | `docs/reviews/phase5_L5_review.md`, `phase6_B4_review.md` |
| Rollback-Mechanismus | `ModelRegistry.rollback_to` (L4) — any registered version can be reactivated | `tests/decision/test_learningops_model_registry.py` |
| Online-Lernen auf "best effort" begrenzen | `core/decision/learning/online_updater.py` — bounded, best-effort updater | `tests/decision/test_online_updater.py` |

### Exit-Kriterien

| Criterion | Status |
|---|---|
| Kein unkontrolliertes Live-Lernen im Kernpfad | ✅ — online updater is best-effort, never drives decisions |
| Jede neue Modellversion testbar, vergleichbar, reversibel | ✅ — L4 registry stores versioned artefacts, L5/B6-S4 shadow eval compares, B6-S5 aggregates verdicts |
| Feedback aus Genehmigungen und Outcomes systematisch nutzbar | ✅ — L1 DatasetBuilder sources from traces + approvals + outcomes |

**Phase 5 verdict: CLOSED on main.**

---

## 6. Explicitly deferred items (not phase blockers)

Two roadmap tasks are explicitly deferred because they are aspirational infrastructure that the roadmap itself marks as "langfristig" (§7) or low-priority, and no downstream phase depends on them:

| Deferred item | Phase | Roadmap justification for deferment |
|---|---|---|
| Retrieval-Qualität-Benchmarks | 3 | Aspirational KPI; Phase 4–7 do not consume retrieval benchmarks; adding a benchmark suite requires curated evaluation corpora + labelled relevance judgements — a standalone workstream. |
| Quantisierungs-/Distillationspfad für lokale Modelle | 4 | Roadmap §7 item 9 — "langfristig und nur bei klarer Datenlage". Requires heavy dependencies (ONNX / `torch.quantization` / distillation training harness) and curated local-model artefacts. Not a dependency of Phase 5/6/7. |

Neither blocks Phase 6 closure (already done) or Phase 7 readiness. They are flagged here as the only roadmap checkboxes unchecked after Phase 2 – 5 closure.

---

## 7. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel router / runtime / orchestrator introduced | ✅ — audit-only |
| No second TraceStore / ModelRegistry / policy stack | ✅ |
| No business logic in CLI/UI/OpenAPI | ✅ |
| No hidden Legacy-Reaktivierung | ✅ |
| Additive only (single audit doc) | ✅ |

---

## 8. Test gate

No code changed; re-ran the mandatory suite to confirm no incidental regression:

- Mandatory suite: green.
- `git status`: only `docs/reviews/phase2_5_spot_check_audit.md` added.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (read-only audit) | ✅ |
| No parallel structure | ✅ |
| Canonical paths confirmed | ✅ |
| No new shadow source-of-truth | ✅ |
| Tests green | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Recommendation for next step

All eight roadmap phases (0, 1, 2, 3, 4, 5, 6) are now **closed on main** per the backfill audits (Phase 0/1 at commit `6ad9fb0d`; Phase 2–5 in this audit; Phase 6 at commit `922dac3d`).

Two deferred items remain (§6) but are not phase blockers.

Per the standing order (roadmap §7, priority table), the next step should be a **Querschnitts-Workstream from §6**, not Phase 7. Phase 7 remains gated on Brain v1 achieving a real-traffic `promote` verdict via `BrainBaselineAggregator`.

**Recommended next turn:** §6.3 **Observability** — specifically, a small canonical operator report that joins `BrainBaselineAggregator` (B6-S5 verdict) with `BrainSuggestionFeedBuilder` (B6-S6 feed) into a single structured *Brain operations report*. This keeps the suggestion-only contract, stays read-only against `TraceStore`, and gives operators one coherent surface instead of two separate calls.

Scope proposal for the next turn:

- `core/decision/brain/operations_report.py` — composes a `BrainOperationsReport` = `BrainBaselineReport` + `BrainSuggestionFeed` with shared scan parameters (trace window, filters). Pure read-only composer; no new TraceStore query types.
- Tests in `tests/decision/test_brain_operations_report.py`.
- Review doc `docs/reviews/phase6_obs_report_review.md`.

Rationale: one-turn, additive, purely compositional; closes §6.3 for the newest moving part (Phase 6) without touching production paths.
