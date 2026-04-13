# Phase S6 API Surface Inventory

## 1. Existing API Endpoints

The existing external HTTP surface lives in `api_gateway/main.py`. Before S6,
the file already exposed these route groups:

- compatibility and experimental helpers:
  - `POST /llm/generate`
  - `POST /chat`
  - `GET /chat/history/{sid}`
  - `POST /chat/feedback`
  - `POST /sessions`
  - `GET /sessions/{sid}/history`
  - `GET /agents`
  - `POST /embed`
- control-plane routes:
  - `GET /control-plane/overview`
  - `GET /control-plane/agents`
  - `GET /control-plane/traces`
  - `GET /control-plane/traces/{trace_id}`
  - `GET /control-plane/traces/{trace_id}/explainability`
  - `GET /control-plane/governance`
  - `GET /control-plane/approvals`
  - `POST /control-plane/approvals/{approval_id}/approve`
  - `POST /control-plane/approvals/{approval_id}/reject`
  - `GET /control-plane/plans`
  - `POST /control-plane/tasks/run`
  - `POST /control-plane/plans/run`
- operational helper:
  - `GET /metrics`

## 2. Today’s External Usage Possibilities

Before S6, an external developer could already:

- start the gateway via `uvicorn api_gateway.main:app`
- call control-plane HTTP routes directly with `curl`
- use the same canonical core through CLI or MCP

But the HTTP developer experience was still weak:

- FastAPI docs existed only with the default minimal setup
- the gateway title and description were generic
- the public surface was not clearly separated from experimental helper routes
- many routes returned anonymous `dict` payloads in OpenAPI
- query parameters and path parameters had little or no descriptive metadata

## 3. Inconsistencies And Gaps

### Public API truth was not visually explicit

- `api_gateway` already was the real HTTP entry point, but Swagger did not make
  it obvious which endpoints were externally supported.
- Compatibility routes and experimental routes could appear equivalent to the
  canonical control-plane routes.

### Request and response models were too anonymous

- `ControlPlaneRunRequest` and `ApprovalDecisionRequest` existed, but only as
  inline route models.
- control-plane responses were typed as `dict`, so OpenAPI could not show the
  actual response structure for traces, approvals, plans, governance or task
  execution.

### Missing outer-facing documentation

- README contained a single `curl` example but no browser-docs guidance.
- There was no dedicated API usage guide explaining:
  - which HTTP endpoints are supported
  - how they map to `services/core.py`
  - when HTTP API vs MCP vs CLI is the right interface

### Status codes and descriptions were under-documented

- routes did not consistently document authorization or upstream-service error
  responses
- summaries, tags and route descriptions were minimal or absent

## 4. Why `api_gateway` Remains The Only External HTTP Truth

S6 does not introduce:

- a second API service
- a second OpenAPI generator
- a proxy in front of the gateway
- a parallel debug HTTP stack

Instead, it sharpens the existing `api_gateway/main.py` routes so that:

- `/control-plane/*` is the documented, supported HTTP surface
- Swagger/ReDoc/OpenAPI reflect the real current code path
- request and response schemas point at canonical core-backed structures
- compatibility or experimental routes do not become a second public API truth
