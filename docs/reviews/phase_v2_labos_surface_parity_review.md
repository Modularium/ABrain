# Phase V2 — LabOS Domain-Reasoning Surface Parity (CLI + HTTP + MCP)

**Branch:** `codex/phase_v2_labos_surface_parity`
**Date:** 2026-04-20
**Scope:** Exposes the five LabOS domain-reasoning use cases already
implemented in `core/reasoning/labos/usecases.py` on all three
canonical ABrain surfaces — CLI, HTTP and MCP — as pure delegates
of a single `services.core` dispatcher.  No new reasoning logic;
identical Response Shape V2 across surfaces; symmetric error
envelope translation.

---

## 1. Roadmap position

Follow-up to the V1 commit `878fce39` that introduced the reasoner
under `core/reasoning/labos/` and the per-use-case entry points
`services.core.get_labos_<mode>(context)`.

| Turn | Commit | Surface |
|---|---|---|
| V1 | `878fce39` | `core/reasoning/labos/*` + `get_labos_<mode>` entry points |
| **V2 (this turn)** | — | CLI + HTTP + MCP surfaces over one shared dispatcher |

After this turn every LabOS use case is reachable from every
canonical caller surface with the same payload shape.

---

## 2. Idempotency check

Pre-turn survey:

- `grep 'reasoning.*labos\|reason_labos' scripts/ api_gateway/ interfaces/mcp/`
  → zero hits.  No pre-existing surface exposed the LabOS
  reasoner.
- No parallel dispatcher in `api_gateway/`, `scripts/`,
  `interfaces/mcp/` — the five V1 entry points live exclusively in
  `services/core.py`.
- `TOOLS` registry contained eight entries; the allow-list test
  `test_tools_list_contains_only_static_v2_tools` pinned that
  count — a deliberate guard we extend, not bypass.

Consequence: fully additive.  One public dispatcher in
`services/core.py`, one surface-shaped wrapper per layer, zero new
reasoning paths.

---

## 3. Design (as-built)

### 3.1 Shared dispatcher (`services/core.py`)

The V1 core already exported five typed entry points
(`get_labos_reactor_daily_overview`, `get_labos_incident_review`,
…) plus a private `_run_labos_reasoner(mode, context)` used by the
HTTP fallback in `_run_labos_reasoning_mode`.  V2 promotes two
things to public surface:

```python
LABOS_REASONING_MODES: tuple[str, ...] = (
    "reactor_daily_overview",
    "incident_review",
    "maintenance_suggestions",
    "schedule_runtime_review",
    "cross_domain_overview",
)
_LABOS_REASONING_MODES = LABOS_REASONING_MODES  # back-compat alias

def run_labos_reasoning(mode: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Public mode-based dispatcher used by every ABrain surface."""
    return _run_labos_reasoner(mode, context)
```

This is the **single** entry point every surface uses.  No surface
maps from a string mode to a typed `get_labos_<mode>` function on
its own — that would be a parallel dispatcher.  The typed entry
points remain for in-process Python callers that prefer them.

### 3.2 CLI (`scripts/abrain` + `scripts/abrain_control.py`)

- `scripts/abrain` — gained one `cmd_reasoning` bridge +
  `reasoning)` dispatch + one help line.  No logic.
- `scripts/abrain_control.py`:
  - `reasoning` subparser with a single `labos` child.
  - `labos` takes `mode` (argparse `choices=list(LABOS_REASONING_MODES)` —
    unknown mode fails with argparse exit 2 before we ever call
    the service).
  - Context source is one of `--input PATH` / `--input-json STR` /
    `--stdin`.  A helper `_read_reasoning_context` enforces
    mutual exclusivity via `CliUsageError` (exit 2, service is
    never called).
  - Validates that the parsed JSON is a dict (rejects `[1,2,3]`
    with exit 2).
  - `--json` emits `json.dumps(payload, indent=2)`; otherwise a
    compact text renderer `_render_labos_reasoning` shows the
    mode, summary, top-10 prioritised entities and counts for the
    three action lists.
  - Error envelope → exit code `1` with the error message
    rendered in either JSON or text mode.

### 3.3 HTTP (`api_gateway/schemas.py` + `api_gateway/main.py`)

- `LabOsReasoningRequest` pydantic model — strict
  (`ConfigDict(extra="forbid")`), `context: dict[str, Any]`
  (default empty dict).  `extra="forbid"` turns stray keys into
  422 before routing.
- New OpenAPI tag `Reasoning`.
- `_register_labos_reasoning_endpoint(mode, summary)` factory
  closes over `mode` and registers one `POST
  /control-plane/reasoning/labos/{mode}` per entry in
  `_LABOS_REASONING_ENDPOINT_SUMMARIES`.  Each handler is a
  closure that:
  1. Applies `check_scope(request, "agents:read")` — read-only
     reasoning, no mutations.
  2. Calls `services.core.run_labos_reasoning(mode, payload.context)`
     (imported lazily so tests can `monkeypatch.setattr`
     `services.core.run_labos_reasoning`).
  3. Translates the error envelope to `HTTPException(status_code=400, ...)`.
  4. Returns the Response Shape V2 payload verbatim otherwise.
- `__name__` is patched per-mode so FastAPI assigns distinct
  operation IDs.

### 3.4 MCP (`interfaces/mcp/handlers/reasoning.py`)

- `LabOsReasoningParams` pydantic model with
  `ConfigDict(extra="forbid")` + single `context` field.
- `_LabOsReasoningHandlerBase` implements the shared `handle()`:

  ```python
  def handle(self, params):
      from services.core import run_labos_reasoning
      request = self.input_model.model_validate(params)
      payload = run_labos_reasoning(self.mode, request.context)
      if "error" in payload:
          return {"status": "error",
                  "error": payload["error"],
                  "detail": payload.get("detail")}
      return {"status": "success", **payload}
  ```

- `_make_handler_class(mode)` uses `type()` to create five
  concrete subclasses — `ReasonLabosReactorDailyOverviewHandler`,
  `ReasonLabosIncidentReviewHandler`, … — each pinning
  `name = f"abrain.reason_labos_{mode}"` and a
  per-mode `description`.
- `LABOS_REASONING_HANDLERS` is a tuple of all five classes;
  `interfaces/mcp/tool_registry.py` iterates it with a dict
  comprehension into `TOOLS`.
- Server plumbing (`MCPV2Server._handle_tools_call`) already
  routes through `TOOLS[name].handler.handle(arguments)` — no
  server change.

### 3.5 Non-changes

- `core/reasoning/labos/` — untouched.  No reasoner change.
- `services/core.py` — only the public dispatcher + the exported
  `LABOS_REASONING_MODES` constant.  All V1 typed entry points
  retained.
- Governance / approval / execution / audit pipeline — untouched.
  The reasoner remains read-only; actions it recommends are not
  executed by the surfaces.

---

## 4. Public-surface effect

**Additive, opt-in surfaces.**  Existing CLI subcommands,
existing HTTP paths and existing MCP tools are all unchanged.

### CLI

```bash
./scripts/abrain reasoning labos reactor_daily_overview --input ctx.json --json
cat ctx.json | ./scripts/abrain reasoning labos incident_review --stdin
./scripts/abrain reasoning labos maintenance_suggestions --input-json '{"maintenance_items":[]}'
```

### HTTP

```
POST /control-plane/reasoning/labos/reactor_daily_overview
POST /control-plane/reasoning/labos/incident_review
POST /control-plane/reasoning/labos/maintenance_suggestions
POST /control-plane/reasoning/labos/schedule_runtime_review
POST /control-plane/reasoning/labos/cross_domain_overview
```

All accept `{"context": {...}}` with `extra="forbid"`.
`scope=agents:read`.  Response Shape V2 body on 200; 400 on
invalid context; 422 on unknown request keys.

### MCP

```
abrain.reason_labos_reactor_daily_overview
abrain.reason_labos_incident_review
abrain.reason_labos_maintenance_suggestions
abrain.reason_labos_schedule_runtime_review
abrain.reason_labos_cross_domain_overview
```

Strict input schema (`additionalProperties: false`), single
`context` argument.  `isError=false` on success, `isError=true`
when the service returns `{"error": ...}`.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Single reasoning core (`core/reasoning/labos/`) | ✅ — untouched; surfaces delegate only |
| `services/core.py` is sole reasoning entry point | ✅ — `run_labos_reasoning` is the one dispatcher |
| Response Shape V2 keyed identically across surfaces | ✅ — payload forwarded verbatim by all three |
| Error envelope translation symmetric | ✅ — CLI exit 1, HTTP 400, MCP `isError=true` |
| No business logic in surfaces | ✅ — CLI reads input; HTTP does scope+delegate; MCP validates+delegate |
| Strict input schemas | ✅ — argparse `choices` + pydantic `extra="forbid"` × 2 |
| No shadow dispatchers | ✅ — no surface maps mode→typed entry on its own |
| Tool-list allow-list guard extended | ✅ — from 8 to 13 entries |
| `no_invented_actions` / `respects_approval` / `respects_safety_context` | ✅ — enforced in the reasoner, unchanged |
| CLI + HTTP + MCP share one payload projection | ✅ — same `run_labos_reasoning` |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +`LABOS_REASONING_MODES`, +`run_labos_reasoning(mode, ctx)` dispatcher |
| `scripts/abrain` | +`cmd_reasoning` bridge, +`reasoning)` dispatch, +help line |
| `scripts/abrain_control.py` | +`reasoning labos <mode>` subparser, `_read_reasoning_context`, `_render_labos_reasoning`, `_handle_reasoning_labos` |
| `api_gateway/schemas.py` | +`Reasoning` OpenAPI tag, +`LabOsReasoningRequest` |
| `api_gateway/main.py` | +`_LABOS_REASONING_ENDPOINT_SUMMARIES`, +`_register_labos_reasoning_endpoint` factory, +5 endpoint registrations |
| `interfaces/mcp/handlers/reasoning.py` | new — `LabOsReasoningParams`, `_LabOsReasoningHandlerBase`, `_make_handler_class`, 5 concrete classes, `LABOS_REASONING_HANDLERS` |
| `interfaces/mcp/handlers/__init__.py` | +imports + `__all__` entries for 5 new handlers |
| `interfaces/mcp/tool_registry.py` | +dict-comprehension append of the 5 new handlers |
| `tests/reasoning/labos/test_surface_cli.py` | new — 13 tests |
| `tests/reasoning/labos/test_surface_http.py` | new — 9 tests |
| `tests/mcp/test_reasoning_labos_tool.py` | new — 10 tests |
| `tests/mcp/test_run_task_tool.py` | allow-list extended to 13 entries (pinned ordering) |
| `README.md` | surface section under §🧠 ABrain V2 |
| `docs/reviews/phase_v2_labos_surface_parity_review.md` | this doc |

No reasoner change, no governance change, no store change.

---

## 7. Test coverage

New (+32):

- **`tests/reasoning/labos/test_surface_cli.py` (13)**
  - `TestCliDelegation` (7): parametrized service delegation over
    five modes, `--input-json`, `--stdin`.
  - `TestCliOutput` (6): JSON emission parses, text renderer
    shows mode+summary+top entity, invalid context → exit 1,
    unknown mode → argparse exit 2, multiple inputs → exit 2
    (service not called), non-object JSON → exit 2.

- **`tests/reasoning/labos/test_surface_http.py` (9)**
  - `TestHttpRouting` (7): OpenAPI registers all 5 paths with
    `Reasoning` tag; parametrized delegation over 5 modes;
    invalid context → 400; `extra="forbid"` → 422.
  - `TestHttpRealService` (1): real-service smoke returns every
    Response Shape V2 key.

- **`tests/mcp/test_reasoning_labos_tool.py` (10)**
  - `TestToolRegistration` (2): all 5 tools registered; input
    schemas are strict objects.
  - `TestToolCall` (7): parametrized delegation over 5 modes;
    error envelope → `isError=true`; unknown argument →
    JSON-RPC -32602.
  - `TestRealServiceSmoke` (1): end-to-end against the real
    reasoner surfaces every Response Shape V2 key.

Plus: `tests/mcp/test_run_task_tool.py` allow-list assertion
extended to pin the new 13-entry `tools/list` ordering.

---

## 8. Test gates

- Focused (`tests/reasoning/labos/ tests/mcp/test_reasoning_labos_tool.py tests/mcp/test_run_task_tool.py`) — **36 passed**.
- Full suite — see §9.

Commands:

```bash
.venv/bin/python -m pytest \
    -o python_files='test_*.py' \
    tests/reasoning/labos/ \
    tests/mcp/test_reasoning_labos_tool.py \
    tests/mcp/test_run_task_tool.py -q

.venv/bin/python -m pytest -o python_files='test_*.py' tests/ -q
```

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (surface parity over V1 reasoner) | ✅ |
| Idempotency rule honoured (no duplicate dispatcher) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical surface + service paths reinforced | ✅ |
| No business logic in surface layers | ✅ |
| No Schatten-Wahrheit (surfaces read dispatcher; dispatcher reads reasoner) | ✅ |
| Response Shape V2 identical across surfaces | ✅ |
| Error envelope translation symmetric | ✅ |
| Tool-list allow-list guard updated | ✅ |
| Strict input schemas everywhere | ✅ |
| Focused suite green (+36) | ✅ |
| Documentation consistent with §V1 + §6.5 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

The LabOS reasoner is now symmetric across CLI, HTTP and MCP.
Possible follow-ups, none urgent:

1. **UI parity** — `frontend/agent-ui` could render the five
   reasoning outputs.  Purely additive; blocked only on whether
   the UI project's build pipeline is available in-session.
2. **Real Smolit-AI-Assistant integration** — wire the
   assistant's LabOS dossier pipeline to call one of the MCP
   tools.  This is a cross-repo change; ABrain side is complete.
3. **Second external system** — duplicate the reasoning+surface
   scaffold for a non-LabOS target to prove the abstraction
   really does generalise.  Optional; waits on a real
   second-system input schema.

No immediate code blockers.
