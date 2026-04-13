# Phase S4 — Provider Fallback Resilience: Inventory

**Branch:** `codex/phaseS4-provider-fallback-resilience`
**Date:** 2026-04-13
**Scope:** Controlled single-attempt provider fallback within the canonical orchestration step path.

---

## 1. Today's Canonical Step Path

```
PlanExecutionOrchestrator._execute_step()
  │
  ├─ routing_engine.route_step(step, task, descriptors)
  │    → route_intent(intent, descriptors)
  │         → candidate_filter.filter_candidates(intent, descriptors)  [hard policy]
  │         → neural_policy.score_candidates(...)                       [ranking]
  │    → RoutingDecision(selected_agent_id=...)
  │
  ├─ policy_engine.evaluate(step_intent, selected_descriptor)           [governance]
  │    → enforce_policy(policy_decision)
  │         → DENY    → StepExecutionResult(policy_effect="deny")
  │         → APPROVAL_REQUIRED + step not approved → pause, emit ApprovalRequest
  │         → ALLOW   → continue
  │
  ├─ execution_engine.execute(step_task, decision, registry)            [execution]
  │    → adapter.execute(task, descriptor)
  │    → ExecutionResult(success=bool, error=StructuredError|None, ...)
  │
  ├─ feedback_loop.update_performance(agent_id, execution_result)       [learning]
  │    → PerformanceHistoryStore.record_result(...)
  │
  └─ StepExecutionResult.from_execution_result(step_id, execution, metadata)
       → returned to _execute_group → aggregate → PlanExecutionResult
```

**Existing adapter error codes:**

| Error code | Source | Semantics |
|---|---|---|
| `adapter_unavailable` | claude_code, codex | CLI binary not found — clear provider absence |
| `adapter_timeout` | claude_code, codex, openhands | Subprocess/HTTP timeout — provider unresponsive |
| `adapter_transport_error` | openhands | Network-level connection failure |
| `adapter_http_error` | openhands | HTTP non-2xx (includes 4xx — ambiguous) |
| `adapter_process_error` | claude_code, codex | Non-zero CLI exit — ambiguous (domain or infra) |
| `adapter_protocol_error` | claude_code, codex, openhands | Invalid JSON — adapter-side issue |
| `adapter_execution_error` | flowise, n8n | Generic HTTP/execution failure |
| `missing_selected_agent` | execution_engine | No agent selected by routing |

---

## 2. Where Fallback Hooks In Cleanly

**Single canonical injection point:** `_execute_step()` in `orchestrator.py`, immediately after the primary `execution_engine.execute()` call.

```
execution = execution_engine.execute(...)
if not execution.success and is_fallback_eligible(execution):    # ← S4 hook
    # record primary failure to FeedbackLoop
    # re-route with exclude_agent_ids={primary_agent_id}
    # re-run governance for fallback agent
    # execute fallback agent
    # record fallback feedback
    # return fallback StepExecutionResult (or compounded failure)
```

This is the only place where:
- We have the primary `ExecutionResult` with a classified error
- We still have all routing/governance/feedback machinery in scope
- We are inside a span context that can record both attempts
- We have not yet committed a `StepExecutionResult` to the plan state

---

## 3. Exclusion Architecture

**Decision:** Option A — `route_step(..., exclude_agent_ids=set[str] | None)`.

Rationale:
- Exclusion is a runtime concern (this specific failed agent for this specific attempt), not a deterministic policy concern
- `CandidateFilter` encodes structural policy (capabilities, trust, availability) — wrong layer for ephemeral exclusion
- Pre-filtering the descriptor list before passing to `route_intent` is the cleanest pattern
- Adds one optional `exclude_agent_ids` parameter to `route_step()` and `route_intent()` — zero impact on callers that don't pass it

Implementation:
```python
def route_step(self, step, task, descriptors, *, exclude_agent_ids=None):
    # filter descriptors BEFORE route_intent
    filtered = [d for d in descriptors if d.agent_id not in (exclude_agent_ids or set())]
    return self.route_intent(intent, filtered, ...)
```

---

## 4. Fallback-Eligible Error Codes

S4 uses a strict whitelist of clearly infrastructure-level errors:

```python
_FALLBACK_ELIGIBLE_CODES = frozenset({
    "adapter_unavailable",    # CLI not installed/found → provider absence
    "adapter_timeout",        # timed out → provider unresponsive
    "adapter_transport_error", # network connection failure → transport down
})
```

NOT fallback-eligible:
- `adapter_process_error` — non-zero exit: ambiguous (could be domain failure in the task itself)
- `adapter_protocol_error` — bad JSON: likely adapter/config issue, not provider failure
- `adapter_execution_error` — too generic to classify safely
- `adapter_http_error` — includes 4xx (task errors), not always provider failure
- `missing_selected_agent` — routing failure, not a provider error
- Policy deny / user rejection / approval expiry — explicit decisions

---

## 5. Invariants Not to Violate

1. **No double execution of same Step by same Agent.** Once `feedback_loop.update_performance()` is called for an agent on a step, it must not be called again for the same (agent, step) pair.

2. **Governance is always enforced.** The fallback agent MUST go through `policy_engine.evaluate()`. A pre-existing approval covers the STEP (not a specific agent), but the new agent may trigger a deny or new approval requirement.

3. **Approval semantics:** If `step.step_id in approved_step_ids`, the human approval covers the step regardless of which agent executes it. The approval gate is skipped. If the fallback agent needs fresh approval and the step is NOT approved, the step must pause (not auto-approve).

4. **Bounded fallback.** Maximum one fallback attempt per step. No recursive fallback, no while-loop retries.

5. **Feedback separation.** Primary failure → recorded as failure for primary agent. Fallback result → recorded for fallback agent only. Never mix.

6. **No silent fallback.** Trace/spans must record: primary failure, fallback trigger, exclusion, fallback routing decision, fallback execution result.

7. **Single orchestrator.** `_execute_step` handles both primary and fallback inline. No second orchestrator, no external retry queue.

---

## 6. Files Changed in S4

| File | Change |
|---|---|
| `core/execution/adapters/base.py` | Add `is_fallback_eligible(result)` function |
| `core/decision/routing_engine.py` | Add `exclude_agent_ids` to `route_step()` + `route_intent()` |
| `core/orchestration/orchestrator.py` | Add `_attempt_fallback_step()` + wire into `_execute_step()` |
| Tests | S4 coverage: eligible/non-eligible errors, exclusion, governance, feedback semantics, trace |
