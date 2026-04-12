# Canonical Repository Structure

**ABrain — Modular Multi-Agent Orchestration Framework**
**Date:** 2026-04-11 (Phase O canonicalization)

This document defines the single source of truth for what belongs on `main`.

---

## Active Code Paths

### Decision Layer — `core/decision/`
Routing engine, neural policy, agent registry/descriptor, planner, capabilities, candidate filter, feedback loop, learning subsystem (dataset, trainer, online_updater, reward_model, persistence).

### Execution Layer — `core/execution/`
ExecutionDispatcher, ExecutionEngine, and all canonical adapters:
- `adapters/adminbot_adapter.py`
- `adapters/openhands_adapter.py`
- `adapters/claude_code_adapter.py`
- `adapters/codex_adapter.py`
- `adapters/n8n_adapter.py`
- `adapters/flowise_adapter.py`

### Approval Layer — `core/approval/`
Human-in-the-loop approval: models, ApprovalPolicy, ApprovalStore (durable JSON).

### Governance Layer — `core/governance/`
PolicyEngine, PolicyRegistry, PolicyRule, enforce_policy.

### Audit / Explainability Layer — `core/audit/`
TraceStore (SQLite), trace_models, ExplainabilityRecord, TraceContext, exporters.

### Orchestration Layer — `core/orchestration/`
PlanExecutionOrchestrator, resume_plan, ResultAggregator, PlanStateStore (SQLite — Phase N).

### Core Models — `core/models/`
AdminBot models, errors, identity (RequesterIdentity), tooling (ToolExecutionRequest).

### Core Tools — `core/tools/`
ToolRegistry (fixed/frozen), ToolDefinition, ToolHandlers.

### Core Utilities — `core/*.py`
- `core/model_context.py` — ModelContext, TaskContext
- `core/config.py` — Settings (pydantic_settings)
- `core/logging_utils.py` — structlog middleware
- `core/metrics_utils.py` — Prometheus middleware
- `core/auth_utils.py` — JWT auth middleware
- `core/audit_log.py` — AuditLog, AuditEntry

---

## Active Service Layer

### Canonical Service Layer — `services/core.py`
The single service module that wires all canonical layers together.
Active functions: `run_task`, `run_task_plan`, `approve_plan_step`, `reject_plan_step`, `list_pending_approvals`, `get_trace`, `list_recent_traces`, `get_explainability`, `list_recent_plans`, `list_recent_governance_decisions`, `list_agent_catalog`, `get_governance_state`, `execute_tool`, `list_agents`.

### Routing Agent — `services/routing_agent/service.py`
Thin canonical wrapper around `core/decision` routing engine.

### Federation Manager — `services/federation_manager/service.py`
Multi-node federation dispatch.

---

## Active API / Interface

### REST Control Plane API — `api_gateway/main.py`
The single active REST API. Exposes:
- `POST /control-plane/tasks/run` — run a task via canonical service layer
- `POST /control-plane/plans/run` — run a multi-step plan
- `POST /control-plane/approvals/{approval_id}/approve` — approve a paused plan step
- `POST /control-plane/approvals/{approval_id}/reject` — reject a paused plan step
- `GET /control-plane/overview` — system overview
- `GET /control-plane/traces` — recent traces
- `GET /control-plane/traces/{trace_id}` — trace detail
- `GET /control-plane/traces/{trace_id}/explainability` — explainability detail
- `GET /control-plane/approvals` — pending approvals
- `GET /control-plane/governance` — recent governance decisions
- `GET /control-plane/plans` — recent plans
- `POST /chat`, `GET /chat/history/{sid}`, `POST /chat/feedback` — legacy bridge/chat routes still present in the gateway
- `POST /sessions`, `GET /sessions/{sid}/history` — session bridge routes
- `GET /agents` — agent catalog
- `POST /embed` — embedding passthrough
- `GET /metrics` — Prometheus metrics

### MCP v2 Interface — `interfaces/mcp/`
The single active MCP interface. Canonical tools:
- `run_task`, `run_plan`, `approve_step`, `reject_step`, `list_pending_approvals`, `get_trace`, `get_explainability`
CLI entrypoint: `scripts/abrain_mcp.py` → `interfaces/mcp/server.py::run_stdio_server()`

### Adapters — `adapters/`
- `adapters/adminbot/` — AdminBot v2 hardened client + service
- `adapters/flowise/` — Flowise agent importer/exporter

---

## Active UI

**One and only UI:** `frontend/agent-ui/`

React + TypeScript + Zustand + Vite + Tailwind.
Pages: Dashboard, Agents, Tasks, Routing, Traces, Approvals (via AdminPage), Feedback, Metrics, Settings.
nginx config: `frontend/nginx.conf`.

No other UI is active. `monitoring/` and `archive/ui_legacy/` are deleted.

---

## Active Scripts

| Script | Purpose |
|--------|---------|
| `scripts/abrain` | Canonical Bash CLI |
| `scripts/agentnn` | Thin legacy wrapper around `scripts/abrain` |
| `scripts/abrain_mcp.py` | MCP v2 stdio entrypoint |
| `scripts/setup.sh` | Canonical one-liner bootstrap for `.venv`, deps, editable install, API/MCP smokes and UI build |
| `scripts/__init__.py` | Makes scripts importable |

---

## Active CI

| Workflow | Purpose |
|----------|---------|
| `.github/workflows/core-ci.yml` | Foundations CI (canonical test suite + compile check) |
| `.github/workflows/adminbot-security-gates.yml` | AdminBot security gate (tests + compile) |
| `.github/workflows/openhands-resolver.yml` | OpenHands issue resolver |

---

## Active Tests

The canonical test suite runs via:
```
python -m pytest -o python_files='test_*.py' \
  tests/mcp \
  tests/approval \
  tests/orchestration \
  tests/execution \
  tests/decision \
  tests/adapters \
  tests/core \
  tests/services \
  tests/state \
  tests/integration/test_node_export.py
```

Tests in `tests/mcp/` that are canonical:
- `test_plan_pause_resume.py`
- `test_policy_enforcement.py`
- `test_run_task_tool.py`
- `test_server_exposure.py`
- `test_trace_integration.py`

---

## Active Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Project entry point |
| `AGENTS.md` | AI tool instructions |
| `CHANGELOG.md` | Release history |
| `CONTRIBUTING.md` | Contributor guide |
| `docs/architecture/SETUP_ONE_LINER_FLOW.md` | Canonical one-liner setup flow |
| `docs/architecture/SETUP_AND_BOOTSTRAP_FLOW.md` | Canonical bootstrap flow |
| `docs/architecture/CANONICAL_RUNTIME_STACK.md` | Canonical layer overview |
| `docs/architecture/CANONICAL_REPO_STRUCTURE.md` | **This file** |
| `docs/integrations/adminbot/` | AdminBot integration contract |
| `docs/reviews/` | Phase review records |

---

## What Is NOT on `main` After Phase O

| Category | Removed |
|----------|---------|
| Old MCP v1 path | `interfaces/mcp_v1/`, `mcp/` directory |
| Old agent system | `agents/`, `agentnn/`, `archive/` |
| Old SDK/CLI | `sdk/` |
| Old managers | `managers/` |
| Old training | `training/` |
| Old microservices | `services/agent_coordinator/`, `services/agent_registry/`, `services/agent_worker/`, `services/coalition_manager/`, `services/llm_gateway/`, `services/session_manager/`, `services/task_dispatcher/`, `services/user_manager/`, `services/vector_store/` |
| Old monitoring UI | `monitoring/` |
| Old integrations | `integrations/` |
| Old core legacy | ~35 flat Python files in `core/` |
| Old docs | ~100+ old doc files across use-cases, CLI, BenutzerHandbuch, Wiki, deployment, etc. |
| Old CI | ci-core.yml, ci-full.yml, deploy.yml, docs.yml, deploy-docs.yml, plugin-release.yml |
| Old root files | docker-compose files, Dockerfiles, setup.py, flowise manifests, PDFs, planning docs |

---

## Invariants

1. `services/core.py` is the **single service layer**. No parallel service entry point exists.
2. `api_gateway/main.py` is the **single REST API**. No other FastAPI app is active.
3. `interfaces/mcp/` is the **single MCP interface**. MCP v1 is deleted.
4. `frontend/agent-ui/` is the **single UI**. No monitoring dashboard or legacy frontend.
5. `core/decision/` → `core/execution/` → `core/approval/` → `core/governance/` → `core/audit/` → `core/orchestration/` is the **canonical runtime stack**. Nothing else routes or executes tasks.
6. The canonical test suite runs in the project venv and produces 0 failures.
