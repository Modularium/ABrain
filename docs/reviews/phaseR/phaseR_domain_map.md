# Phase R — Domain Map

**Date:** 2026-04-12
**Branch:** `codex/phaseR-historical-re-review`
**Purpose:** Define the 10 analysis domains for the historical re-review.

---

## Domain Overview

| # | Domain | Historical Status | Current Status |
|---|---|---|---|
| 1 | Core Architecture | Monolithic → microservices → canonical layers | Canonical layer stack |
| 2 | Decision / Routing / Agent Model | Implicit → NN-based → canonical decision layer | Canonical decision layer with neural policy |
| 3 | Execution / Adapter Layer | Hardcoded workers → adapters → canonical dispatcher | Canonical dispatcher + 6 adapters |
| 4 | Learning / Feedback / NN | Heavy PyTorch (torch, mlflow) → canonical learning | Lightweight canonical learning (no torch on main) |
| 5 | Governance / Approval / Audit | None → AgentContract → canonical policy + HITL + trace | Canonical governance + approval + audit |
| 6 | MCP / Interfaces / APIs | REST microservices + MCP v1 → MCP v2 | MCP v2 only |
| 7 | UI / Control Plane / UX | React + Python monitoring + legacy dashboards | Single React control plane |
| 8 | CLI / Setup / Dev Experience | 30+ shell scripts → abrain CLI → one-liner setup | `scripts/abrain` + `scripts/setup.sh` |
| 9 | Docs / Information Architecture | 100+ doc files (Docusaurus) → lean arch docs | Canonical architecture docs + reviews |
| 10 | Integrations | flowise-plugin, n8n-plugin, OpenHands, Codex, Claude, AdminBot | Adapters (canonical) + AdminBot (production) |

---

## Domain 1 — Core Architecture

**Scope:** How the system is structured at the highest level. The evolution of the main runtime, module boundaries, and the runtime execution path.

**Key historical artifacts:**
- `managers/` (24 manager classes)
- `core/` legacy flat files (35 files)
- `services/` old microservice directories (9 directories)
- The canonical pivot commit `c2b4579d`
- `docs/architecture/CANONICAL_RUNTIME_STACK.md`

---

## Domain 2 — Decision / Routing / Agent Model

**Scope:** How the system selects which agent handles a task. Agent registry, routing engine, neural policy, capabilities, candidate filtering.

**Key historical artifacts:**
- `managers/meta_learner.py` — PyTorch MetaLearner
- `managers/nn_manager.py` — NNManager
- `managers/hybrid_matcher.py` — HybridMatcher
- `core/matching_engine.py` — old matching
- `core/routing/` — old HTTP-based routing
- `core/decision/` — current canonical decision layer (all files)

---

## Domain 3 — Execution / Adapter Layer

**Scope:** How tasks are actually dispatched and executed. Adapter pattern, sandboxing, execution engine.

**Key historical artifacts:**
- `agents/agentic_worker.py` — LangChain-based agent worker
- `agents/agent_creator.py` / `agent_factory.py` / `agent_generator.py` / `agent_improver.py`
- `agents/software_dev/` — Python/TypeScript/SafetyValidator agents
- `agents/openhands/` — OpenHands-specific agent wrappers
- `core/execution/` — current canonical execution layer

---

## Domain 4 — Learning / Feedback / NN

**Scope:** How the system learns from task outcomes. Neural network models, training pipeline, reward models, online updates, feedback loops.

**Key historical artifacts:**
- `training/agent_selector_model.py` — 292 lines, PyTorch-based agent selector
- `training/data_logger.py` — 355 lines, MLflow-based data logger
- `training/reinforcement_learning.py` — Q-learning
- `managers/meta_learner.py` — PyTorch meta-learner
- `managers/ab_testing.py` — A/B testing
- `managers/adaptive_learning_manager.py` — adaptive learning
- `managers/evaluation_manager.py` — evaluation
- `utils/logging_util.py` — MLflow + torch JSON encoder
- `core/decision/learning/` — current canonical learning subsystem (5 files)

---

## Domain 5 — Governance / Approval / Audit

**Scope:** How the system enforces policies, manages human-in-the-loop approval, and records what happened.

**Key historical artifacts:**
- `core/governance.py` (flat file) — early governance concept
- `core/governance/legacy_contracts.py` — AgentContract dataclass
- `core/trust_evaluator.py` — trust score calculation
- `core/trust_network.py` — trust graph
- `core/trust_circle.py` — trust circles
- `core/roles.py`, `core/role_capabilities.py` — role/capability enforcement
- `core/access_control.py` — token-based access control
- `security/input_filter.py` — input sanitization
- Current: `core/governance/`, `core/approval/`, `core/audit/`

---

## Domain 6 — MCP / Interfaces / APIs

**Scope:** How external systems connect to ABrain. MCP protocol versions, REST API surface, tool schemas.

**Key historical artifacts:**
- `mcp/` — old MCP v1 microservice package (8 sub-services)
- `legacy-runtime/mcp/` — legacy-runtime MCP client/gateway/server/ws
- `interfaces/mcp_v1/` — disabled MCP v1 server
- `api/` — old API client/endpoints/models
- Current: `interfaces/mcp/` (MCP v2), `api_gateway/main.py`

---

## Domain 7 — UI / Control Plane / UX

**Scope:** What the user sees and interacts with. Dashboards, monitoring, task visualization.

**Key historical artifacts:**
- `monitoring/agen-nn_dashboard.tsx` — rich React dashboard with mock data (CPU, GPU, memory, agents, tasks, knowledge bases, A/B tests, security events)
- `monitoring/agent_dashboard.py` — Python terminal dashboard
- `monitoring/system_monitor.py` — system metrics collection
- `archive/ui_legacy/legacy_frontend/` — early frontend
- `archive/ui_legacy/monitoring_dashboard/` — monitoring dashboard
- Current: `frontend/agent-ui/` — React + TypeScript + Zustand + Vite (18 pages)

---

## Domain 8 — CLI / Setup / Dev Experience

**Scope:** How developers and operators interact with the system from the command line. Setup, onboarding, tooling.

**Key historical artifacts:**
- ~30 legacy `.sh` scripts: `setup.sh`, `start_fullstack.sh`, `repair_env.sh`, `validate.sh`, `status.sh`, `test.sh`, `deploy.sh`, `REPAIR.sh`, `build_and_start.sh`, `install_dependencies.sh`, etc.
- `sdk/cli/` — Python SDK CLI (commands, schemas, templates)
- `tools/cli_docgen.py` — auto-generate CLI docs
- Current: `scripts/abrain` (bash CLI), `scripts/setup.sh` (one-liner), `scripts/abrain_mcp.py`

---

## Domain 9 — Docs / Information Architecture

**Scope:** How the system documents itself. User-facing docs, architecture docs, API references, development guides.

**Key historical artifacts:**
- Docusaurus-based docs site (full `.docusaurus/` cache, ~100+ doc files)
- `docs/BenutzerHandbuch/` — German user manual with SVG diagrams
- `docs/Wiki/` — planning docs
- `docs/cli/` — CLI docs with SVG diagrams
- `docs/api/` — OpenAPI/service API docs
- `docs/architecture/` (old files: agent-levels, agent-memory, agent-missions, agent-teams, coalitions, delegation-model, dynamic-roles, federation, identity-and-signatures, reputation-system, skill-system, token-budgeting, trust-network, voting-logic, etc.)
- `docs/use-cases/` — scenario docs
- Current: `docs/architecture/` (18 files), `docs/reviews/` (25+ files)

---

## Domain 10 — Integrations

**Scope:** How ABrain connects to external platforms and tools.

**Key historical artifacts:**
- `integrations/flowise-legacy-runtime/` — Flowise plugin
- `integrations/flowise-nodes/` — Flowise custom nodes
- `integrations/n8n-legacy-runtime/` — n8n integration
- `agents/openhands/` — OpenHands agent wrappers
- `tools/generate_flowise_nodes.py` / `generate_flowise_plugin.py` — code generators
- `legacy-runtime/integrations/langchain_mcp_adapter.py` — LangChain MCP adapter
- Current: `adapters/adminbot/`, `adapters/flowise/`, `core/execution/adapters/` (6 adapters)
