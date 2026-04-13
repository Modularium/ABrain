# Phase S9 — Provider / Adapter Inventory

## 1. Adapters and providers that exist today

### Static adapter registry (`core/execution/adapters/registry.py`)

Nine (execution_kind, source_type) pairs are registered:

| execution_kind | source_type | Adapter class |
|---|---|---|
| `system_executor` | `adminbot` | AdminBotExecutionAdapter |
| `http_service` | `openhands` | OpenHandsExecutionAdapter |
| `local_process` | `openhands` | OpenHandsExecutionAdapter |
| `local_process` | `claude_code` | ClaudeCodeExecutionAdapter |
| `cloud_agent` | `claude_code` | ClaudeCodeExecutionAdapter |
| `local_process` | `codex` | CodexExecutionAdapter |
| `cloud_agent` | `codex` | CodexExecutionAdapter |
| `workflow_engine` | `flowise` | FlowiseExecutionAdapter |
| `workflow_engine` | `n8n` | N8NExecutionAdapter |

### Adapter characteristics (today, implicit)

| Adapter | How it runs | Network | Local process | Cost reported | Tokens reported |
|---|---|---|---|---|---|
| adminbot | Internal tool dispatch (no subprocess, no HTTP) | No | No | No | No |
| openhands | HTTP POST `/api/v1/app-conversations` | Yes | No | Optional | No |
| claude_code | `claude -p … --output json` (subprocess) | No | Yes | Optional | Optional |
| codex | `codex exec --json …` (subprocess) | No | Yes | Optional | Optional |
| flowise | HTTP POST `/api/v1/prediction/{chatflow_id}` | Yes | No | Optional | No |
| n8n | HTTP POST to webhook URL | Yes | No | Optional | No |

---

## 2. source_type / execution_kind combinations that exist

From `AgentSourceType` and `AgentExecutionKind` enums:

**source_types defined:** NATIVE, FLOWISE, N8N, OPENHANDS, CODEX, CLAUDE_CODE, ADMINBOT

**execution_kinds defined:** LOCAL_PROCESS, HTTP_SERVICE, CLOUD_AGENT, WORKFLOW_ENGINE, SYSTEM_EXECUTOR

**Combinations with active adapters:** 9 (listed above)

**Combinations without active adapters (implicit gaps):**
- `NATIVE` — any execution_kind: no adapter (native agents run inline, no adapter needed)
- `LOCAL_PROCESS` + `FLOWISE`: not registered
- `HTTP_SERVICE` + `CLAUDE_CODE`: not registered
- etc.

---

## 3. Capabilities that are implicit today

All of the following are currently **known only by reading the adapter source code**:

- Whether a provider requires a network call (HTTP)
- Whether a provider requires a local CLI binary installed
- Whether cost data is populated in `ExecutionResult`
- Whether token count is populated in `ExecutionResult`
- What error codes an adapter can emit (`adapter_unavailable`, `adapter_timeout`, etc.)
- What configuration keys an adapter expects in `AgentDescriptor.metadata`
- Whether an adapter uses a process, HTTP, webhook, or tool dispatch

---

## 4. Where clear execution surfaces are missing today

1. **`AgentDescriptor`** has `source_type` + `execution_kind` but no field saying
   "what this combination can actually do."

2. **`BaseExecutionAdapter`** has no class-level capability declaration — each adapter's
   capabilities live only in its `execute()` logic, not as queryable metadata.

3. **`ExecutionAdapterRegistry`** has `resolve()` but no `get_capabilities()` — no way
   to ask "what can the adapter for this agent do?" without instantiating and reading code.

4. **`AgentCatalogEntry`** (API response) shows `source_type` and `execution_kind` but
   nothing about what those imply operationally.

5. **CLI `abrain agent list`** shows source and execution kind columns but no protocol or
   capability column.

---

## 5. Current inconsistencies

- `adminbot` uses `SYSTEM_EXECUTOR` execution_kind but behaves more like a local tool
  dispatcher, unlike any other adapter.
- `openhands` is registered for both `HTTP_SERVICE` and `LOCAL_PROCESS` with the same
  adapter class — the distinction is nominal, not behavioural.
- Costs are "optionally" reported by all HTTP adapters but there is no declaration
  stating which adapters attempt it — this is implicit.
- `claude_code` and `codex` both report tokens from a usage block, but this is not
  declared anywhere as a capability.
- No adapter declares what `metadata` keys it requires — operators must read source code.

---

## What S9 will operationalize

A new `ExecutionCapabilities` model in `core/execution/provider_capabilities.py` that:
- declares `execution_protocol`, `requires_network`, `requires_local_process`,
  `supports_cost_reporting`, `supports_token_reporting`, `runtime_constraints`
- is attached as a class attribute (`capabilities`) to every `BaseExecutionAdapter` subclass
- is queryable via `ExecutionAdapterRegistry.get_capabilities_for(execution_kind, source_type)`
- is surfaced in the agent catalog API (`AgentCatalogEntry.execution_capabilities`)
- is visible in the CLI agent list (protocol column)

No second adapter stack, no new registry, no new routing layer.
