# Phase 4 M3 Review — Default Model Catalog for LOCAL/SMALL Models

**Step:** M3 — Default model catalog with LOCAL/SMALL descriptors for classification, ranking, and guardrails  
**Date:** 2026-04-18  
**Branch:** `codex/phase4-model-catalog`  
**Status:** Complete

## Roadmap task addressed

> "lokale/kleine Modelle für einfache Klassifikation, Ranking und Guardrails prüfen"

This step establishes the catalog of concrete `ModelDescriptor` entries that give the `ModelDispatcher` something real to dispatch against, specifically targeting:
- LOCAL tier: on-device models (Llama 3.2 1B/3B, Phi-3 Mini) for zero-cost classification and guardrails
- SMALL tier: cheap hosted models (Claude Haiku, GPT-4o Mini, Gemini 1.5 Flash) for classification, ranking, retrieval assist

## What was built

`core/routing/catalog.py`:
- `_LOCAL: list[ModelDescriptor]` — 3 entries: `llama-3.2-1b-local`, `llama-3.2-3b-local`, `phi-3-mini-local`
  - All `is_available=False` by default — operators must enable after deploying a backend
  - All `cost_per_1k_tokens=None` per LOCAL-tier invariant
  - Purposes: CLASSIFICATION, LOCAL_ASSIST, RANKING — exactly the guardrail use cases
- `_SMALL: list[ModelDescriptor]` — 3 entries: `claude-haiku-4-5`, `gpt-4o-mini`, `gemini-1.5-flash`
  - All available, cost-declared, latency-declared
  - Purposes: CLASSIFICATION, RANKING, RETRIEVAL_ASSIST, LOCAL_ASSIST
- `_MEDIUM: list[ModelDescriptor]` — 3 entries: `claude-sonnet-4-6`, `gpt-4o`, `gemini-1.5-pro`
- `_LARGE: list[ModelDescriptor]` — 1 entry: `claude-opus-4-7`
- `DEFAULT_MODELS: list[ModelDescriptor]` — flat union in tier order
- `build_default_registry(*, enable_local: bool = False) -> ModelRegistry`
  - Default: LOCAL tier skipped (no phantom models without a backend)
  - `enable_local=True`: LOCAL entries included (still `is_available=False` per-entry — operator must update)

## Design decisions

**LOCAL models disabled by default** — The 5-pass dispatcher filters availability before any pass. Registering LOCAL models as `is_available=False` means they're known to the registry (for inspection, tooling, documentation) but excluded from dispatch until an operator explicitly enables them. This avoids routing failures in environments with no local inference backend.

**Realistic metadata** — Every entry declares `cost_per_1k_tokens` and `p95_latency_ms`. This ensures the budget-aware dispatcher can make meaningful comparisons without falling back to `math.inf` sentinel values for any known model.

**Pure data, no logic** — `catalog.py` contains no routing logic. It only produces `ModelDescriptor` instances and a factory function, maintaining the invariant that all routing logic lives in `dispatcher.py`.

## Governance invariants preserved

- No parallel routing path: the catalog feeds the existing `ModelRegistry` + `ModelDispatcher`, nothing new
- LOCAL tier invariant: all LOCAL entries have `cost_per_1k_tokens=None`
- `is_available=False` on LOCAL entries until operator confirms backend is running
- `extra="forbid"` enforced via `ModelDescriptor` — no drift on fields

## Tests

`tests/routing/test_routing_catalog.py` — 30 tests covering:
- Catalog completeness: all four tiers, all target purposes, no duplicate IDs
- Metadata correctness: LOCAL has no cost, all entries have latency, non-LOCAL have cost
- LOCAL governance: all LOCAL entries are `is_available=False`, provider=LOCAL
- `build_default_registry`: excludes LOCAL by default, includes with `enable_local=True`
- `build_default_registry`: independent registry per call (no shared state)
- Dispatch integration: classification → SMALL, planning under cost cap → not LARGE, local model after operator enable → LOCAL

## Test suite result

1150 passed, 1 skipped, 0 failures (full suite).
