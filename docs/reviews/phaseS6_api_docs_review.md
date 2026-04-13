# Phase S6 API Docs Review

## 1. Which API Areas Were Sharpened

S6 sharpens the existing external HTTP surface in `api_gateway/main.py` without
adding a second API system.

The externally supported and documented route set is now the canonical
`/control-plane/*` family:

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

## 2. How Swagger / OpenAPI Can Now Be Used

The existing gateway now exposes a clean external developer surface through:

- `/docs`
- `/redoc`
- `/openapi.json`

Improvements:

- explicit API title, version and description
- stable OpenAPI tag groups:
  - Control Plane
  - Agents
  - Traces
  - Approvals
  - Plans
  - Tasks
- summaries and descriptions on the supported control-plane endpoints
- request and response schemas for the externally relevant routes
- path and query parameter descriptions for `trace_id`, `approval_id` and `limit`

Compatibility or experimental helper routes remain executable where needed, but
they are intentionally hidden from the public OpenAPI document.

## 3. Which Endpoints Are Deliberately Supported Externally

Externally supported over HTTP:

- control-plane inspection
- task and plan launch
- approval handling
- trace and explainability inspection
- projected agent visibility
- governance visibility

Deliberately not promoted as public API truth:

- chat helper routes
- session helper routes
- direct `/agents`
- `/llm/generate`
- `/embed`
- `/metrics`

Those routes are not the supported external developer contract for S6 and are
therefore omitted from Swagger/OpenAPI.

## 4. How API / MCP / CLI Are Separated

HTTP API:

- browser-visible documentation
- typed JSON request and response surface
- service-to-service integration
- canonical external HTTP contract

MCP:

- small JSON-RPC tool surface over stdio
- AI/editor integration path
- same canonical core, different transport

CLI:

- local developer and operator control path
- human-readable default output with optional `--json`
- same canonical core, optimized for local workflow speed

## 5. Explicit Architecture Confirmation

- no parallel structure was introduced
- no second API was introduced
- no legacy paths were reactivated
- `api_gateway` remains the only external HTTP truth
- only existing canonical core-backed routes were sharpened and documented

## Optional OpenAPI Export Decision

S6 does not add a separate OpenAPI export pipeline or generated spec artifact.
Reason:

- the live FastAPI schema at `/openapi.json` is already the canonical source
- a second export artifact would create another documentation truth to keep in
  sync
- the current value is in live route metadata quality, not in another generator
