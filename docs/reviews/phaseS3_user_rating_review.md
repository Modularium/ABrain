# Phase S3 — User-Rating Feedback: Post-Implementation Review

**Branch:** `codex/phaseS3-user-rating-feedback`
**Date:** 2026-04-13
**Scope:** Optional `rating` (0.0–1.0) on `ApprovalDecision`; flows Approval → Orchestration → FeedbackLoop → PerformanceHistory. Frontend star-rating input.

---

## 1. Architecture Cross-Check

### 1.1 Canonical Pipeline Integrity

The ABrain pipeline is: Decision → Governance → Approval → Execution → Audit.  
Phase S3 adds an optional signal that rides the **existing** Approval → Execution → Feedback path. No new layers, no parallel stacks.

| Check | Result |
|---|---|
| Rating stored only on `ApprovalDecision` (correct model) | ✓ |
| Serialization path: `model_dump()` → stored in `request.metadata["decision"]` → deserialized in `resume_plan()` | ✓ automatic |
| No new storage tables, no schema migration | ✓ |
| `ExecutionResult.cost` is sole canonical cost truth (unchanged) | ✓ |
| `avg_user_rating` uses existing `_rolling_average()` pattern identical to `avg_token_count` | ✓ |
| `ConfigDict(extra="forbid")` preserved — `rating` is a formal field on `ApprovalDecision` | ✓ |
| All new fields default `None` / `0.0` — no breaking changes | ✓ |

### 1.2 Approved Path (HITL → Execute → Learn)

```
ApprovalDecision.rating
  → orchestrator.execute_plan(approved_step_rating=decision.rating)
    → _execute_step: execution.metadata["approval_decision"] = {"rating": rating}
      → feedback_loop.update_performance() extracts user_rating
        → record_result(user_rating=...) → avg_user_rating rolling average
```

Injection point (`execution.metadata["approval_decision"]`) mirrors the structure already used on the rejected path — uniform extraction in `FeedbackLoop.update_performance()`.

### 1.3 Rejected Path (HITL → Skip Learn → Surface Rating)

```
ApprovalDecision.rating
  → decision.model_dump() → StepExecutionResult.metadata["approval_decision"]["rating"]
    → feedback_loop.update_performance() extracts user_rating
      → returns FeedbackUpdate(user_rating=rating, score_delta=0)
      → execution_count NOT incremented (learning correctly skipped)
```

Rating is surfaced in `FeedbackUpdate` even on rejection, without double-counting execution success.

### 1.4 Trace Consistency

- `resume_span` attributes include `"user_rating": decision.rating`
- `feedback_span` attributes (orchestrator + `run_task` path) include `"user_rating": feedback.user_rating`
- Rating is observable in the `SpanRecord.attributes` open-schema dict without any audit model migration

### 1.5 API / Frontend

- `ApprovalDecisionRequest` now accepts `rating: float | None` (validated 0.0–1.0 by Pydantic)
- Both `/approve` and `/reject` endpoints forward `rating` down to `approve_plan_step` / `reject_plan_step`
- Frontend `ApprovalsPage` renders a 5-star selector; normalizes to 0.0–1.0 before sending
- `controlPlane.ts` `approve()` / `reject()` accept an optional `rating` parameter

---

## 2. Files Changed

| File | Change |
|---|---|
| `core/approval/models.py` | `ApprovalDecision.rating: float | None` (ge=0, le=1) |
| `core/orchestration/resume.py` | Pass `approved_step_rating=decision.rating` to `execute_plan()`; add `user_rating` to resume span |
| `core/orchestration/orchestrator.py` | `execute_plan/group/step` accept `approved_step_rating`; inject into execution metadata; add `user_rating` to feedback span |
| `core/decision/feedback_loop.py` | `FeedbackUpdate.user_rating`; extract from `metadata["approval_decision"]["rating"]` |
| `core/decision/performance_history.py` | `AgentPerformanceHistory.avg_user_rating`; `record_result(user_rating=...)` |
| `services/core.py` | `approve/reject/decide_plan_step` accept `rating`; feedback span includes `user_rating` |
| `api_gateway/main.py` | `ApprovalDecisionRequest.rating`; endpoints forward rating |
| `frontend/.../ApprovalsPage.tsx` | 5-star rating input; normalizes to 0.0–1.0 |
| `frontend/.../controlPlane.ts` | `approve/reject` accept optional `rating` |

---

## 3. Tests Added

| Test file | Tests added |
|---|---|
| `tests/approval/test_models.py` | `rating` accepted, serialized, defaults None, rejects out-of-range |
| `tests/decision/test_performance_history.py` | `avg_user_rating` rolling average; None preserves average; default 0.0 |
| `tests/decision/test_feedback_loop.py` | Rating extracted from metadata; None when absent; surfaced on rejection without learning |
| `tests/services/test_approval_flow.py` | Approve with rating → `avg_user_rating` updated; reject with rating → stored in decision metadata |
| `tests/core/test_control_plane_gateway.py` | Updated existing stub to accept `rating` kwarg |

**Full suite: 179 passed, 1 skipped (pre-existing integration skip), 0 failures.**

---

## 4. Explicit Non-Changes (Confirmed Out of Scope)

- `PolicyRule` / `PolicyEvaluationContext` — no rating-based governance rules introduced
- `RoutingEngine` scoring — `avg_user_rating` is stored but not yet wired into routing weights
- Provider-Fallback — not implemented
- Semantic Matching — not implemented
- Adaptive Threshold — not implemented
- `ApprovalRequest` model — not modified
- `ExecutionResult.cost` — unchanged

---

## 5. Verdict

**Architecture: CLEAN.** Rating is an additive optional signal with zero breaking changes. All serialization flows through the existing `ApprovalDecision.model_dump()` path. Both HITL paths (approved and rejected) surface the rating symmetrically to `FeedbackLoop`. The `avg_user_rating` field follows the established rolling-average pattern from `avg_token_count` (Phase S1). Full test suite passes.

**Ready for merge-gate review.**
