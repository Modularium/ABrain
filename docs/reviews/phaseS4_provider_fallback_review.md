# Phase S4 — Provider Fallback Resilience: Post-Implementation Review

**Branch:** `codex/phaseS4-provider-fallback-resilience`
**Date:** 2026-04-13
**Status:** PASS — implementation is architecturally clean, all invariants satisfied, full test coverage

---

## 1. Scope

Controlled single-attempt provider fallback within the canonical orchestration step path.  When a step execution fails with a clear infrastructure-level error, the orchestrator re-routes to an alternative agent (excluding the failed one), re-enforces governance, and executes once.  No recursive retries, no second orchestrator, no bypass of any canonical layer.

---

## 2. Files Changed

| File | Change |
|---|---|
| `core/execution/adapters/base.py` | Added `_FALLBACK_ELIGIBLE_ERROR_CODES` frozenset + `is_fallback_eligible()` free function |
| `core/decision/routing_engine.py` | Added `exclude_agent_ids: set[str] | None = None` to `route_step()` with pre-filtering before `route_intent` |
| `core/orchestration/orchestrator.py` | Added `_FallbackAttemptResult` dataclass, `_attempt_fallback_step()` method, fallback hook wired into `_execute_step()` |
| `tests/orchestration/test_fallback_resilience.py` | 27 new tests covering all S4 paths |
| `docs/reviews/phaseS4_resilience_inventory.md` | Pre-implementation inventory (written in S4-1) |

---

## 3. Invariant Verification

| # | Invariant | Status |
|---|---|---|
| 1 | No double execution of same step by same agent | ✓ `_execute_step` fallback check runs once; `execution = _fallback.fallback_execution` overwrites for metadata only |
| 2 | Governance always enforced | ✓ `_attempt_fallback_step` runs `policy_engine.evaluate()` for fallback agent before execution |
| 3 | Approval semantics: pre-approval covers step not agent | ✓ `step.step_id not in approved_step_ids` check before creating new ApprovalRequest; pre-approved steps skip gate |
| 4 | Bounded fallback — max one attempt per step | ✓ `if not execution.success and is_fallback_eligible(execution)` evaluated once on primary result; fallback execution never re-checked |
| 5 | Feedback separation | ✓ Primary feedback recorded inside `_attempt_fallback_step` before any fallback attempt; fallback feedback recorded after fallback execution only |
| 6 | No silent fallback | ✓ `fallback_triggered` span event on `step_span`; `fallback_triggered`, `primary_agent_id`, `primary_error_code`, `fallback_agent_id`, `fallback_routing_decision` in step metadata |
| 7 | Single orchestrator | ✓ Inline in `_execute_step`; no secondary orchestrator, no external queue |

---

## 4. Error Code Classification

**Fallback-eligible (whitelist):**

```python
_FALLBACK_ELIGIBLE_ERROR_CODES = frozenset({
    "adapter_unavailable",      # CLI not found — provider absent
    "adapter_timeout",          # subprocess/HTTP timeout — provider unresponsive
    "adapter_transport_error",  # network-level connection failure
})
```

**Not fallback-eligible (intentional exclusions):**

| Code | Reason excluded |
|---|---|
| `adapter_process_error` | Non-zero CLI exit — ambiguous: could be domain failure in the task itself |
| `adapter_protocol_error` | Invalid JSON — likely adapter/config issue, not provider failure |
| `adapter_execution_error` | Too generic to classify safely as infrastructure |
| `adapter_http_error` | Includes 4xx (task errors); not reliably a provider-level failure |
| `missing_selected_agent` | Routing failure, not a provider error |

---

## 5. Canonical Step Path After S4

```
PlanExecutionOrchestrator._execute_step()
  │
  ├─ routing_engine.route_step(step, task, descriptors)     [primary routing]
  ├─ policy_engine.evaluate(...)                             [primary governance]
  ├─ execution_engine.execute(...)                           [primary execution]
  │
  │  if not success and is_fallback_eligible(execution):
  │    └─ _attempt_fallback_step()                           [S4 fallback hook]
  │         ├─ feedback_loop.update_performance(primary)     [primary feedback]
  │         ├─ route_step(exclude_agent_ids={primary})       [fallback routing]
  │         ├─ policy_engine.evaluate(fallback_agent)        [fallback governance]
  │         ├─ execution_engine.execute(fallback_decision)   [fallback execution]
  │         └─ feedback_loop.update_performance(fallback)    [fallback feedback]
  │
  ├─ feedback_loop.update_performance(agent_id, execution)   [normal path only]
  └─ StepExecutionResult.from_execution_result(...)
```

---

## 6. Test Coverage

| Scenario | Test |
|---|---|
| Eligible codes whitelist | `test_is_fallback_eligible_true_on_all_whitelisted_codes` |
| Non-eligible codes blocked | `test_is_fallback_eligible_false_on_non_eligible_code[*]` (parametrized × 5) |
| Success never triggers fallback | `test_is_fallback_eligible_false_on_success` |
| No error field handled | `test_is_fallback_eligible_false_when_no_error_field` |
| `exclude_agent_ids` removes candidate | `test_route_step_exclude_agent_ids_removes_candidate` |
| All agents excluded → no selection | `test_route_step_exclude_all_agents_returns_no_selection` |
| No exclusion unchanged | `test_route_step_no_exclusion_behaves_as_before` |
| Fallback succeeds on `adapter_timeout` | `test_fallback_triggers_on_eligible_error_and_succeeds` |
| Fallback succeeds on `adapter_unavailable` | `test_fallback_triggers_on_adapter_unavailable` |
| Fallback succeeds on `adapter_transport_error` | `test_fallback_triggers_on_adapter_transport_error` |
| Non-eligible error no fallback | `test_fallback_not_triggered_on_non_eligible_error` |
| Success no fallback | `test_fallback_not_triggered_on_success` |
| No candidate → primary failure | `test_fallback_no_candidate_returns_primary_failure` |
| Governance denies fallback | `test_fallback_governance_deny_returns_primary_failure` |
| Approval required + not pre-approved → paused | `test_fallback_approval_required_and_step_not_approved_pauses` |
| Approval required + pre-approved → continues | `test_fallback_approval_required_but_step_pre_approved_continues` |
| Primary failure feedback recorded | `test_feedback_primary_failure_recorded_before_fallback` |
| No mixing when no fallback | `test_feedback_no_mix_when_no_fallback_triggered` |
| Primary only when no candidate | `test_feedback_primary_only_when_no_fallback_candidate` |
| Both fail → both recorded separately | `test_feedback_fallback_failure_recorded_when_both_fail` |
| Two routing calls on fallback | `test_routing_called_twice_on_fallback` |
| One routing call on success | `test_routing_called_once_on_success` |
| Bounded: exactly one fallback attempt | `test_fallback_bounded_to_single_attempt` |

**Total: 27 tests, all passing.  Full regression suite: 151 tests, 0 failures.**

---

## 7. Architecture Notes

**Why injection in `_execute_step` rather than a new orchestrator layer:**
The fallback hook sits immediately after `finish_span(execution_span)`, where all routing/governance/feedback machinery is in scope, the primary `ExecutionResult` is classified, and a `StepExecutionResult` has not yet been committed.  This is the only correct point: earlier means the primary span isn't finished; later means feedback has already been double-recorded.

**Why exclusion in `route_step` rather than `CandidateFilter`:**
`CandidateFilter` encodes structural policy (capabilities, trust, availability).  The failed-agent exclusion is ephemeral runtime state for this specific step attempt.  Pre-filtering the descriptor list before `route_intent` is zero-intrusion on `CandidateFilter` semantics.

**Why feedback separation matters:**
Recording primary failure for primary agent and fallback result for fallback agent independently preserves the performance history signal for each.  Mixing them would inflate the primary's failure count on fallback success, or credit the fallback agent for work it didn't do.
