# §6.5 Green AI — `abrain.list_routing_models` MCP tool

**Branch:** `codex/phase_green_routing_mcp_surface`
**Date:** 2026-04-19
**Scope:** Exposes the read-only routing-model catalog as an MCP v2
tool `abrain.list_routing_models`, completing the three-surface
parity (CLI / HTTP / MCP) for catalog introspection.  Thin delegate
of `services.core.get_routing_models` — no new catalog path, no
second payload shape.

---

## 1. Roadmap position

Eighth turn of the §6.5 Green-AI track; third observability-surface
turn after CLI (Turn 16) and HTTP (Turn 17):

| Turn | Commit | Surface |
|---|---|---|
| Turn 15 | `f73948fe` | Per-decision energy signal (descriptor / dispatcher / auditor) |
| Turn 16 | `64e175b8` | CLI column on `abrain routing models` |
| Turn 17 | `38026e94` | HTTP endpoint `/control-plane/routing/models` |
| **Turn 18 (this turn)** | — | MCP tool `abrain.list_routing_models` |

The routing catalog is now queryable through every canonical
operator/caller surface with identical payload shape.

---

## 2. Idempotency check

- `grep 'routing\|list_routing' interfaces/mcp/` before this turn —
  zero hits.
- No pre-existing MCP tool exposes the routing catalog.
- `TOOLS` registry contained seven entries; the allow-list test
  `test_tools_list_contains_only_static_v2_tools` pinned that
  count — a deliberate guard we extend, not bypass.
- No parallel branch.

Consequence: fully additive.  One new handler module, three
one-line edits to the registry plumbing, one extension to the
existing tool-list allow-list.

---

## 3. Design (as-built)

### 3.1 Handler

`interfaces/mcp/handlers/routing.py`:

```python
class ListRoutingModelsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: str | None = Field(default=None, max_length=64)
    provider: str | None = Field(default=None, max_length=64)
    purpose: str | None = Field(default=None, max_length=64)
    available_only: bool = Field(default=False)

    @field_validator("tier", "provider", "purpose")
    @classmethod
    def normalize_filter(cls, value): ...  # strip + empty→None


class ListRoutingModelsHandler:
    name = "abrain.list_routing_models"
    description = ("List the canonical ABrain routing-model catalog "
                   "with quantization, distillation and energy_profile "
                   "metadata. Read-only; accepts optional tier / "
                   "provider / purpose / available_only filters.")
    input_model = ListRoutingModelsParams

    def handle(self, params):
        from services.core import get_routing_models
        request = self.input_model.model_validate(params)
        payload = get_routing_models(
            tier=request.tier,
            provider=request.provider,
            purpose=request.purpose,
            available_only=request.available_only,
        )
        if "error" in payload:
            return {"status": "error",
                    "error": payload["error"],
                    "detail": payload.get("detail")}
        return {"status": "success", **payload}
```

- **Name:** `abrain.list_routing_models` — matches the `abrain.<verb>`
  convention used by every other MCP tool.
- **Strict input schema:** `ConfigDict(extra="forbid")` plus
  per-field normalization (`" "` / `""` → `None`) so callers
  can hand through optional args uniformly.  Unknown argument
  keys fail as JSON-RPC -32602 at the server boundary — already
  tested.
- **Error envelope translation:** the service's
  `{"error": "invalid_<x>", "detail": "..."}` response for bad
  enum values becomes `{"status": "error", ...}`.  The MCP server
  flips `isError=true` when `structuredContent["status"] ==
  "error"` — same convention used by `RunTaskHandler` for
  `status == "error"` branches.
- **Happy path:** `{"status": "success", **payload}` — keeps the
  service's full dict shape intact (total, catalog_size, filters,
  tiers, providers, purposes, models) so callers can branch on
  either `status` or `isError`.

### 3.2 Registry plumbing

Three one-line edits:

- `interfaces/mcp/handlers/__init__.py` — `+ import
  ListRoutingModelsHandler` + `__all__` entry.
- `interfaces/mcp/tool_registry.py` — `+ import
  ListRoutingModelsHandler` + one `TOOLS` entry using the
  existing `ExposedTool(...)` pattern verbatim.

No server.py change: `MCPV2Server._handle_tools_call` already
routes through `TOOLS[name].handler.handle(arguments)` for every
registered tool.

### 3.3 Non-changes

- `services/core.py`, `core/routing/`, `api_gateway/`,
  `scripts/abrain_control.py` — untouched.  MCP surface is a pure
  additive mirror.
- Server-side protocol (`MCPV2Server.handle_message`) — unchanged.
- No new scope / auth layer — MCP tools already run unauthenticated
  on the local stdio socket; the catalog is already read-only.
- No new dependency — pydantic is already the baseline.

---

## 4. Public-surface effect

**Additive, opt-in MCP tool.**  Existing tools unchanged; existing
tool-list ordering unchanged (new tool appended).

AI-tool caller example:

```
→ tools/call name="abrain.list_routing_models" arguments={"tier": "local"}
← result.structuredContent = {
    "status": "success",
    "total": 3, "catalog_size": 10,
    "filters": {"tier": "local", "provider": null, ...},
    "tiers": {"local": 3, ...},
    "models": [{"model_id": "llama-3.2-1b-local",
                "quantization": {"method": "gguf_q4_k_m", ...},
                "distillation": null,
                "energy_profile": null}, ...]
  }
  result.isError = false

→ tools/call name="abrain.list_routing_models" arguments={"tier": "xxl"}
← result.structuredContent = {"status": "error", "error": "invalid_tier",
                              "detail": "Unknown tier 'xxl'..."}
  result.isError = true
```

Live stdio smoke (`scripts/abrain_mcp.py` with
`tier=local`): `total=3 catalog=10 isError=False` — matches HTTP /
CLI output exactly.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Single MCP surface (`interfaces/mcp/`) | ✅ — tool added here; no second MCP path |
| `services/core.py` is sole catalog reader | ✅ — handler delegates verbatim |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only tool, no pipeline change |
| No business logic in MCP layer | ✅ — handler normalises empty strings and forwards error envelope; everything else is service |
| No new runtime / store / heavy dependency | ✅ — stdlib + existing pydantic |
| Stable-schema emission preserved | ✅ — service payload returned verbatim |
| `None`-signal honesty rule preserved | ✅ — `quantization` / `distillation` / `energy_profile` all `None`-able |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` sole truths | ✅ — none touched |
| CLI + HTTP + MCP share one catalog projection | ✅ — all three call `get_routing_models` |
| Tool-list allow-list guard updated | ✅ — pinned to new 8-entry list |
| Strict input schema (`additionalProperties: false`) | ✅ — inherited from `extra="forbid"` + server-side schema post-processing |

---

## 6. Artifacts

| File | Change |
|---|---|
| `interfaces/mcp/handlers/routing.py` | new — `ListRoutingModelsParams` + `ListRoutingModelsHandler` |
| `interfaces/mcp/handlers/__init__.py` | +import + `__all__` entry |
| `interfaces/mcp/tool_registry.py` | +import + `TOOLS` entry |
| `tests/mcp/test_routing_models_tool.py` | new — 9 tests across three classes |
| `tests/mcp/test_run_task_tool.py` | allow-list assertion extended to 8 tools |
| `docs/reviews/phase_green_routing_mcp_surface_review.md` | this doc |

No descriptor change, no dispatcher change, no auditor change, no
service change, no HTTP change, no CLI change, no catalog change.

---

## 7. Test coverage

Nine new tests in `tests/mcp/test_routing_models_tool.py`:

- **`TestToolRegistration` (2)** — tool shows up in `tools/list`;
  input schema documents all four filter keys with
  `additionalProperties: false`.
- **`TestToolCall` (6)** —
  1. Service delegation (mocked): default filters, full payload
     flow-through, `energy_profile` + lineage presence, `isError` =
     false.
  2. Filter forwarding: all four args arrive at the service call.
  3. Empty-string / whitespace-only filters normalise to `None`.
  4. Service error envelope flips `isError` to true and surfaces
     the detail.
  5. Unknown argument → JSON-RPC -32602.
  6. `content[0].text` mirrors `structuredContent` (server
     contract).
- **`TestRealCatalogSmoke` (1)** — end-to-end against the real
  `DEFAULT_MODELS` catalog; asserts stable-schema keys on every
  entry plus the `energy_profile=None` honesty-rule regression
  guard.

Plus: existing `tests/mcp/test_run_task_tool.py` allow-list
extended to pin the new 8-entry ordering.

---

## 8. Test gates

- Focused: `tests/mcp/test_routing_models_tool.py` — **9 passed**.
- Full suite (`tests/` with `test_*.py`): **1931 passed, 1 skipped**
  (+9 from Turn 17 baseline of 1922).
- `py_compile interfaces/mcp/handlers/routing.py
  interfaces/mcp/handlers/__init__.py interfaces/mcp/tool_registry.py`
  — clean.
- MCP stdio smoke: two JSON-RPC calls piped through
  `scripts/abrain_mcp.py` return
  `total=3 catalog=10 isError=False` for `tier=local` — matches
  the HTTP + CLI output against the same real catalog.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (MCP mirror of `get_routing_models`) | ✅ |
| Idempotency rule honoured (no duplicate tool / schema) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical MCP + service paths reinforced | ✅ |
| No business logic in MCP handler | ✅ |
| No Schatten-Wahrheit (handler reads service; service reads catalog) | ✅ |
| `None`-signal honesty rule preserved | ✅ |
| Stable-schema emission preserved | ✅ |
| Error envelope translation clean (flips `isError`) | ✅ |
| Tool-list allow-list guard updated | ✅ |
| Strict input schema | ✅ |
| MCP suite green (+9) | ✅ |
| Full suite green (+9) | ✅ |
| Documentation consistent with prior §6.5 + §263 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

The §6.5 Green-AI track now has symmetric catalog observability
across every canonical surface:

| Surface | Turn | Catalog | Lineage | Energy |
|---|---|---|---|---|
| Auditor span | Turn 15 | — | ✅ | ✅ |
| CLI (`abrain routing models`) | Turn 7 / 16 | ✅ | ✅ | ✅ |
| HTTP (`/control-plane/routing/models`) | Turn 17 | ✅ | ✅ | ✅ |
| MCP (`abrain.list_routing_models`) | **Turn 18** | ✅ | ✅ | ✅ |

Every in-session code lever for §6.5 observability is now pulled.

Candidates remaining, none urgent:

1. **UI parity** — `frontend/agent-ui` could render the routing
   catalog.  This is a frontend-only addition; the backend is
   complete.  In-session feasibility depends on whether the UI
   project's build infrastructure is available.
2. **Operator-side:** shadow-mode real-traffic run of Brain-v1 via
   `BrainOperationsReporter` — unblocks Phase 6 E1/E3 + Phase 7.
   Cannot land in-session.
3. **Operator-side:** real quant/distill-Benchmarks →
   `quality_delta_*` registration.  Closes §Phase 4 §263 + §6.5
   line 428 Eval-Ausführung.  Cannot land in-session.

Recommendation: stop here and surface the session state, or
attempt option 1 if the frontend build environment is accessible.

No immediate code blockers on `main`.
