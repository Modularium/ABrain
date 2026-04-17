# Phase R1 — Knowledge Source Classification + Retrieval API Surface

**Branch:** `codex/phaseR1-retrieval-classification`
**Date:** 2026-04-17
**Reviewer:** automated phase gate

---

## 1. Roadmap Position

**Phase 3 — Retrieval- und Wissensschicht**, first step R1:

| Roadmap task | Status |
|---|---|
| Wissensquellen klassifizieren: trusted / internal / external / untrusted | ✅ closed |
| Retrieval-API definieren | ✅ closed (data model layer) |
| RAG nur für Erklärung, Planung und Assistenz freigeben | ✅ closed (scope enum + boundary) |
| Prompt-Injection-Abwehr an Retrieval-Grenzen | 🔜 R3 (structural boundary established; content-level sanitization deferred) |
| Ingestion-Pipeline mit Metadaten und Provenienz | 🔜 R2 |
| Quellennachweise in Explainability/Audit integrieren | 🔜 R4 |
| PII-/Lizenz-/Retention-Regeln für Wissensquellen definieren | ✅ modeled in KnowledgeSource (enforcement R2) |
| Benchmarks für Retrieval-Qualität | 🔜 R5 |

---

## 2. What was already present

### Legacy `rag/` directory (pre-canonical, not activated)

Four files exist in `rag/` but import from non-existent modules
(`agents.web_scraper_agent`, `datastores.vector_store`, etc.) and depend on
`langchain`/`OpenAI`.  They are not imported anywhere in the canonical core.

**Decision:** Leave in place (deleting is a Phase-0 cleanup — Phase 0 is closed).
Document as pre-canonical.  Not imported, not activated, not referenced.

### No canonical retrieval infrastructure

`core/retrieval/` did not exist before this step.  No imports in
`services/core.py`, `api_gateway/`, or `core/` referenced any retrieval module.

---

## 3. What changed

### `core/retrieval/__init__.py` (new)

Public exports: `SourceTrust`, `RetrievalScope`, `KnowledgeSource`,
`RetrievalQuery`, `RetrievalResult`, `RetrievalBoundary`,
`RetrievalPolicyViolation`.

### `core/retrieval/models.py` (new)

```
SourceTrust (StrEnum)
    TRUSTED    — first-party, verified
    INTERNAL   — internal, less controlled
    EXTERNAL   — third-party, controlled access
    UNTRUSTED  — public web, user-provided

RetrievalScope (StrEnum)
    EXPLANATION — explain decisions; all trust levels allowed
    ASSISTANCE  — Q&A, context; all trust levels allowed
    PLANNING    — task planning; UNTRUSTED forbidden, EXTERNAL warned
    (no "critical_action" scope — intentionally absent)

KnowledgeSource (Pydantic, extra="forbid")
    source_id, display_name, trust, source_type
    provenance | None, pii_risk, license | None, retention_days | None

RetrievalQuery (Pydantic, extra="forbid")
    query_text, scope, allowed_trust_levels (deduplicated)
    task_id | None, max_results [1..50]

RetrievalResult (Pydantic, extra="forbid")
    source_id, trust, content, score [0..1]
    provenance | None, retrieved_at (UTC ISO), warnings: list[str]
```

All models: `extra="forbid"`, validators for string normalization and
deduplication, boundary value enforcement.

### `core/retrieval/boundaries.py` (new)

```
RetrievalPolicyViolation(RuntimeError)
    .reason: str
    .query:  RetrievalQuery

RetrievalBoundary
    validate_query(query)
        → raises RetrievalPolicyViolation for UNTRUSTED+PLANNING
    annotate_results(results, query) → list[RetrievalResult]
        → injects trust warnings; never mutates content or score
    check_planning_scope_trust(results, query) → list[str]
        → advisory pre-flight check without mutation
```

Trust/scope matrix is a pure `dict` lookup — no runtime logic, easy to audit.

### `tests/retrieval/test_retrieval_models.py` (new, 46 tests)

Covers all model fields, validators, edge cases, extra-field rejection,
enum completeness, scope restriction (no critical_action).

### `tests/retrieval/test_retrieval_boundaries.py` (new, 21 tests)

Covers: UNTRUSTED+PLANNING hard block; all permitted scope/trust combinations;
warning injection; no mutation of originals; duplicate warning suppression;
`RetrievalPolicyViolation` carry-through; `check_planning_scope_trust`.

---

## 4. Trust/scope matrix enforced

| Scope | TRUSTED | INTERNAL | EXTERNAL | UNTRUSTED |
|---|---|---|---|---|
| EXPLANATION | ✅ | ✅ | ✅ | ✅ + warning |
| ASSISTANCE | ✅ | ✅ | ✅ | ✅ + warning |
| PLANNING | ✅ | ✅ | ✅ + warning | ❌ `RetrievalPolicyViolation` |

---

## 5. Architecture invariant check

| Invariant | Status |
|---|---|
| No parallel retrieval path | `core/retrieval/` is the single namespace; legacy `rag/` not activated |
| No new heavy dependencies | Pure Python + Pydantic, no langchain, no vector store |
| Single canonical API | `core/retrieval/__init__.py` is the only public surface |
| extra="forbid" on all models | ✅ |
| No business logic in wrong layer | `boundaries.py` is pure stateless governance; no backend calls |
| No modification to existing canonical paths | `services/core.py`, `api_gateway/`, orchestrator untouched |
| Additive only | no existing code modified |

---

## 6. Test results

```
67 passed (tests/retrieval/)
752 passed, 1 skipped, 0 failed (full canonical suite + tests/retrieval/)
```

---

## 7. Review-/Merge-Gate

| Check | Result |
|---|---|
| Scope correct (R1 = classification + API spec only)? | ✅ |
| No parallel retrieval structure? | ✅ |
| Canonical paths used? | ✅ |
| No business logic in wrong layer? | ✅ |
| No new shadow truth? | ✅ |
| Tests green? | ✅ 67/67 + 752/752 |
| Documentation consistent? | ✅ |
| Merge-ready? | ✅ |

---

## 8. Next Step

**R2 — Ingestion Pipeline mit Metadaten und Provenienz**

Implement `core/retrieval/registry.py` — a `KnowledgeSourceRegistry` that
holds registered `KnowledgeSource` objects, and `core/retrieval/retriever.py`
— a `RetrievalPort` abstract interface (no concrete backend yet) and an
`InMemoryRetriever` for testing that allows the orchestrator integration test
to exercise the retrieval path without a real vector store.

This separates the abstract contract from any specific backend implementation
and enables the governance boundary to be tested end-to-end in R3.
