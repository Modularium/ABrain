# Phase S1 — Observability/Feedback Backbone: Pre-Implementation Inventory

## 1. Scope

Phase S1 adds `token_count` (and confirms `api_cost`/`cost`) as first-class signals flowing through the canonical execution → feedback → trace pipeline. This document inventories the current dataflow, identifies every file that requires a change, and confirms no parallel implementation is introduced.

---

## 2. Current Dataflow (Pre-S1)

```
Adapter.execute()
  → ExecutionResult { agent_id, success, output, metadata, warnings, error, duration_ms, cost }
  
ExecutionEngine.execute()
  → returns ExecutionResult unchanged (no enrichment)

PlanExecutionOrchestrator._execute_step()
  1. execution_engine.execute() → ExecutionResult
  2. finish_span(execution_span, attributes={success, duration_ms, cost, ...})    ← cost is there
  3. feedback_loop.update_performance(agent_id, execution, ...)
     → performance_history.record_result(agent_id, success, latency, cost)        ← cost is there
     → FeedbackUpdate { agent_id, performance, score_delta, reward, ... }
  4. finish_span(feedback_span, attributes={reward, dataset_size, ...})
```

**What is missing:**
- `ExecutionResult` has no `token_count` field (adapters cannot surface it)
- `AgentPerformanceHistory` has no `avg_token_count` field (rolling average not computed)
- `PerformanceHistoryStore.record_result()` has no `token_count` parameter
- `FeedbackUpdate` has no `token_count` field (not forwarded to caller)
- Execution span attributes do not include `"token_count"`
- Feedback span attributes do not include `"token_count"`

**What already exists (no duplicate needed):**
- `ExecutionResult.cost: float | None` — this IS the `api_cost` field; naming is canonical, no rename needed
- `AgentPerformanceHistory.avg_cost` — rolling average already computed from `cost`
- `PerformanceHistoryStore.record_result(cost=...)` — already accepted and averaged

---

## 3. Files Requiring Changes

### 3.1 `core/execution/adapters/base.py`
**Change:** Add `token_count: int | None = None` to `ExecutionResult`.  
**Why:** This is the canonical output type. Every adapter returns it. Adding the field here makes token data available to all downstream consumers (feedback loop, trace).  
**Risk:** Minimal — additive, `extra="forbid"` means existing code producing `ExecutionResult` without `token_count` will default to `None`.

### 3.2 `core/decision/performance_history.py`
**Change 1:** Add `avg_token_count: float = Field(default=0.0, ge=0.0)` to `AgentPerformanceHistory`.  
**Change 2:** Add `token_count: int | None = None` parameter to `PerformanceHistoryStore.record_result()`. Compute rolling average using `_rolling_average()`.  
**Why:** `PerformanceHistoryStore` is the canonical per-agent performance snapshot. Token efficiency is a meaningful signal alongside cost and latency.  
**Risk:** Minimal — additive field with default, backward-compatible parameter.

### 3.3 `core/decision/feedback_loop.py`
**Change 1:** Add `token_count: int | None = None` to `FeedbackUpdate`.  
**Change 2:** In `update_performance()`, pass `token_count=result.token_count` to `record_result()` and include `token_count=result.token_count` in the returned `FeedbackUpdate`.  
**Why:** `FeedbackUpdate` is the structured result of a feedback cycle. Surfacing `token_count` there allows callers (e.g., orchestrator, services) to log or inspect it.  
**Risk:** Minimal — new optional field, existing call sites unaffected.

### 3.4 `core/orchestration/orchestrator.py`
**Change 1:** Add `"token_count": execution.token_count` to execution span attributes.  
**Change 2:** Add `"token_count": feedback.token_count` to feedback span attributes.  
**Why:** Spans are the audit/trace vehicle. Recording token_count per span makes it SQL-queryable via TraceStore.  
**Risk:** None — `SpanRecord.attributes` is `dict[str, Any]`, adding a key is purely additive.

---

## 4. Files NOT Requiring Changes

| File | Reason |
|---|---|
| `core/execution/execution_engine.py` | Simple pass-through — returns adapter result unchanged |
| `core/audit/trace_models.py` | `SpanRecord.attributes: dict[str, Any]` — already flexible |
| `core/audit/context.py` | `finish_span(attributes=...)` accepts arbitrary dict |
| `core/approval/models.py` | User-rating is explicitly excluded from S1 |
| `core/governance/` | Policy rules for cost-ceiling excluded from S1 |
| `services/core.py` | Passes `ExecutionResult` by reference — new field is transparent |

---

## 5. Adapter Assessment

### Adapters that CAN realistically populate `token_count`:
- **`adapters/claude/`** / **`adapters/codex/`** — Claude API and Codex responses include `usage.input_tokens + usage.output_tokens`. These adapters can extract token counts from API responses.
- **`adapters/flowise/`** — Flowise REST responses may include token usage depending on model configuration; best-effort.

### Adapters where `token_count = None` is correct:
- **`adapters/adminbot/`** — Internal bot, no LLM API call, token count meaningless.
- **`adapters/openhands/`** — External agent, token data not exposed in current response format.

### S1 position on adapters:
S1 does **not** modify any adapter. Adding `token_count: int | None = None` to `ExecutionResult` is sufficient — adapters that know their token usage can start setting the field in a future phase (S2+). The field being `None` by default means zero breaking changes.

---

## 6. No Parallel Implementation

This change is strictly additive within the canonical pipeline:
- No new managers, no new stores, no new threads
- No MLflow, no Redis, no Prometheus
- No second truth source for token data — `ExecutionResult.token_count` is the single origin
- `PerformanceHistoryStore` remains the single performance aggregate
- `TraceStore` remains the single audit sink

The pattern matches the existing `cost` field: origin in `ExecutionResult`, rolling average in `PerformanceHistoryStore`, surfaced in `FeedbackUpdate`, recorded in trace spans.

---

## 7. Summary of Changes

| File | Type | Breaking? |
|---|---|---|
| `core/execution/adapters/base.py` | Add field `token_count: int \| None = None` | No |
| `core/decision/performance_history.py` | Add field `avg_token_count`, add param `token_count` | No |
| `core/decision/feedback_loop.py` | Add field `token_count` to FeedbackUpdate, pass through | No |
| `core/orchestration/orchestrator.py` | Add `token_count` to 2 span attribute dicts | No |
