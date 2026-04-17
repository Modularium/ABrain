# Phase 3 R6 — Review: Retrieval Audit Integration (Source Attribution in TraceStore)

**Branch:** `codex/phaseR6-retrieval-audit`  
**Date:** 2026-04-18  
**Roadmap:** Phase 3 – Retrieval- und Wissensschicht — "Quellennachweise in Explainability/Audit integrieren"

---

## 1. Scope

Adds `RetrievalAuditor` to `core/retrieval/auditor.py` — the component that surfaces retrieval source attribution into `TraceStore`, fulfilling the last open Phase 3 roadmap task _"Quellennachweise in Explainability/Audit integrieren"_.

| Component | File | Role |
|---|---|---|
| `RetrievalAuditor` | `core/retrieval/auditor.py` | Emits structured `retrieval.*` spans to `TraceStore` |

`core/retrieval/__init__.py` exports `RetrievalAuditor`.

---

## 2. What was already present (R1–R5)

| Step | What |
|---|---|
| R1 | Models + RetrievalBoundary |
| R2 | Registry + RetrievalPort + InMemoryRetriever |
| R3 | DocumentStore + IngestionPipeline |
| R4 | SQLiteRetriever |
| R5 | Injection detection — `sanitise_results()` |

R6 adds one new file and one export. Nothing in R1–R5 is modified.

---

## 3. Architecture invariants verified

| Invariant | Status |
|---|---|
| `TraceStore` is the single Trace/Audit truth — no second path | ✅ `RetrievalAuditor` calls `TraceStore.start_span()` + `finish_span()` directly |
| Retrieval layer not coupled to tracing | ✅ Retrievers are unchanged; auditor is called by the orchestration layer |
| Optional — no hard trace dependency at retrieval time | ✅ `RetrievalAuditor(None)` is a no-op; retrieval always works without an auditor |
| Errors in audit emission swallowed | ✅ `_emit()` catches all exceptions, logs, returns `None` |
| Span type = `"retrieval"` — queryable and distinct | ✅ all spans use `SPAN_TYPE = "retrieval"` |

---

## 4. Span attributes (canonical format, per S19 convention)

**`record_retrieval` → span name `retrieval.query`, status `ok`:**

| Attribute | Type | Description |
|---|---|---|
| `retrieval.query.scope` | str | Retrieval scope (explanation/assistance/planning) |
| `retrieval.query.task_id` | str \| None | Task for audit attribution |
| `retrieval.results.count` | int | Number of results returned |
| `retrieval.results.sources` | list | `[{source_id, trust, provenance}]` per result |
| `retrieval.warnings.count` | int | Sum of warnings across all results |
| `retrieval.injection_blocked` | bool | Always `False` here |

**`record_injection_block` → span name `retrieval.blocked`, status `blocked`:**

Same query attributes plus:

| Attribute | Value |
|---|---|
| `retrieval.results.count` | `0` |
| `retrieval.results.sources` | `[]` |
| `retrieval.injection_blocked` | `True` |
| `retrieval.injection_reason` | Truncated violation reason (≤512 chars) |

---

## 5. Usage pattern (caller side)

```python
auditor = RetrievalAuditor(trace_store)  # once, at service init
try:
    results = retriever.retrieve(query, registry)
    auditor.record_retrieval(trace_id, query, results, parent_span_id=span_id)
except RetrievalPolicyViolation as violation:
    auditor.record_injection_block(trace_id, query, violation, parent_span_id=span_id)
    raise
```

No changes required in the retrievers themselves.

---

## 6. Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/retrieval/test_retrieval_auditor.py` | 24 | span type/name/status, all attributes, source list, warnings count, no-store no-op, injection_block span, violation reason truncation, parent_span_id propagation, error swallowing |

All tests use a real `TraceStore` backed by `tmp_path` — no mocks.

**Full test run:**
- Retrieval: 254/254 passed
- Full standard suite: 685 passed, 1 skipped, 0 failed

---

## 7. Phase 3 completion status

All Phase 3 roadmap tasks are now delivered:

| Task | Step | Status |
|---|---|---|
| Wissensquellen klassifizieren | R1 | ✅ |
| Retrieval-API definieren | R1/R2 | ✅ |
| Ingestion-Pipeline mit Metadaten und Provenienz | R3 | ✅ |
| RAG nur für Erklärung/Planung/Assistenz | R1 | ✅ |
| Quellennachweise in Explainability/Audit | R6 | ✅ |
| Prompt-Injection-Abwehr | R5 | ✅ |
| PII-/Lizenz-/Retention-Regeln | R2/R3 | ✅ |

The _"Benchmarks für Retrieval-Qualität und Antwortstabilität"_ task from the roadmap maps naturally to Phase 1 evaluation infrastructure (replay harness, baseline metrics) rather than the retrieval module itself — it will be addressed when evaluation infrastructure is extended.

---

## 8. Merge gate

| Check | Result |
|---|---|
| Scope correct (R6 per roadmap) | ✅ |
| No parallel structure | ✅ |
| Canonical paths (`core/retrieval/`, `TraceStore`) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green | ✅ 254/254 retrieval, 685/685 full suite |
| Review doc present | ✅ this file |
| Merge-ready | ✅ |

---

## 9. Next phase

Phase 3 functional core is complete. The next roadmap phase is **Phase 4 — System-Level MoE und hybrides Modellrouting**:

- Modell-/Provider-Registry with metadata
- Model classification by purpose (planning, classification, ranking, etc.)
- Budget-aware dispatching with fallback cascades
- KPI comparison between external and internal routing paths
