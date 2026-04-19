# §6.5 Green AI — `/control-plane/routing/models` HTTP surface

**Branch:** `codex/phase_green_routing_http_surface`
**Date:** 2026-04-19
**Scope:** Extends the canonical `api_gateway` control-plane surface
with a read-only `GET /control-plane/routing/models` endpoint that
mirrors the `abrain routing models` CLI (Turn 7 / Turn 16) so
browser-facing dashboards and service-to-service integrations can
consume the routing-model catalog — including quantization /
distillation lineage and per-model energy profile — without bypassing
`services/core.py`.

---

## 1. Roadmap position

Seventh turn of the §6.5 Green-AI track and the first HTTP-surface
turn.  Completes the read-only observability triangle established by
the prior two turns:

| Turn | Commit | Surface |
|---|---|---|
| Turn 15 | `f73948fe` | Per-decision energy signal (descriptor / dispatcher / auditor) |
| Turn 16 | `64e175b8` | CLI column on `abrain routing models` |
| **Turn 17 (this turn)** | — | HTTP endpoint `/control-plane/routing/models` |

The CLI and HTTP surfaces now share the single `get_routing_models`
reader — no second catalog projection, no divergent payload shape.

---

## 2. Idempotency check

- `grep 'routing/models\|RoutingModels' api_gateway/` before this
  turn — zero hits.
- No pre-existing HTTP endpoint exposes the routing catalog.
- `services.core.get_routing_models` was already the sole reader
  (landed Turn 7, extended with `energy_profile` in Turn 16).
  Nothing else needs to change service-side.
- No parallel branch.

Consequence: fully additive — one new endpoint, one new response
schema (+ four nested entry schemas), five new tests, one new
OpenAPI tag.

---

## 3. Design (as-built)

### 3.1 Endpoint

`api_gateway/main.py`:

```python
@app.get(
    "/control-plane/routing/models",
    response_model=RoutingModelsResponse,
    tags=["Routing"],
    ...
)
async def control_plane_routing_models(
    request: Request,
    tier: str | None = Query(default=None, ...),
    provider: str | None = Query(default=None, ...),
    purpose: str | None = Query(default=None, ...),
    available_only: bool = Query(default=False, ...),
) -> dict:
    check_scope(request, "agents:read")
    from services.core import get_routing_models
    payload = get_routing_models(
        tier=tier, provider=provider, purpose=purpose,
        available_only=available_only,
    )
    if "error" in payload:
        raise HTTPException(status_code=400, detail=payload.get("detail") or payload["error"])
    return payload
```

- **Scope:** `agents:read` — same read-scope already used by the
  other `/control-plane/*` catalog reads (agents, traces,
  governance, plans).  No new permission category.
- **Method/path:** `GET /control-plane/routing/models` — aligned
  with the `/control-plane/<resource>` naming already in use.
- **Filters:** exactly the four query params accepted by the
  canonical reader (`tier`, `provider`, `purpose`,
  `available_only`).  No gateway-side filter logic.
- **Error mapping:** the service returns
  `{"error": "invalid_<x>", "detail": "..."}` for bad enum values
  (already existing behaviour).  Gateway translates to HTTP 400 so
  typos surface as a caller error rather than a 200 with an error
  blob — keeps the REST contract clean.
- **No response post-processing:** `return payload` as-is.  The
  service's payload is already the stable catalog shape.

### 3.2 Response schema

`api_gateway/schemas.py` adds five pydantic models under
`ConfigDict(extra="forbid")`:

| Schema | Maps to |
|---|---|
| `RoutingQuantizationEntry` | `services.core.get_routing_models` `quantization` dict |
| `RoutingDistillationEntry` | `services.core.get_routing_models` `distillation` dict |
| `RoutingEnergyProfileEntry` | `services.core.get_routing_models` `energy_profile` dict |
| `RoutingModelEntry` | one element of `payload["models"]` |
| `RoutingModelsResponse` | whole payload envelope |

Every nested schema uses the "always emit, null when absent"
convention — mirrors the auditor-span schema and the CLI output.
`RoutingEnergyProfileEntry.source` is `str` (not a Python `Literal`)
because OpenAPI tooling renders enums more ergonomically when the
service already serialises to a plain string; the canonical
literal stays enforced on the service side
(`core.decision.energy_report.ProfileSource`).

### 3.3 New OpenAPI tag

Single added tag entry:

```python
{
    "name": "Routing",
    "description": "Read-only inspection of the canonical routing-model catalog with lineage and energy metadata.",
}
```

Separates the catalog read from the general Control-Plane tag, so
Swagger UI groups routing introspection next to Agents / Traces.

### 3.4 Non-changes

- `services/core.py`, `core/routing/`, `scripts/abrain_control.py` —
  untouched.  HTTP surface is a pure additive mirror.
- No new dispatch, no new audit hook, no new descriptor field.
- No change to existing `/control-plane/*` endpoints, scopes or
  schemas.
- No new external dependency — FastAPI / pydantic / httpx already
  in the stack.

---

## 4. Public-surface effect

**Additive, opt-in endpoint.**  Existing endpoints unchanged;
existing OpenAPI schema unchanged except for five new component
entries and one new path.

Consumer example:

```
GET /control-plane/routing/models?tier=local&available_only=true
→ 200 {
  "total": 3, "catalog_size": 10,
  "filters": {"tier": "local", "provider": null, "purpose": null, "available_only": true},
  "tiers": {"local": 3, ...},
  "models": [
    {"model_id": "llama-3.2-1b-local",
     "tier": "local", "provider": "local",
     "quantization": {"method": "gguf_q4_k_m", "bits": 4, ...},
     "distillation": null,
     "energy_profile": null}, ...]
}

GET /control-plane/routing/models?tier=xxl
→ 400 {"detail": "Unknown tier 'xxl'. Valid: local, small, medium, large"}
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Single external HTTP surface (`api_gateway/main.py`) | ✅ — endpoint added here; no second gateway |
| `services/core.py` is sole reader | ✅ — endpoint delegates verbatim; no new catalog path |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only route, no pipeline change |
| No business logic in gateway | ✅ — gateway translates error envelope to HTTP 400, nothing else |
| No new runtime / store / heavy dependency | ✅ — stdlib + existing FastAPI |
| Stable-schema emission preserved | ✅ — schemas mirror the service dict 1:1, incl. null-emission |
| `None`-signal honesty rule preserved | ✅ — `quantization` / `distillation` / `energy_profile` all `None`-able |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` sole truths | ✅ — none touched |
| CLI + HTTP + (future) MCP share one catalog projection | ✅ — all three call `get_routing_models` |
| OpenAPI surface explicitly enumerated (gateway guard test) | ✅ — `/control-plane/routing/models` added to the allow-list |
| No auth-scope expansion | ✅ — reuses `agents:read` |

---

## 6. Artifacts

| File | Change |
|---|---|
| `api_gateway/main.py` | +import of `RoutingModelsResponse`, +`control_plane_routing_models` endpoint with four query filters + 400 error mapping |
| `api_gateway/schemas.py` | +"Routing" OpenAPI tag, +5 pydantic schemas (`RoutingQuantizationEntry`, `RoutingDistillationEntry`, `RoutingEnergyProfileEntry`, `RoutingModelEntry`, `RoutingModelsFilters`, `RoutingModelsResponse`) |
| `tests/core/test_api_gateway_openapi.py` | +allow-list assertion, +"Routing" tag assertion, +5 new tests (openapi-shape, mocked 200, forwarded filters, 400 on invalid enum, end-to-end real-catalog smoke) |
| `docs/reviews/phase_green_routing_http_surface_review.md` | this doc |

No CLI change, no service change, no descriptor change, no catalog
change.

---

## 7. Test coverage

Five new tests in `tests/core/test_api_gateway_openapi.py`:

1. `test_openapi_documents_routing_models_schema` — asserts the
   response `$ref` is `RoutingModelsResponse`, all five nested
   schemas are in `components.schemas`, all four query parameters
   are documented.
2. `test_routing_models_http_route_returns_documented_shape` —
   mocked `get_routing_models`; verifies the payload flows through
   1:1 including `energy_profile` (both populated and `null`).
3. `test_routing_models_http_route_forwards_filters` — verifies
   all four query params arrive at the service call verbatim
   (including `available_only=True` from string coercion).
4. `test_routing_models_http_route_surfaces_invalid_filter_as_400` —
   verifies the service's `{"error": ..., "detail": ...}` envelope
   becomes HTTP 400 with the detail message preserved.
5. `test_routing_models_http_route_returns_real_catalog` —
   end-to-end smoke against the real `DEFAULT_MODELS` catalog
   (no mock), asserts every entry carries the stable-schema
   lineage + energy keys and that DEFAULT_MODELS ships
   `energy_profile=None` (honesty-rule regression guard).

Plus: the existing
`test_openapi_exposes_only_canonical_control_plane_surface` allow-
list now pins `/control-plane/routing/models` and the `Routing`
tag — so a future deletion would trip the guard.

---

## 8. Test gates

- Focused: `tests/core/test_api_gateway_openapi.py` — **10 passed**
  (+5 new + 2 existing tests extended).
- Full suite (`tests/` with `test_*.py`): **1922 passed, 1 skipped**
  (+5 from Turn 16 baseline of 1917).
- `py_compile api_gateway/main.py api_gateway/schemas.py` — clean.
- CLI smoke: `bash scripts/abrain --version` → `ABrain CLI v1.0.0`
  (gateway changes do not touch CLI, but rule-G wants it run on any
  `scripts/` adjacent turn; no regression).
- OpenAPI schema live check embedded in tests (10/10 green,
  including `/openapi.json` round-trip).

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (HTTP mirror of `get_routing_models`) | ✅ |
| Idempotency rule honoured (no duplicate endpoint / schema) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical gateway + service paths reinforced | ✅ |
| No business logic in gateway | ✅ |
| No Schatten-Wahrheit (endpoint reads service; service reads catalog) | ✅ |
| `None`-signal honesty rule preserved | ✅ |
| Stable-schema emission preserved | ✅ |
| Auth-scope reused (no permission expansion) | ✅ |
| OpenAPI allow-list guard updated | ✅ |
| Gateway openapi test suite green (+5) | ✅ |
| Full suite green (+5) | ✅ |
| Documentation consistent with prior §6.5 + §263 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

The §6.5 Green-AI track now has symmetric observability across the
three canonical operator surfaces:

| Surface | Turn | Catalog | Lineage | Energy |
|---|---|---|---|---|
| Auditor span | Turn 15 | — | ✅ | ✅ |
| `abrain routing models` CLI | Turn 7 / 16 | ✅ | ✅ | ✅ |
| `/control-plane/routing/models` HTTP | **Turn 17** | ✅ | ✅ | ✅ |

Candidates remaining, none urgent:

1. **MCP surface parity** — expose the same catalog read through
   `interfaces/mcp/` so AI-tool callers can introspect routing
   too.  Likely tiny (one-tool addition) if wanted.
2. **Operator-side:** shadow-mode real-traffic run of Brain-v1 via
   `BrainOperationsReporter` — unblocks Phase 6 E1/E3 + Phase 7.
   Cannot land in-session.
3. **Operator-side:** real quant/distill-Benchmarks →
   `quality_delta_*` registration.  Closes §Phase 4 §263 + §6.5
   line 428 Eval-Ausführung.  Cannot land in-session.

Recommendation: option 1 if another code turn is warranted, or stop
here and surface the session state.  Every catalog-observability
lever is now pulled on the canonical surfaces.

No immediate code blockers on `main`.
