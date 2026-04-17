# Phase 4 M2 Review — Budget-aware ModelDispatcher + Fallback Cascades

**Step:** M2 — `ModelDispatcher` with five-pass fallback cascade  
**Date:** 2026-04-17  
**Status:** Complete

## What was built

`core/routing/dispatcher.py` — stateless model routing with budget enforcement:

- `ModelRoutingRequest` (Pydantic, `extra="forbid"`) — purpose, cost/latency budgets, capability flags, `prefer_local` hint, `task_id`
- `ModelRoutingResult` (Pydantic, `extra="forbid"`) — selected model + provider/tier/purposes + fallback metadata + `selected_reason`
- `NoModelAvailableError(RuntimeError)` — carries `reason` and `request`; analogous to `RetrievalPolicyViolation`
- `ModelDispatcher.dispatch()` — thin class wrapper around module-level `_dispatch()`
- Five-pass fallback cascade: strict → no-latency → no-cost → no-budget → no-caps
- Sort key per candidate: `(local_bonus, tier_order, cost_or_inf, latency_or_inf)` — lower preferred
- `_TIER_ORDER = {LOCAL:0, SMALL:1, MEDIUM:2, LARGE:3}` — cost-ascending
- `prefer_local=True` gives LOCAL an extra first-dimension bonus (redundant with tier order for LOCAL vs non-LOCAL, but documents the preference)

## Design decisions

**Five-pass cascade** — each pass relaxes exactly one constraint class before yielding to the next. This is explicit and auditable: `fallback_reason` always names which constraint was relaxed, letting operators diagnose why a fallback fired.

**Sentinel infinity for unknown cost/latency** — `None` fields sort after all known values. This avoids silently preferring under-documented models and incentivises operators to fill in metadata.

**Stateless module-level `_dispatch()`** — tested independently of the `ModelDispatcher` class wrapper; no registry mutation, no I/O, no side effects.

**`NoModelAvailableError` carries the request** — callers can log or surface full routing context on failure without needing to re-construct the request.

## Tests

`tests/routing/test_routing_dispatcher.py` — 38 tests covering:
- Strict pass happy path (fallback_used=False, fallback_reason=None)
- Each of the five fallback passes individually
- Prefer-local sort ordering
- Tier ordering (SMALL < MEDIUM < LARGE)
- Cost and latency ordering within tier
- Unknown cost/latency sentinel sorting
- Capability filtering (tool_use, structured_output, both)
- Availability exclusion from all passes
- `NoModelAvailableError` (empty registry, wrong purpose, all unavailable, carries reason/request)
- Request/result validation (extra fields, out-of-range budgets)
- `selected_reason` content (mentions purpose and tier)

## Exports updated

`core/routing/__init__.py` now exports:
`ModelDispatcher`, `ModelRoutingRequest`, `ModelRoutingResult`, `NoModelAvailableError`

## Test suite result

1120 passed, 1 skipped, 0 failures (full suite including all prior phases).
