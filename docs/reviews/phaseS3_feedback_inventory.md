# Phase S3 — User-Rating Feedback: Inventory

**Branch:** `codex/phaseS3-user-rating-feedback`
**Date:** 2026-04-12
**Scope:** Add optional `rating` field (0.0–1.0) to `ApprovalDecision`; propagate through Approval → FeedbackLoop → PerformanceHistory. No Provider-Fallback, no Semantic Matching, no Adaptive Threshold.

---

## 1. Canonical Touch-Point Map

### 1.1 `core/approval/models.py` — `ApprovalDecision`

**Current state:** `approval_id`, `decision`, `decided_by`, `decided_at`, `comment`, `metadata`.  
**Change (S3-2):** Add `rating: float | None = Field(default=None, ge=0.0, le=1.0)`.

`ApprovalDecision` is serialized in two places:
- `approval_store.record_decision()` → `request.metadata["decision"] = decision.model_dump(mode="json")`
- `resume_plan()` → `StepExecutionResult.metadata["approval_decision"] = decision.model_dump(mode="json")` (rejected path only)

Adding `rating` to the model means it flows into both serialized payloads automatically with zero additional storage code.

---

### 1.2 `core/approval/store.py` — `record_decision()`

**Current state:** Stores `decision.model_dump(mode="json")` in `request.metadata["decision"]`.  
**Change (S3):** None — rating flows through existing serialization automatically.

---

### 1.3 `core/orchestration/resume.py` — `resume_plan()`

**APPROVED path:**
```python
result = orchestrator.execute_plan(
    plan, ..., start_step_index=state.next_step_index or 0,
    approved_step_ids={state.next_step_id} if state.next_step_id else set(),
    ...
)
```
`execute_plan()` runs the approved step and calls `feedback_loop.update_performance(agent_id, execution_result)`. The `ExecutionResult.metadata` here is built by the adapter — it does **not** include `approval_decision` today.

**REJECTED path:**
```python
rejected_step = StepExecutionResult(
    ...,
    metadata={
        "approval_status": decision.decision.value,
        "approval_decision": decision.model_dump(mode="json"),  # ← rating lands here after S3-2
        "approval_reason": approval_request.reason,
    },
)
```
Rating lands in `metadata["approval_decision"]["rating"]` automatically after S3-2.

**Change (S3-5):** On APPROVED path, pass `approved_step_rating=decision.rating` to `execute_plan()`. The orchestrator injects `"approval_decision": {"rating": approved_step_rating}` into the step's `ExecutionResult.metadata` when running a pre-approved step. This makes the APPROVED and REJECTED paths symmetric for the feedback loop.

Also enrich `resume_span` attributes with `"user_rating": decision.rating`.

---

### 1.4 `core/orchestration/orchestrator.py` — `execute_plan()`

**Current signature (relevant part):**
```python
def execute_plan(self, plan, registry, routing_engine, execution_engine, feedback_loop, *,
                 approved_step_ids: set[str] | None = None, ...)
```
**Change (S3-5):** Add `approved_step_rating: float | None = None`. When executing a step whose `step_id` is in `approved_step_ids`, inject `"approval_decision": {"rating": approved_step_rating}` into `ExecutionResult.metadata` (or `StepExecutionResult.metadata`) before passing to `feedback_loop.update_performance()`.

---

### 1.5 `core/decision/feedback_loop.py` — `FeedbackUpdate` + `update_performance()`

**`FeedbackUpdate` current:** `agent_id`, `performance`, `score_delta`, `reward`, `token_count`, `dataset_size`, `training_metrics`, `warnings`.  
**Change (S3-3):** Add `user_rating: float | None = None`.

**`update_performance()` current:** Extracts `token_count` from `result.token_count`. Skips learning for rejected/cancelled/expired approval outcomes.  
**Change (S3-3):**
- Extract `user_rating = result.metadata.get("approval_decision", {}).get("rating")` (works for both APPROVED and REJECTED paths after S3-5 wires the approved path)
- Pass `user_rating=user_rating` to `record_result()`
- Return `user_rating=user_rating` in `FeedbackUpdate`

Note: For the rejected/skipped path, `user_rating` can still be extracted and stored even though learning is skipped — this preserves the rating signal without double-counting execution success.

---

### 1.6 `core/decision/performance_history.py` — `AgentPerformanceHistory` + `record_result()`

**`AgentPerformanceHistory` current:** `success_rate`, `avg_latency`, `avg_cost`, `avg_token_count`, `recent_failures`, `execution_count`, `load_factor`.  
**Change (S3-4):** Add `avg_user_rating: float = Field(default=0.0, ge=0.0)`.

**`record_result()` current signature:**
```python
def record_result(self, agent_id: str, *, success: bool, latency: float | None = None,
                  cost: float | None = None, token_count: int | None = None) -> AgentPerformanceHistory
```
**Change (S3-4):** Add `user_rating: float | None = None`; apply `_rolling_average(current.avg_user_rating, user_rating, execution_count)`. When `user_rating is None`, rolling average is preserved unchanged (same pattern as `token_count`).

---

### 1.7 `services/core.py` — `approve_plan_step()`, `reject_plan_step()`, `_decide_plan_step()`

**Current `approve_plan_step` / `reject_plan_step`:**  
Both accept `comment: str | None = None` and delegate to `_decide_plan_step()`.

**`_decide_plan_step()` current:**
```python
updated_request = approval_store.record_decision(
    approval_id,
    ApprovalDecision(
        approval_id=approval_id,
        decision=ApprovalStatus(decision),
        decided_by=decided_by,
        comment=comment,
        metadata=dict(metadata or {}),
    ),
)
result = resume_plan(updated_request, ...)
```

**Change (S3-5):**
- Add `rating: float | None = None` to `approve_plan_step()`, `reject_plan_step()`, and `_decide_plan_step()`
- Pass `rating=rating` when constructing `ApprovalDecision(...)`
- Pass `approved_step_rating=rating` to `resume_plan()` (approved path) — propagated via `execute_plan()`

---

### 1.8 `api_gateway/main.py` — `ApprovalDecisionRequest` + endpoints

**`ApprovalDecisionRequest` current:** `decided_by`, `comment`.  
**Change (S3-5):** Add `rating: float | None = Field(default=None, ge=0.0, le=1.0)`.

**`control_plane_approve()` / `control_plane_reject()` current:**
```python
return approve_plan_step(approval_id, decided_by=payload.decided_by, comment=payload.comment)
```
**Change (S3-5):** Add `rating=payload.rating`.

---

### 1.9 `frontend/agent-ui/src/pages/ApprovalsPage.tsx`

**Current state:** Approve/Reject buttons pass `comment` only. No rating input.  
**Change (S3-5):** Add a numeric rating input (0–5 stars or 0.0–1.0 slider) per pending approval. Normalize to 0.0–1.0. Pass `rating` in the API call.

---

### 1.10 `frontend/agent-ui/src/services/controlPlane.ts`

**`approve()` / `reject()` current:**
```typescript
body: JSON.stringify({ decided_by: 'agent-ui', comment })
```
**Change (S3-5):** Add `rating?: number` to both call bodies.

---

## 2. Data-Flow Summary

```
UI (ApprovalsPage)
  └─ rating input (0–5 stars → normalized 0.0–1.0)
       ↓ POST /control-plane/approvals/{id}/approve|reject
           body: { decided_by, comment, rating }

api_gateway/main.py  ApprovalDecisionRequest.rating
  └─ approve_plan_step(approval_id, ..., rating=payload.rating)

services/core.py  _decide_plan_step(rating=...)
  └─ ApprovalDecision(rating=rating)
       → approval_store.record_decision()
           stores rating in request.metadata["decision"]["rating"]

core/orchestration/resume.py  resume_plan()
  ├─ [APPROVED] orchestrator.execute_plan(..., approved_step_rating=decision.rating)
  │    └─ execution_result.metadata["approval_decision"] = {"rating": rating}  ← injected
  └─ [REJECTED] StepExecutionResult.metadata["approval_decision"]["rating"]  ← automatic via model_dump

core/decision/feedback_loop.py  update_performance()
  └─ user_rating = result.metadata.get("approval_decision", {}).get("rating")
       → record_result(..., user_rating=user_rating)
       → FeedbackUpdate(user_rating=user_rating)

core/decision/performance_history.py  AgentPerformanceHistory
  └─ avg_user_rating: float  (rolling average; None preserves current average)
```

---

## 3. Files Changed

| File | Change type |
|---|---|
| `core/approval/models.py` | Add `rating` field to `ApprovalDecision` |
| `core/orchestration/resume.py` | Pass rating to execute_plan; enrich resume_span |
| `core/orchestration/orchestrator.py` | Accept + inject `approved_step_rating` |
| `core/decision/feedback_loop.py` | Extract rating; add to `FeedbackUpdate` |
| `core/decision/performance_history.py` | Add `avg_user_rating`; extend `record_result()` |
| `services/core.py` | Add `rating` param to approve/reject/decide functions |
| `api_gateway/main.py` | Add `rating` to `ApprovalDecisionRequest` and endpoints |
| `frontend/agent-ui/src/pages/ApprovalsPage.tsx` | Add rating input |
| `frontend/agent-ui/src/services/controlPlane.ts` | Pass rating in approve/reject requests |

---

## 4. Explicit Non-Changes (Out of Scope)

- `PolicyRule` / `PolicyEvaluationContext` — no rating-based governance rules
- `RoutingEngine` scoring — no rating-based routing weights (future S4)
- Provider-Fallback / Semantic Matching / Adaptive Threshold — excluded per scope definition
- `ApprovalRequest` model — not modified; rating lives on `ApprovalDecision` only
- `ExecutionResult.cost` — sole canonical cost truth, unchanged
