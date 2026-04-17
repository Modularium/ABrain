# Phase 3 R5 — Review: Prompt-Injection Detection at RetrievalBoundary

**Branch:** `codex/phaseR5-injection-boundary`  
**Date:** 2026-04-18  
**Roadmap:** Phase 3 – Retrieval- und Wissensschicht — "Prompt-Injection-Abwehr an Retrieval-Grenzen implementieren"

---

## 1. Scope

Adds prompt-injection detection as a mandatory step inside `RetrievalBoundary`, fulfilling the Phase 3 roadmap task _"Prompt-Injection-Abwehr an Retrieval-Grenzen implementieren"_.

| Component | File | What changed |
|---|---|---|
| `RetrievalBoundary.sanitise_results()` | `core/retrieval/boundaries.py` | New canonical combined method: trust/scope annotation + injection scan |
| `_detect_injection()` | `core/retrieval/boundaries.py` | Internal helper — case-insensitive substring match against `_INJECTION_PATTERNS` |
| `_INJECTION_PATTERNS` | `core/retrieval/boundaries.py` | 14 high-signal instruction-injection patterns |
| `InMemoryRetriever.retrieve()` | `core/retrieval/retriever.py` | Calls `sanitise_results()` instead of `annotate_results()` |
| `SQLiteRetriever.retrieve()` | `core/retrieval/retriever.py` | Calls `sanitise_results()` instead of `annotate_results()` |

`annotate_results()` is unchanged — `sanitise_results()` calls it internally as step 1.

---

## 2. What was already present (R1–R4)

- `RetrievalBoundary` with `validate_query()`, `annotate_results()`, `check_planning_scope_trust()`
- Both retrievers calling `annotate_results()` before returning results

R5 is purely additive: one new method, one helper, one constant, two one-line call-site changes.

---

## 3. Architecture invariants verified

| Invariant | Status |
|---|---|
| Single enforcement point — `RetrievalBoundary` remains the only policy gate | ✅ |
| Content never modified — injection detected → warning/violation, `content` unchanged | ✅ |
| No new dependencies — pure stdlib string operations | ✅ |
| `annotate_results()` unchanged — backward-compatible | ✅ |
| Both retrievers updated consistently | ✅ `InMemoryRetriever` + `SQLiteRetriever` |

---

## 4. Detection policy

| Source trust | Injection detected | Behaviour |
|---|---|---|
| `TRUSTED` | any | Not scanned — controlled, verified content |
| `INTERNAL` | any | Not scanned — controlled, verified content |
| `EXTERNAL` | yes | Advisory warning appended to `result.warnings`; result still returned |
| `EXTERNAL` | no | Unchanged |
| `UNTRUSTED` | yes | `RetrievalPolicyViolation` raised immediately |
| `UNTRUSTED` | no | Unchanged (trust warning from scope matrix still applies) |

**Why TRUSTED/INTERNAL are not scanned:** Security documentation and internal knowledge bases legitimately discuss injection patterns. Scanning controlled sources would produce false positives and undermine trust in the system. The attack surface is exclusively EXTERNAL and UNTRUSTED content.

**Why UNTRUSTED raises vs EXTERNAL warns:** UNTRUSTED content with injection is an unacceptable risk — it should never have been ingested for the planning scope, and its presence in results is a hard signal. EXTERNAL is lower risk (licensed, controlled-access) but still warrants operator attention.

---

## 5. Injection pattern set

14 patterns covering the most common instruction-injection families:

- `ignore (all|previous) instructions` variants
- `disregard (all|previous|your) instructions` variants
- `forget (all|your|previous) instructions` variants
- `you are now a` / `you must now` / `override your instructions`
- `new system prompt`
- `as an ai with no restrictions`
- Role-injection via embedded markers: `\nsystem:`, `\nuser:`, `\nassistant:`

Conservative scope: high-signal phrases unlikely to appear in legitimate content from untrusted sources.

---

## 6. Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/retrieval/test_retrieval_injection.py` | 29 | `_detect_injection` patterns, TRUSTED/INTERNAL passthrough, EXTERNAL warning, UNTRUSTED violation, trust/scope annotations preserved, end-to-end via InMemoryRetriever, end-to-end via SQLiteRetriever |

**Full test run:**
- Retrieval: 230/230 passed
- Full standard suite: 685 passed, 1 skipped, 0 failed

---

## 7. What R5 does NOT include (by design)

- No semantic/embedding-based injection detection — deliberately conservative; pattern matching is auditable and deterministic
- No content sanitisation — content is never modified, only blocked or warned
- No retrieval/audit source-citation integration — this is Phase 3 R6 (Quellennachweise in Explainability/Audit)

---

## 8. Merge gate

| Check | Result |
|---|---|
| Scope correct (R5 per roadmap) | ✅ |
| No parallel structure | ✅ |
| Canonical path (`core/retrieval/boundaries.py`) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green | ✅ 230/230 retrieval, 685/685 full suite |
| Review doc present | ✅ this file |
| Merge-ready | ✅ |

---

## 9. Next step (R6)

**Retrieval audit integration** — the last open Phase 3 task:
surface `RetrievalResult.source_id` and `provenance` into `TraceStore` span attributes so that every retrieval operation is attributable in the audit trail.  This connects `core/retrieval/` to the canonical `TraceStore` without creating a second trace path.
