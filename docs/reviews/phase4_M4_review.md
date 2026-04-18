# Phase 4 M4 Review — RoutingAuditor: KPI-Vergleiche zwischen externen und internen Pfaden

**Step:** M4 — `RoutingAuditor` — dispatch attribution and cost/latency KPI tracking in TraceStore  
**Date:** 2026-04-18  
**Branch:** `codex/phase4-routing-auditor`  
**Status:** Complete

## Roadmap task addressed

> "KPI-Vergleiche zwischen externen und internen Pfaden etablieren"

Every dispatch decision now emits a structured span to `TraceStore` carrying:
- which tier was selected (LOCAL / SMALL / MEDIUM / LARGE)
- whether a fallback was used and why
- actual cost and latency of the selected model (when descriptor is provided)
- whether the dispatch failed entirely (`NoModelAvailableError`)

These spans enable operators to query the audit trail for tier-distribution, fallback rates, and cost-per-dispatch — the direct basis for LOCAL vs. external KPI comparisons.

## What was built

`core/routing/auditor.py` — `RoutingAuditor`:

```
RoutingAuditor(store: TraceStore | None)
  .record_dispatch(trace_id, request, result, *, descriptor=None, parent_span_id=None)
      → SpanRecord | None
  .record_routing_failure(trace_id, request, error, *, parent_span_id=None)
      → SpanRecord | None
```

**Span attributes:**

| Key | Source | Present on |
|-----|--------|-----------|
| `routing.request.purpose` | request | both |
| `routing.request.task_id` | request | both |
| `routing.request.prefer_local` | request | both |
| `routing.request.require_tool_use` | request | both |
| `routing.request.require_structured_output` | request | both |
| `routing.result.model_id` | result | dispatch / None on failure |
| `routing.result.provider` | result | dispatch / None on failure |
| `routing.result.tier` | result | dispatch / None on failure |
| `routing.result.fallback_used` | result | both |
| `routing.result.fallback_reason` | result | dispatch |
| `routing.result.cost_per_1k_tokens` | descriptor | dispatch (optional) |
| `routing.result.p95_latency_ms` | descriptor | dispatch (optional) |
| `routing.failure.reason` | error | failure only |

## Design decisions

**Analogous to `RetrievalAuditor` (R6)** — same conventions: `TYPE_CHECKING` import of `TraceStore`, best-effort emission (errors swallowed), no-op when `store=None`, single `SPAN_TYPE = "routing"` constant.

**Decoupled from `ModelDispatcher`** — `RoutingAuditor` is not embedded in `ModelDispatcher`. The orchestration layer calls both and passes the descriptor if it has it. This keeps the routing layer free of trace coupling and lets callers omit auditing when no trace context is available.

**Optional `descriptor` for KPIs** — passing `descriptor=None` still records a complete span (model_id, tier, fallback). When the caller has the descriptor from the registry, cost and latency are recorded too, enabling real cost-per-dispatch metrics.

**LOCAL tier transparency** — LOCAL-tier dispatches record `cost_per_1k_tokens=None` (per the LOCAL invariant), making it immediately clear in the audit trail that a zero-cost path was taken.

## Governance invariants preserved

- `TraceStore` is the single audit truth — no second audit store
- No routing logic in `auditor.py` — pure observation layer
- Best-effort: errors swallowed, never interrupt dispatch
- `TYPE_CHECKING` guard on `TraceStore` import — no circular dependency

## Tests

`tests/routing/test_routing_auditor.py` — 35 tests:
- Span type, name, status for dispatch and failure paths
- All start (request) attributes
- All finish (result) attributes: with and without descriptor, LOCAL descriptor cost=None
- No-store no-op for both methods
- `parent_span_id` threading
- Error swallowing (orphan trace_id)

## Test suite result

1185 passed, 1 skipped, 0 failures (full suite).
