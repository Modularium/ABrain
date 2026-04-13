# Phase S9 — Provider Abstraction & Execution Capability Surface

**Branch:** `codex/phaseS9-provider-abstraction-capability-surface`
**Date:** 2026-04-13
**Reviewer:** automated phase gate

---

## Goal

Formalize the execution capabilities of real adapters into a canonical, type-safe surface accessible from the agent catalog API, the CLI, and the frontend — with no new registry, no second adapter stack, and no parallel provider world.

---

## What changed

### New file — `core/execution/provider_capabilities.py`

Defines two things:

```python
ExecutionProtocol = Literal["cli_process", "http_api", "webhook_json", "tool_dispatch"]

class ExecutionCapabilities(BaseModel):
    execution_protocol: ExecutionProtocol
    requires_network: bool
    requires_local_process: bool
    supports_cost_reporting: bool
    supports_token_reporting: bool
    runtime_constraints: list[str]
```

This is the single source of truth for what an adapter's execution model looks like. It is a Pydantic model with `extra="forbid"` — no undocumented fields allowed.

### Adapters extended (class attribute pattern)

Each concrete adapter declares `capabilities` as a class attribute. The source of truth stays co-located with the adapter implementation:

| Adapter | Protocol | Network | Local process | Cost | Tokens | Constraints |
|---------|----------|---------|---------------|------|--------|-------------|
| `AdminBotExecutionAdapter` | `tool_dispatch` | No | No | No | No | `requires_adminbot_tools` |
| `OpenHandsExecutionAdapter` | `http_api` | Yes | No | Yes | No | `requires_service_endpoint` |
| `ClaudeCodeExecutionAdapter` | `cli_process` | No | Yes | Yes | Yes | `requires_claude_cli` |
| `CodexExecutionAdapter` | `cli_process` | No | Yes | Yes | Yes | `requires_codex_cli` |
| `FlowiseExecutionAdapter` | `http_api` | Yes | No | Yes | No | `requires_service_endpoint`, `requires_chatflow_id` |
| `N8NExecutionAdapter` | `webhook_json` | Yes | No | Yes | No | `requires_webhook_url` |
| `BaseExecutionAdapter` | `http_api` (safe default) | No | No | No | No | — |

### Registry extended — `get_capabilities_for()`

```python
def get_capabilities_for(self, execution_kind: str, source_type: str) -> ExecutionCapabilities | None:
```

Takes string values (enum `.value`) and returns the adapter's `capabilities` attribute, or `None` for unregistered pairs. Raises nothing.

### `core/execution/__init__.py`

`ExecutionCapabilities` added to `__all__` with lazy import so downstream importers get it from the canonical package.

### `api_gateway/schemas.py`

`AgentCatalogEntry` gains:

```python
execution_capabilities: ExecutionCapabilities | None = None
```

Serialised as a typed JSON object or `null` for agents without a registered adapter.

### `services/core.py` — `list_agent_catalog()`

Instantiates `ExecutionAdapterRegistry`, calls `get_capabilities_for(execution_kind, source_type)`, and includes `execution_capabilities` in every catalog entry dict. No IO — registry lookup is in-memory.

### `scripts/abrain_control.py`

`abrain agents` table gains a "protocol" column showing `cli_process[L]`, `http_api[N]`, etc. where `[N]` = requires network, `[L]` = requires local process.

### `frontend/agent-ui/src/services/controlPlane.ts`

`ExecutionCapabilities` TypeScript interface added; `ControlPlaneAgent` gains `execution_capabilities?: ExecutionCapabilities | null`.

---

## Architecture check

### No parallel implementation

There is no second capability registry, no second adapter list, no duplicate capability table. The capability is declared on the class and queried via the existing `ExecutionAdapterRegistry`. Removing the implementation leaves the system in exactly its previous state.

### No second adapter stack

`ExecutionAdapterRegistry._adapters` is unchanged. `get_capabilities_for()` is purely additive — it reads from the same instance dict that `resolve()` already uses.

### Single canonical surface

`core/execution/provider_capabilities.py` is the only definition of `ExecutionCapabilities`. All consumers import from this one location.

### No managers/ revival

Zero changes to `managers/`. All changes are inside `core/execution/`, `api_gateway/`, `services/`, `scripts/`, and `frontend/agent-ui/`.

### Value delivered

- Operators can see `execution_protocol`, `requires_network`, and `requires_local_process` per agent in the CLI agent table — useful for capacity planning and debugging deployment mismatches.
- The API now exposes this in `GET /control-plane/overview` and `GET /control-plane/agents` — visible in `/docs` and consumable by the frontend.
- The TypeScript types are in sync with the backend Pydantic model — no manual casting needed.
- New agents added to the registry automatically get their capabilities surfaced; no secondary step required.

---

## Tests added

**`tests/execution/test_provider_capabilities.py`** — 25 unit tests:
- `ExecutionCapabilities` model validation: valid minimal, all protocols accepted, invalid protocol rejected, extra fields forbidden, runtime_constraints list, `model_dump` JSON-serialisable
- Per-adapter class attribute correctness: all 6 concrete adapters + `BaseExecutionAdapter`
- `get_capabilities_for()`: all 9 registered pairs, unknown pairs return `None`, empty strings return `None`, no exception raised for unknowns, all registered pairs have non-None capabilities

**`tests/services/test_control_plane_views.py`** — updated `test_list_agent_catalog_projects_existing_agent_listing` to include `"execution_capabilities": None` for agents without source_type/execution_kind.

**Full suite result:** 284 passed, 1 skipped, 0 failures.

---

## Limitations and future work

- `execution_capabilities` on the frontend `ControlPlaneAgent` type is available but the `AgentsPage` does not yet render it. A future UI phase can add a "Capabilities" column or drawer to the agent catalog table.
- `Openhands` local-process and HTTP-service registrations share one adapter instance — both return `http_api`. This is accurate (the local-process variant still reaches OpenHands via HTTP), but the naming may surprise operators used to thinking of `LOCAL_PROCESS` as CLI-style. Can be addressed by a dedicated `OpenHandsLocalAdapter` if needed.
- `supports_token_reporting` is `False` for all non-CLI adapters. The token parsing path exists in some adapters but is not consistently exercised; this field accurately reflects current production behaviour.
