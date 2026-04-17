# Phase 4 M1 — Review: Model/Provider Registry with Purpose Classification

**Branch:** `codex/phase4-model-registry`  
**Date:** 2026-04-18  
**Roadmap:** Phase 4 – System-Level MoE und hybrides Modellrouting — "Modell-/Provider-Registry mit Metadaten aufbauen" + "Modelle nach Zweck klassifizieren"

---

## 1. Scope

Opens Phase 4 with the foundational data layer: the model/provider registry and purpose classification taxonomy.  Without this registry the routing layer (M2) has no canonical source of which models exist, what they cost, and what they're suited for.

| Component | File | Role |
|---|---|---|
| `ModelPurpose` | `core/routing/models.py` | Purpose taxonomy (PLANNING, CLASSIFICATION, RANKING, RETRIEVAL_ASSIST, LOCAL_ASSIST, SPECIALIST) |
| `ModelTier` | `core/routing/models.py` | Cost/capability tier (LOCAL, SMALL, MEDIUM, LARGE) |
| `ModelProvider` | `core/routing/models.py` | Provider enum (ANTHROPIC, OPENAI, GOOGLE, LOCAL, CUSTOM) |
| `ModelDescriptor` | `core/routing/models.py` | Canonical model declaration with governance metadata |
| `ModelRegistry` | `core/routing/registry.py` | Registration authority with idempotency and advisory warnings |
| `RegistrationError` | `core/routing/registry.py` | Hard violation exception |

New package `core/routing/` with `__init__.py` exporting the full public surface.

---

## 2. Architecture invariants verified

| Invariant | Status |
|---|---|
| Not a parallel router — distinct from `core/decision/routing_engine.py` | ✅ Agent routing = "which adapter handles the task". Model routing = "which LLM handles the AI step". Different layers. |
| `extra="forbid"` on `ModelDescriptor` | ✅ governance fields can't drift silently |
| LOCAL tier cannot declare `cost_per_1k_tokens` | ✅ enforced via `model_validator` — LOCAL runs on local infra with no API cost |
| `purposes` must be non-empty | ✅ `min_length=1` on the field |
| No business logic — pure data contracts + registry | ✅ routing logic is M2 |
| No new heavy dependencies | ✅ pure Pydantic (already present) |

---

## 3. Governance rules

**Hard violations (RegistrationError):**
- Re-registering a different descriptor under the same `model_id`

**Model-level validation (ValueError):**
- LOCAL tier with `cost_per_1k_tokens` declared
- Empty `model_id` / `display_name`
- Empty `purposes` list

**Advisory warnings (non-blocking, returned from `register()`):**
- Non-LOCAL model without `cost_per_1k_tokens` → budget routing falls back
- Any model without `p95_latency_ms` → latency routing falls back to tier ordering

---

## 4. Purpose taxonomy

| Purpose | Intended model characteristics |
|---|---|
| `PLANNING` | Large context, strong reasoning; multi-step task decomposition |
| `CLASSIFICATION` | Fast, cheap; maps input to categorical output |
| `RANKING` | Scoring/ordering candidates; often local embedding models |
| `RETRIEVAL_ASSIST` | Query rewriting, re-ranking, RAG context summarisation |
| `LOCAL_ASSIST` | Short responses; local or small models to reduce cost |
| `SPECIALIST` | Narrow domain expertise (code, legal, medical) |

---

## 5. Tests

| File | Tests | Coverage |
|---|---|---|
| `tests/routing/test_routing_models.py` | 22 | descriptor validation, enum coverage, purpose dedup, LOCAL tier cost guard, optional field defaults |
| `tests/routing/test_routing_registry.py` | 33 | register happy path, idempotency, conflicts, advisory warnings, deregister, get, is_registered, list_all, list_available, list_by_purpose, list_by_tier, list_by_provider, len |

**Full test run:**
- Routing: 55/55 passed
- Full standard suite: 685 passed, 1 skipped, 0 failed

---

## 6. What M1 does NOT include (by design)

- No routing logic — that is M2 (budget-aware dispatcher + fallback cascades)
- No persistence — in-process registry only (analogous to Phase 3 R2 pattern)
- No API/CLI surface — wired into services in a later step
- No pre-loaded catalog of actual models — operators register their available models at startup

---

## 7. Merge gate

| Check | Result |
|---|---|
| Scope correct (P4-M1 per roadmap) | ✅ |
| No parallel structure | ✅ |
| Canonical path (`core/routing/`) | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green | ✅ 55/55 routing, 685/685 full suite |
| Review doc present | ✅ this file |
| Merge-ready | ✅ |

---

## 8. Next step (M2)

**Budget-aware model dispatcher + fallback cascades** — the routing logic that selects the best available model from the registry for a given `ModelRoutingRequest`:
- Filter by purpose, availability, tool-use and structured-output requirements
- Score candidates by cost and latency budget fit
- Apply tier-ordered fallback cascade when no candidate meets strict constraints
- Return `ModelRoutingResult` with selected model and selection reason
