# ABrain API Usage

## Purpose

The canonical external HTTP surface of ABrain is the existing `api_gateway`.
The public developer-facing routes are the `/control-plane/*` endpoints exposed
by `api_gateway/main.py`.

Use this surface when you want:

- browser-visible API docs via Swagger or ReDoc
- typed JSON requests and responses
- service-to-service integration over HTTP
- traceable task, plan and approval flows without importing internal modules

## Start The Gateway

```bash
./scripts/abrain setup
.venv/bin/python -m uvicorn api_gateway.main:app --reload
```

Developer docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Supported External Endpoints

| Area | Method | Path | Canonical core mapping |
| --- | --- | --- | --- |
| Control Plane | `GET` | `/control-plane/overview` | `services.core.get_control_plane_overview(...)` |
| Agents | `GET` | `/control-plane/agents` | `services.core.list_agent_catalog()` |
| Traces | `GET` | `/control-plane/traces` | `services.core.list_recent_traces(...)` |
| Traces | `GET` | `/control-plane/traces/{trace_id}` | `services.core.get_trace(trace_id)` |
| Traces | `GET` | `/control-plane/traces/{trace_id}/explainability` | `services.core.get_explainability(trace_id)` |
| Control Plane | `GET` | `/control-plane/governance` | `services.core.list_recent_governance_decisions(...)` |
| Approvals | `GET` | `/control-plane/approvals` | `services.core.list_pending_approvals()` |
| Approvals | `POST` | `/control-plane/approvals/{approval_id}/approve` | `services.core.approve_plan_step(...)` |
| Approvals | `POST` | `/control-plane/approvals/{approval_id}/reject` | `services.core.reject_plan_step(...)` |
| Plans | `GET` | `/control-plane/plans` | `services.core.list_recent_plans(...)` |
| Tasks | `POST` | `/control-plane/tasks/run` | `services.core.run_task(...)` |
| Plans | `POST` | `/control-plane/plans/run` | `services.core.run_task_plan(...)` |

These are the externally supported HTTP routes for developer control-plane
integration. Other gateway routes may still exist for runtime compatibility or
internal experiments, but they are intentionally not part of the public
OpenAPI surface.

## Examples

### Overview

```bash
curl http://localhost:8000/control-plane/overview
```

### Run One Task

```bash
curl -X POST http://localhost:8000/control-plane/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "system_status",
    "description": "Check system health",
    "input_data": {},
    "options": {
      "timeout": 5
    }
  }'
```

### Run One Plan

```bash
curl -X POST http://localhost:8000/control-plane/plans/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "workflow_automation",
    "description": "Trigger controlled workflow execution"
  }'
```

### Inspect Traces

```bash
curl http://localhost:8000/control-plane/traces?limit=5
curl http://localhost:8000/control-plane/traces/trace-123
curl http://localhost:8000/control-plane/traces/trace-123/explainability
```

### Work With Approvals

```bash
curl http://localhost:8000/control-plane/approvals

curl -X POST http://localhost:8000/control-plane/approvals/approval-123/approve \
  -H "Content-Type: application/json" \
  -d '{
    "decided_by": "developer@example",
    "comment": "Approved after review",
    "rating": 0.9
  }'
```

## API vs MCP vs CLI

Use HTTP API when:

- you want OpenAPI, Swagger and browser-visible docs
- you are integrating from another service
- you want typed JSON request and response contracts

Use MCP when:

- you need a small tool surface for AI or editor integration
- you want JSON-RPC over stdio rather than HTTP
- you want the narrow MCP tool contract documented in `docs/guides/MCP_USAGE.md`

Use CLI when:

- you are operating a local checkout
- you want fast developer or operator commands such as `task run`, `plan run`,
  `approval list`, `trace show` or `health`
- you prefer human-oriented output with optional `--json`

## What S6 Does Not Add

- no second API
- no second OpenAPI generator
- no HTTP replacement for MCP
- no new runtime or proxy layer

The gateway remains a thin transport and documentation layer over the canonical
core.
