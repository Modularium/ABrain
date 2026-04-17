# Phase 3 R3 — Review: Ingestion Pipeline + SQLite DocumentStore

**Branch:** `codex/phaseR3-ingestion-pipeline`  
**Date:** 2026-04-17  
**Roadmap:** Phase 3 – Retrieval- und Wissensschicht, Step R3

---

## 1. Scope

Adds the ingestion layer that closes the "Ingestion-Pipeline mit Metadaten und Provenienz" task from the Phase 3 roadmap:

| Component | File | Role |
|---|---|---|
| `DocumentStore` | `core/retrieval/document_store.py` | Abstract Protocol for storage backends |
| `SQLiteDocumentStore` | `core/retrieval/document_store.py` | Canonical durable store (SQLite, same pattern as TraceStore) |
| `IngestionRequest` | `core/retrieval/ingestion.py` | Validated input contract |
| `IngestionResult` | `core/retrieval/ingestion.py` | Result with chunk count and advisory warnings |
| `IngestionPipeline` | `core/retrieval/ingestion.py` | Governance-aware ingest: validate → chunk → store |

Updated `core/retrieval/__init__.py` to export all five new public symbols.

---

## 2. What was already present (R1 + R2)

- R1: `SourceTrust`, `RetrievalScope`, `KnowledgeSource`, `RetrievalQuery`, `RetrievalResult`, `RetrievalBoundary`, `RetrievalPolicyViolation`
- R2: `KnowledgeSourceRegistry`, `RegistrationError`, `RetrievalPort`, `InMemoryRetriever`

R3 builds on both without modifying them.

---

## 3. Architecture invariants verified

| Invariant | Status |
|---|---|
| Single ingestion entry-point | ✅ All content enters via `IngestionPipeline.ingest()` |
| No content modification | ✅ Pipeline only splits and stores; content is never altered |
| Governance enforced before storage | ✅ Registry lookup + `_governance_warnings()` run before `store_chunks()` |
| Canonical SQLite pattern (TraceStore) | ✅ Schema-on-connect, `DELETE` + batch `INSERT` for idempotency |
| Deterministic chunk IDs | ✅ `<source_id>:<index>` — re-ingest is safe and reproducible |
| `RetrievalScope` has no action scope | ✅ Preserved from R1; not touched |
| No new heavyweight dependencies | ✅ sqlite3 is stdlib |
| `InMemoryRetriever` still usable | ✅ `DocumentStore` is a Protocol; `InMemoryRetriever` is unchanged |

---

## 4. Governance rules enforced at ingest time

**Hard violations (raise immediately):**
- `source_id` not registered in `KnowledgeSourceRegistry` → `KeyError`

**Advisory warnings (non-blocking, returned in `IngestionResult.warnings`):**
- PII source without `retention_days`
- EXTERNAL/UNTRUSTED source without `license`
- UNTRUSTED source (always warned: use restricted to explanation/assistance)

---

## 5. Chunking strategy

`_split_chunks(content, max_chunk_size)`:
1. Split on double-newline (paragraph boundary) to preserve semantic units
2. Hard-split any paragraph exceeding `max_chunk_size` characters
3. Discard empty/whitespace-only paragraphs

Deterministic: same input always produces the same chunks. No LLM, no embedding, no network I/O.

---

## 6. Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/retrieval/test_retrieval_document_store.py` | 25 | protocol, store/get/delete/list/count, idempotency, persistence across reconnect |
| `tests/retrieval/test_retrieval_ingestion.py` | 29 | request validation, chunking, happy path, unknown source, store integration, advisory warnings, re-ingest, task_id echo |

**Full test run:**
- Retrieval: 182/182 passed
- Full standard suite: 685 passed, 1 skipped, 0 failed

---

## 7. What R3 does NOT include (by design)

- No `PersistentRetriever` — closing the ingest→retrieve loop is R4
- No vector/embedding — out of scope for Phase 3 minimal footprint
- No API/CLI surface for ingestion — wired into orchestration in a later step
- No prompt-injection defence at retrieval boundaries — Phase 3 roadmap task, scheduled for R5

---

## 8. Merge gate

| Check | Result |
|---|---|
| Scope correct (R3 per roadmap) | ✅ |
| No parallel structure | ✅ |
| Canonical paths only (`core/retrieval/`) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green | ✅ 182/182 retrieval, 685/685 full suite |
| Review doc present | ✅ this file |
| Merge-ready | ✅ |

---

## 9. Next step (R4)

**PersistentRetriever** — a `RetrievalPort` implementation that queries `SQLiteDocumentStore` instead of an in-memory dict.  This closes the ingestion→retrieval loop: content ingested via `IngestionPipeline` becomes immediately retrievable via the same `RetrievalPort` contract the orchestration layer already expects.
