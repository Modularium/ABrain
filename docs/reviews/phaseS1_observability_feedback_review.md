# Phase S1 — Observability/Feedback Backbone: Implementation Review

## 1. What Was Built

Phase S1 adds `token_count` as a first-class signal through the canonical execution → feedback → trace pipeline. It also confirms that `api_cost` already existed as `ExecutionResult.cost` and documents that no duplicate field was introduced.

---

## 2. Changes Made

### 2.1 `core/execution/adapters/base.py`
```python
# Added to ExecutionResult:
token_count: int | None = None
```
Single new optional field. `extra="forbid"` means no metadata hacks needed; the field is formally typed.

### 2.2 `core/decision/performance_history.py`
```python
# Added to AgentPerformanceHistory:
avg_token_count: float = Field(default=0.0, ge=0.0)

# Extended PerformanceHistoryStore.record_result():
def record_result(self, agent_id, *, success, latency=None, cost=None, token_count=None):
    ...
    avg_token_count=self._rolling_average(
        current.avg_token_count,
        float(token_count) if token_count is not None else None,
        execution_count,
    ),
```
Rolling average consistent with the existing `avg_cost` and `avg_latency` pattern. `None` input preserves the existing average unchanged.

### 2.3 `core/decision/feedback_loop.py`
```python
# Added to FeedbackUpdate:
token_count: int | None = None

# Extended update_performance() call to record_result:
token_count=result.token_count,

# Extended returned FeedbackUpdate:
token_count=result.token_count,
```
`token_count` flows from `ExecutionResult` → `PerformanceHistoryStore.record_result()` → `FeedbackUpdate`.

### 2.4 `core/orchestration/orchestrator.py`
Two span attribute enrichments:

**Execution span:**
```python
"token_count": execution.token_count,
```

**Feedback span:**
```python
"token_count": feedback.token_count,
```

Token count is now recorded in TraceStore alongside cost and latency — SQL-queryable per execution.

### 2.5 `core/execution/adapters/claude_code_adapter.py`
```python
token_count=self._extract_token_count(data),

def _extract_token_count(self, data):
    usage = data.get("usage")
    if isinstance(usage, Mapping):
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        ...
        return total if total > 0 else None
    return None
```

### 2.6 `core/execution/adapters/codex_adapter.py`
Identical `_extract_token_count` method added. Handles both `input_tokens/output_tokens` (Claude) and `prompt_tokens/completion_tokens` (OpenAI) naming conventions.

---

## 3. Tests Added

| File | New Tests |
|---|---|
| `tests/decision/test_performance_history.py` | `test_performance_history_records_token_count`, `test_performance_history_token_count_none_does_not_reset_average`, `test_performance_history_default_avg_token_count` |
| `tests/decision/test_feedback_loop.py` | `test_feedback_loop_propagates_token_count`, `test_feedback_loop_token_count_none_when_absent` |
| `tests/execution/test_execution_engine.py` | `test_execution_result_token_count_defaults_none` |

Full test suite result: **168 passed, 1 skipped, 0 failed.**

---

## 4. Architecture Cross-Check Against R2 Criteria

| Criterion | Status |
|---|---|
| No second runtime created | ✅ Pure model extension |
| No parallel truth source for token data | ✅ Single origin: `ExecutionResult.token_count` |
| No EvaluationManager revival | ✅ Not present anywhere |
| No MLflow introduced | ✅ TraceStore/SpanRecord only |
| No Redis, no torch, no heavy deps added | ✅ Pure Python |
| Policy/Approval layer unchanged | ✅ Excluded from S1 per spec |
| All changes additive, no breaking changes | ✅ All fields default `None` |
| `extra="forbid"` models extended formally | ✅ Fields declared in Pydantic models |
| Flows through canonical pipeline: Execution → Feedback → Trace | ✅ |

---

## 5. Adapter Coverage

| Adapter | `token_count` support | Notes |
|---|---|---|
| `claude_code_adapter` | **Yes** | Extracts from `usage.input_tokens + usage.output_tokens` |
| `codex_adapter` | **Yes** | Extracts from `usage.prompt_tokens + usage.completion_tokens` |
| `adminbot_adapter` | None (correct) | No LLM call, token count not meaningful |
| `flowise_adapter` | None (correct) | Workflow orchestrator, not raw LLM |
| `n8n_adapter` | None (correct) | Workflow orchestrator, not raw LLM |
| `openhands_adapter` | None (correct) | External agent, token data not in current response format |

---

## 6. What S1 Enables for Future Phases

| Future Phase | What S1 Provides |
|---|---|
| S2 / R3-Kandidat-3: Cost-Ceiling PolicyRule | `execution.cost` already flows; `token_count` now also available in `PolicyEvaluationContext` extension |
| S2 / R3-Kandidat-2: Agent-Health PolicyRule | `PerformanceHistoryStore` now has `avg_token_count` as additional health dimension |
| S2 / R4-Kandidat-6: Agent-Health-Monitor CLI | `avg_token_count` queryable from `PerformanceHistoryStore.get()` |
| Observability dashboards | `TraceStore` spans now carry `token_count` — one SQL GROUP BY away |

---

## 7. What S1 Explicitly Did NOT Do (Per Spec)

- No new PolicyRule for cost ceiling
- No Provider-Fallback in Orchestrator
- No Semantic Text-Similarity
- No User-Rating in ApprovalDecision
- No adapter was modified to be broken — all changes are additive
