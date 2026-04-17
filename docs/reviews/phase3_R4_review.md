# Phase 3 R4 — Review: SQLiteRetriever (closes ingest→retrieve loop)

**Branch:** `codex/phaseR4-sqlite-retriever`  
**Date:** 2026-04-18  
**Roadmap:** Phase 3 – Retrieval- und Wissensschicht, Step R4

---

## 1. Scope

Adds `SQLiteRetriever` to `core/retrieval/retriever.py` — the production
`RetrievalPort` backend that queries `SQLiteDocumentStore`.

With R4 the Phase 3 functional loop is complete:

```
register (registry) → ingest (pipeline → store) → retrieve (SQLiteRetriever → store)
```

| Component | File | Role |
|---|---|---|
| `SQLiteRetriever` | `core/retrieval/retriever.py` | `RetrievalPort` impl over `SQLiteDocumentStore` |

`core/retrieval/__init__.py` exports `SQLiteRetriever`.

---

## 2. What was already present (R1–R3)

| Step | Components |
|---|---|
| R1 | `SourceTrust`, `RetrievalScope`, `KnowledgeSource`, `RetrievalQuery`, `RetrievalResult`, `RetrievalBoundary`, `RetrievalPolicyViolation` |
| R2 | `KnowledgeSourceRegistry`, `RegistrationError`, `RetrievalPort`, `InMemoryRetriever` |
| R3 | `DocumentStore`, `SQLiteDocumentStore`, `IngestionPipeline`, `IngestionRequest`, `IngestionResult` |

R4 adds one class; nothing in R1–R3 is modified.

---

## 3. Architecture invariants verified

| Invariant | Status |
|---|---|
| Single `RetrievalPort` contract — two implementations, no parallel paths | ✅ `InMemoryRetriever` (tests/dev) and `SQLiteRetriever` (production) satisfy the same protocol |
| Shared scoring helpers (`_tokenize`, `_overlap_score`) — no duplication | ✅ both classes call the same module-level functions |
| Governance enforcement unchanged — `RetrievalBoundary.annotate_results()` applied | ✅ identical call as `InMemoryRetriever` |
| No new dependencies | ✅ sqlite3 was already used in R3 |
| No content modification | ✅ retriever only reads, scores, annotates |
| Import cycle avoided | ✅ `SQLiteDocumentStore` imported at runtime inside `__init__`; `TYPE_CHECKING` guard for static analysis |

---

## 4. Behaviour

`SQLiteRetriever.retrieve(query, registry)`:

1. Iterate over `registry.list_all()` — only registered sources are considered.
2. Apply `allowed_trust_levels` filter (same logic as `InMemoryRetriever`).
3. Fetch chunks from `SQLiteDocumentStore.get_chunks(source_id)`.
4. Score each chunk with `_overlap_score` (recall-based: `|intersection| / |query|`).
5. Sort candidates descending, cap at `query.max_results`.
6. Build `RetrievalResult` objects with provenance from source.
7. Delegate to `RetrievalBoundary.annotate_results()`.

Sources registered but with no stored chunks silently produce no candidates.
Sources with stored chunks but not in the registry are skipped — registry is the authority.

---

## 5. Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/retrieval/test_retrieval_sqlite_retriever.py` | 19 | protocol conformance, basic match, no match, registered-no-chunks, chunks-not-registered, max_results, trust filtering, boundary annotations, ranking, end-to-end ingest→retrieve, re-ingest replaces |

**Full test run:**
- Retrieval: 201/201 passed
- Full standard suite: 685 passed, 1 skipped, 0 failed

---

## 6. What R4 does NOT include (by design)

- No API/CLI/MCP surface for retrieval — wired into orchestration in a later step
- No prompt-injection defence at retrieval boundaries — Phase 3 roadmap task R5
- No source-citation integration into Audit/Trace — Phase 3 roadmap task R5
- No vector/embedding backend — out of scope for Phase 3 minimal footprint

---

## 7. Merge gate

| Check | Result |
|---|---|
| Scope correct (R4 per roadmap) | ✅ |
| No parallel structure | ✅ |
| Canonical paths only (`core/retrieval/`) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green | ✅ 201/201 retrieval, 685/685 full suite |
| Review doc present | ✅ this file |
| Merge-ready | ✅ |

---

## 8. Next step (R5)

**Retrieval audit integration + prompt-injection boundary** — two remaining
Phase 3 roadmap tasks now that the functional loop is closed:

1. Surface `RetrievalResult.provenance` / `source_id` into `TraceStore` audit events so retrieved sources are attributable in the audit trail.
2. Add prompt-injection detection at `RetrievalBoundary` — reject or sanitise retrieval results that contain instruction-injection patterns before they reach the planning/assistance layer.
