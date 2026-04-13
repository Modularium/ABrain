# Control Plane API Mapping

## Principle

The UI talks to the API gateway. The API gateway exposes thin `/control-plane/*` routes. Those routes call canonical `services/core.py` functions or minimal read-only helpers derived from them.

For external developers, the same route family is now the canonical documented
HTTP surface via `/docs`, `/redoc` and `/openapi.json`. Compatibility or
experimental helper routes remain outside the public OpenAPI contract so the
gateway still has one external HTTP truth.

## View To API To Core Mapping

| UI View / Action | HTTP Route | Core Mapping |
| --- | --- | --- |
| Overview summary | `GET /control-plane/overview` | Aggregates `list_agent_catalog`, `list_pending_approvals`, `list_recent_traces`, `list_recent_plans`, `list_recent_governance_decisions`, `get_governance_state` |
| Recent traces | `GET /control-plane/traces` | `services.core.list_recent_traces(...)` |
| Trace detail | `GET /control-plane/traces/{trace_id}` | `services.core.get_trace(trace_id)` |
| Explainability detail | `GET /control-plane/traces/{trace_id}/explainability` | `services.core.get_explainability(trace_id)` |
| Pending approvals | `GET /control-plane/approvals` | `services.core.list_pending_approvals()` |
| Approve paused step | `POST /control-plane/approvals/{approval_id}/approve` | `services.core.approve_plan_step(...)` |
| Reject paused step | `POST /control-plane/approvals/{approval_id}/reject` | `services.core.reject_plan_step(...)` |
| Recent plan runs | `GET /control-plane/plans` | `services.core.list_recent_plans(...)` |
| Run plan | `POST /control-plane/plans/run` | `services.core.run_task_plan(...)` |
| Run task | `POST /control-plane/tasks/run` | `services.core.run_task(...)` |
| Governance feed | `GET /control-plane/governance` | `services.core.list_recent_governance_decisions(...)` |
| Agent capability view | `GET /control-plane/agents` | `services.core.list_agent_catalog()` |

## Minimal New Core Read Models Added In Phase M

### `services.core.list_recent_plans`

- Derived from canonical trace and approval data.
- Purpose: expose recent plan executions without introducing a second orchestration runtime.

### `services.core.list_recent_governance_decisions`

- Derived from canonical traces and explainability records.
- Purpose: expose recent allow/deny/require_approval outcomes without re-implementing policy logic.

### `services.core.list_agent_catalog`

- Projects the existing agent listing into a control-plane-friendly shape.
- Keeps incomplete metadata explicit rather than fabricating a second descriptor truth.

### `services.core.get_governance_state`

- Exposes lightweight governance configuration metadata for inspection.

## What The UI Does Not Call

- No direct adapter APIs
- No direct execution registry APIs
- No direct audit-store access from the frontend
- No direct orchestration internals
- No direct MCP runtime endpoints

## Rationale

This mapping keeps the browser-facing surface thin and the business logic in the core. The gateway only normalizes transport and aggregates read-only views where that is necessary for operator usability.
