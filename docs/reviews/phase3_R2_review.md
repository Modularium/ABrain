# Phase 3 R2 — Review: KnowledgeSourceRegistry + RetrievalPort

**Branch:** `codex/phaseR2-retrieval-port`  
**Date:** 2026-04-17  
**Roadmap:** Phase 3 – Retrieval- und Wissensschicht, Step R2

---

## 1. Scope

Adds the two components that complete the retrieval API surface started in R1:

| Component | File | Role |
|---|---|---|
| `KnowledgeSourceRegistry` | `core/retrieval/registry.py` | Canonical authority for registered knowledge sources; enforces governance at registration time |
| `RetrievalPort` | `core/retrieval/retriever.py` | Abstract `Protocol` for retrieval backends |
| `InMemoryRetriever` | `core/retrieval/retriever.py` | Keyword-overlap reference implementation for tests and local dev |

Updated `core/retrieval/__init__.py` to export all six public symbols (R1 + R2).

---

## 2. What was already present (R1)

- `core/retrieval/models.py`: `SourceTrust`, `RetrievalScope`, `KnowledgeSource`, `RetrievalQuery`, `RetrievalResult`
- `core/retrieval/boundaries.py`: `RetrievalBoundary`, `RetrievalPolicyViolation`
- Tests for models and boundaries (80 tests, all green)

R2 builds directly on R1 without modifying it.

---

## 3. Architecture invariants verified

| Invariant | Status |
|---|---|
| No parallel retrieval path created | ✅ `core/retrieval/` is the single retrieval module |
| No business logic in CLI/UI/API schema | ✅ all logic in `core/retrieval/` |
| No new heavyweight dependencies | ✅ pure stdlib + pydantic (already present) |
| Governance enforced at the boundary layer | ✅ `RetrievalBoundary.annotate_results()` called inside `InMemoryRetriever` |
| `RetrievalScope` has no critical-action scope | ✅ deliberate restriction preserved from R1 |
| EXTERNAL/UNTRUSTED sources require provenance | ✅ enforced at registration; `RegistrationError` on violation |
| PII risk advisory warnings surfaced | ✅ non-blocking warning returned from `register()` |
| Retrieval results never bypass audit attribution | ✅ every `RetrievalResult` carries `source_id`, `trust`, `provenance` |

---

## 4. Governance rules enforced

**Hard rules (RegistrationError):**
- Re-registration of a different source under the same `source_id` is rejected.
- `EXTERNAL` and `UNTRUSTED` sources must declare `provenance`.

**Advisory warnings (non-blocking):**
- PII source without `retention_days`.
- EXTERNAL/UNTRUSTED source without `license`.

**Idempotency:**
- Re-registering the exact same source object is a no-op (returns `[]`).

---

## 5. Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/retrieval/test_retrieval_registry.py` | 47 | registration happy path, idempotency, conflicts, governance rules, advisory warnings, deregister, get, is_registered, list_all, list_by_trust, len |
| `tests/retrieval/test_retrieval_retriever.py` | 18 | protocol conformance, document management, keyword scoring, max_results cap, trust filtering, unregistered-source skip, boundary annotation |

**Full test run (standard suite + retrieval):**
- Retrieval: 128/128 passed
- Full standard suite: 685 passed, 1 skipped, 0 failed

---

## 6. What R2 does NOT include (by design)

- No persistence — registry is in-process only (R3+ concern)
- No vector/embedding backend — `InMemoryRetriever` is keyword-overlap only
- No ingestion pipeline — that is R3
- No integration into orchestration or API surface — that follows once ingestion is in place

---

## 7. Merge gate

| Check | Result |
|---|---|
| Scope correct (R2 per roadmap) | ✅ |
| No parallel structure | ✅ |
| Canonical paths only (`core/retrieval/`) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green | ✅ 128/128 retrieval, 685/685 full suite |
| Review doc present | ✅ this file |
| Merge-ready | ✅ |

---

## 8. Next step (R3)

**Ingestion pipeline** — a controlled path for ingesting content into a knowledge source with metadata, provenance, and PII/license checks, backed by a lightweight persistent store. This will make `InMemoryRetriever` substitutable by a persistent backend without changing the `RetrievalPort` contract.
