# Phase O — Full Repository Inventory

**Date:** 2026-04-11
**Branch:** `codex/phaseO-canonicalization-cleanup`
**Purpose:** Classify every repo area before cleanup

---

## Classification Key

- **A** — Canonical / active / keep
- **B** — Obsolete but feature-relevant → migrate first, then delete
- **C** — Obsolete / legacy / historical without product value → delete
- **D** — Docs / artefact waste → delete or consolidate
- **E** — Unclear → decided below

---

## 1. `core/` Canonical Layers (A)

| Path | Classification | Notes |
|------|----------------|-------|
| `core/decision/` | **A** | Complete canonical decision layer: routing engine, neural policy, agent registry, planner, capabilities, feedback loop, learning (dataset/trainer/online_updater/reward_model/persistence) |
| `core/execution/` | **A** | Complete canonical execution: dispatcher, execution_engine, all adapters (adminbot, openhands, claude_code, codex, n8n, flowise) |
| `core/approval/` | **A** | Complete canonical HITL approval layer: models, policy, store |
| `core/governance/` | **A** (except legacy_contracts.py) | Canonical governance: policy_engine, policy_models, policy_registry, enforcement — `legacy_contracts.py` only exists for old code (see C) |
| `core/audit/` | **A** | Complete canonical audit/trace layer: trace_models, trace_store, context, exporters |
| `core/orchestration/` | **A** | Complete multi-agent orchestration: orchestrator, resume, result_aggregation, state_store (Phase N) |
| `core/models/` | **A** | Canonical models: adminbot, errors, identity, tooling |
| `core/tools/` | **A** | Canonical tool registry and handlers |
| `core/model_context.py` | **A** | ModelContext/TaskContext used by decision layer and canonical services |
| `core/config.py` | **A** | Settings (pydantic_settings) used by logging_utils |
| `core/logging_utils.py` | **A** | Structlog-based middleware used by api_gateway |
| `core/metrics_utils.py` | **A** | Prometheus metrics middleware used by api_gateway |
| `core/auth_utils.py` | **A** | Auth middleware used by api_gateway |
| `core/audit_log.py` | **A** | AuditLog/AuditEntry used by services/core.py |
| `core/execution/dispatcher.py` | **A** | ExecutionDispatcher (canonical) |
| `core/__init__.py` | **A** (needs cleanup) | Re-exports canonical classes; still references `AgentRuntime` from agents/ via try/except — remove that reference |

## 2. `core/` Pre-Canonical Legacy Files (C)

All flat files in `core/` that pre-date the canonical layer system. None are imported by the canonical test suite, api_gateway, or services/core.py (1409-line version).

| Path | Classification | Notes |
|------|----------------|-------|
| `core/access_control.py` | **C** | Old role/token access control. Used only by old task_dispatcher service. |
| `core/agent_bus.py` | **C** | Old pub/sub bus. No canonical usage. |
| `core/agent_evolution.py` | **C** | Old agent self-improvement. No canonical usage. |
| `core/agent_profile.py` | **C** | Old agent identity/profile. No canonical usage. |
| `core/agents/` | **C** | AgentRuntime wrapper around legacy ChatbotAgent/SupervisorAgent. Only used by old `agents/` directory and optionally imported in `core/__init__.py`. Remove once `agents/` deleted. |
| `core/auto_trainer.py` | **C** | Old auto trainer. Imports from services/session_manager (old service). |
| `core/coalitions.py` | **C** | Old coalition system. No canonical usage. |
| `core/crypto.py` | **C** | Old ECDSA signing. No canonical usage. |
| `core/delegation.py` | **C** | Old delegation/sub-agent system. No canonical usage. |
| `core/dispatch_queue.py` | **C** | Old async task queue. No canonical usage. |
| `core/feedback_loop.py` | **C** | Old feedback loop (duplicate of `core/decision/feedback_loop.py`). |
| `core/feedback_utils.py` | **C** | Old feedback utilities. No canonical usage. |
| `core/governance.py` | **C** | Old governance module (flat file, predates `core/governance/`). Used only by old services. |
| `core/governance/legacy_contracts.py` | **C** | AgentContract dataclass only used by old services/task_dispatcher and old tests. Remove from `core/governance/__init__.py` export. |
| `core/level_evaluator.py` | **C** | Old agent level progression. No canonical usage. |
| `core/levels.py` | **C** | Old agent level models. No canonical usage. |
| `core/llm_providers/` | **C** | Old LLM provider abstraction (OpenAI, Anthropic, local). Not imported by any canonical code path. |
| `core/matching_engine.py` | **C** | Old agent matching. No canonical usage. |
| `core/memory_store.py` | **C** | Old in-memory/file store. No canonical usage. |
| `core/mission_prompts.py` | **C** | Old mission prompt templates. No canonical usage. |
| `core/missions.py` | **C** | Old mission system. No canonical usage. |
| `core/privacy.py` | **C** | Old data privacy/access levels. No canonical usage. |
| `core/privacy_filter.py` | **C** | Old context redaction. No canonical usage. |
| `core/reputation.py` | **C** | Old reputation scoring. No canonical usage. |
| `core/rewards.py` | **C** | Old reward model (predates `core/decision/learning/reward_model.py`). |
| `core/role_capabilities.py` | **C** | Old role capability enforcement. No canonical usage. |
| `core/roles.py` | **C** | Old role resolution. No canonical usage. |
| `core/routing/__init__.py` | **C** | Old HTTP-based routing wrapper around routing service URL. Replaced by canonical `core/decision/routing_engine.py`. |
| `core/run_service.py` | **C** | uvicorn runner helper used only by old MCP service directories. |
| `core/schemas.py` | **C** | Old StatusResponse model. Used only by old services/health_router.py. |
| `core/self_reflection.py` | **C** | Old agent self-reflection. No canonical usage. |
| `core/session_store.py` | **C** | Old session persistence. No canonical usage. |
| `core/skill_matcher.py` | **C** | Old skill matching. No canonical usage. |
| `core/skills.py` | **C** | Old skill models. No canonical usage. |
| `core/team_knowledge.py` | **C** | Old team shared knowledge. No canonical usage. |
| `core/teams.py` | **C** | Old team models. No canonical usage. |
| `core/training.py` | **C** | Old training module. No canonical usage. |
| `core/training/` | **C** | Old training weights loader. No canonical usage. |
| `core/trust_circle.py` | **C** | Old trust circle. No canonical usage. |
| `core/trust_evaluator.py` | **C** | Old trust evaluator. No canonical usage. |
| `core/trust_network.py` | **C** | Old trust network. No canonical usage. |
| `core/utils/imports.py` | **C** | Old import utilities. No canonical usage. |
| `core/voting.py` | **C** | Old voting/consensus. No canonical usage. |

---

## 3. `services/` (mix)

| Path | Classification | Notes |
|------|----------------|-------|
| `services/core.py` | **A** (needs cleanup) | 1409-line canonical service layer. Contains 5 legacy functions (`create_agent`, `evaluate_agent`, `load_model`, `train_model`, `dispatch_task`) that still import from old `legacy runtime/`, `managers/`, `training/`. These functions are **B** — remove them (they have no canonical callers, no api_gateway endpoint calls them). `run_task` and all canonical functions stay. |
| `services/routing_agent/service.py` | **A** | Thin canonical wrapper around `core/decision` routing engine |
| `services/routing_agent/` (rest) | **C** | `main.py`, `routes.py`, `config.py`, `rules.yaml`, `Dockerfile` — only needed if running as standalone microservice, which is obsolete. `service.py` is all that's needed. |
| `services/federation_manager/service.py` | **A** | Federation dispatch, tested canonically |
| `services/federation_manager/` (rest) | **C** | `main.py`, `routes.py`, `config.py` — standalone microservice scaffolding, not used |
| `services/__init__.py` | **A** | Keep |
| `services/health_router.py` | **C** | Old health router used only by old service directories |
| `services/agent_coordinator/` | **C** | Old coordinator microservice. No canonical usage. |
| `services/agent_registry/` | **C** | Old registry microservice. Superseded by `core/decision/agent_registry.py`. |
| `services/agent_worker/` | **C** | Old worker service. No canonical usage. |
| `services/coalition_manager/` | **C** | Old coalition microservice. No canonical usage. |
| `services/llm_gateway/` | **C** | Old LLM gateway microservice. No canonical usage. |
| `services/session_manager/` | **C** | Old session microservice. No canonical usage. |
| `services/task_dispatcher/` | **C** | Old task dispatcher. Superseded by `core/execution/dispatcher.py` + `services/core.py`. |
| `services/user_manager/` | **C** | Old user management. No canonical usage. |
| `services/vector_store/` | **C** | Old vector store microservice. No canonical usage. |

---

## 4. `api_gateway/` (A)

| Path | Classification | Notes |
|------|----------------|-------|
| `api_gateway/main.py` | **A** | Canonical REST API / control plane gateway |
| `api_gateway/connectors.py` | **A** | ServiceConnector (used by api_gateway but for legacy service URLs — still provides the URL routing). Keep for now, may simplify later. |
| `api_gateway/__init__.py` | **A** | Keep |

---

## 5. `interfaces/` (mix)

| Path | Classification | Notes |
|------|----------------|-------|
| `interfaces/mcp/` | **A** | Canonical MCP v2 server, tool_registry, handlers (run_task, run_plan, approval, trace) |
| `interfaces/__init__.py` | **A** | Keep |
| `interfaces/mcp_v1/` | **C** | Disabled MCP v1 server. Guarded by env var, always raises on import. Tests auto-skip. No value on main. |

---

## 6. `adapters/` (A)

| Path | Classification | Notes |
|------|----------------|-------|
| `adapters/adminbot/` | **A** | Canonical AdminBot v2 adapter (client + service) |
| `adapters/flowise/` | **A** | Canonical Flowise importer/exporter |
| `adapters/__init__.py` | **A** | Keep |

---

## 7. `frontend/` (A)

| Path | Classification | Notes |
|------|----------------|-------|
| `frontend/agent-ui/` | **A** | The one and only active UI: React + TypeScript + Zustand + Vite |
| `frontend/nginx.conf` | **A** | Keep |

---

## 8. `mcp/` (C)

Old MCP v1 microservice package (agent_registry, llm_gateway, plugin_agent_service, routing_agent, session_manager, task_dispatcher, vector_store, worker_dev, worker_loh, worker_openhands). All disabled or superseded by canonical runtime. MCP v2 is in `interfaces/mcp/`.

**Decision: Delete entirely.**

---

## 9. `agents/` (C)

Pre-canonical agent implementations: supervisor_agent, chatbot_agent, web_crawler, web_scraper, software_dev wrappers, openhands wrappers, agent_creator, agent_factory, agent_generator. All superseded by the canonical execution adapter layer in `core/execution/adapters/`.

**Decision: Delete entirely.**

---

## 10. `legacy runtime/` (C)

Pre-ABrain CLI runtime: auth, catalog, context, deployment, integrations, mcp (old), prompting, reasoning, session, storage. Used only by old test_client_interaction.py and test_server_exposure.py (which test that it's disabled).

**Decision: Delete entirely.**

---

## 11. `archive/` (C)

Explicitly archived code: example_agent, sample_agent, legacy critic_agent_service, Smolit_LLM-NN, ui_legacy (legacy_frontend, monitoring_dashboard).

**Decision: Delete entirely.** Git history preserves it.

---

## 12. `sdk/` (C)

Old SDK: CLI commands (agent, mcp, plugins, etc.), python_agent_nn client, nn_models, client. All CLI commands reference old services. Canonical runtime is accessed via `services/core.py` and `api_gateway/`.

**Decision: Delete entirely.**

---

## 13. `training/` (C)

Old training layer: agent_selector_model, data_logger, federated, reinforcement_learning, train. Superseded by `core/decision/learning/`.

**Decision: Delete entirely.**

---

## 14. `managers/` (C)

Old manager layer: agent_manager, agent_optimizer, model_manager, model_registry, monitoring_system, meta_learner, nn_manager, etc. No canonical runtime dependency.

**Decision: Delete entirely.**

---

## 15. `monitoring/` (C)

Old monitoring dashboard (Python + React/TSX). Not the active UI. Active UI is `frontend/agent-ui/`.

**Decision: Delete entirely.**

---

## 16. `integrations/` (C)

Old Flowise/n8n plugins: flowise-legacy runtime, flowise-nodes, n8n-legacy runtime. All point to old API endpoints. Canonical Flowise integration is in `adapters/flowise/`.

**Decision: Delete entirely.**

---

## 17. `benchmarks/` (C)

Old performance benchmarks. Import old utils/optional_torch. No canonical usage.

**Decision: Delete.**

---

## 18. `datastores/` (C)

Old vector_store.py and worker_agent_db.py. Superseded by canonical execution layer.

**Decision: Delete.**

---

## 19. `security/` (C)

Old input_filter.py. Uses old logging utils. No canonical usage.

**Decision: Delete.**

---

## 20. `server/` (C)

Old frontend bridge server (FastAPI). Superseded by `api_gateway/`.

**Decision: Delete.**

---

## 21. `tools/` root (C)

Old tool generators: generate_flowise_nodes.py, generate_flowise_plugin.py, package_plugin.py, validate_plugin_manifest.py, cli_docgen.py, registry.py. All reference old plugin/flowise patterns.

**Decision: Delete.**

---

## 22. `api/` (C)

Old API client/endpoints/models/smolitux_integration. Superseded by `api_gateway/`.

**Decision: Delete.**

---

## 23. `config/` root (C)

Old llm_config.py, smolitux_config.py, services.yaml. Superseded by `core/config.py`. Used only by `scripts/setup_llamafile.py` (also being deleted).

**Decision: Delete.**

---

## 24. `utils/` root (mix)

| Path | Classification | Notes |
|------|----------------|-------|
| `utils/api_utils.py` | **B** | Only `api_route` decorator; used by `api_gateway/main.py` and `services/health_router.py`. Inline into `api_gateway/main.py`, then delete. |
| `utils/agent_descriptions.py` | **C** | Old agent descriptions. |
| `utils/document_manager.py` | **C** | Old document manager. |
| `utils/flowise.py` | **C** | Old Flowise config helper. |
| `utils/knowledge_base.py` | **C** | Old knowledge base. |
| `utils/logging_util.py` | **C** | Old logging. Superseded by `core/logging_utils.py`. |
| `utils/optional_torch.py` | **C** | Old torch availability check. No canonical usage. |
| `utils/prompts.py`, `prompts_v2.py` | **C** | Old prompts. |
| `utils/__init__.py` | **C** | Delete with directory. |

---

## 25. `scripts/` (mix)

| Path | Classification | Notes |
|------|----------------|-------|
| `scripts/abrain_mcp.py` | **A** | Canonical MCP v2 stdio entrypoint |
| `scripts/__init__.py` | **A** | Keep (makes scripts importable) |
| `scripts/generate_openapi.py` | **C** | Generates OpenAPI for old service directories. |
| `scripts/setup_llamafile.py` | **C** | Old llamafile setup. |
| `scripts/setup_local_models.py` | **C** | Old local model setup. |
| `scripts/*.sh` (all) | **C** | Old shell scripts: build_and_start, build_and_test, build_docker, build_frontend, check_env, check_integrity, deploy*, deploy_docs, deploy_to_registry, help, install*, repair_env, start_docker, start_mcp, status, test_env, test_install, test, validate + lib/, helpers/, deploy/, install/ subdirs |

---

## 26. `tests/` (mix)

### Keep (canonical)
- `tests/mcp/` — keep: test_plan_pause_resume.py, test_policy_enforcement.py, test_run_task_tool.py, test_server_exposure.py, test_trace_integration.py
- `tests/approval/` — all keep
- `tests/orchestration/` — all keep
- `tests/execution/` — all keep
- `tests/decision/` — all keep
- `tests/adapters/` — all keep
- `tests/core/` — all keep
- `tests/services/` — keep except `test_core.py` (tests old legacy functions)
- `tests/integration/test_node_export.py` — keep
- `tests/state/` — all keep (Phase N)
- `tests/conftest.py` — keep
- `tests/test_sanity.py` — keep
- `tests/__init__.py` — keep

### Delete (reference old code)
- `tests/mcp/test_agent_external_tools.py` — uses `sdk.cli.main` (old SDK)
- `tests/mcp/test_client_interaction.py` — uses `legacy runtime.mcp.mcp_client` (old, disabled)
- `tests/mcp/test_mcp_v1_server.py` — tests disabled MCP v1; auto-skips in CI
- `tests/services/test_core.py` — tests old `create_agent`/`dispatch_task`/etc. from old services/core.py
- All remaining `tests/` subdirectories and `tests/test_*.py` root files (test old code)

---

## 27. `.github/workflows/` (mix)

| Path | Classification | Notes |
|------|----------------|-------|
| `.github/workflows/core-ci.yml` | **A** | Canonical Foundations CI |
| `.github/workflows/adminbot-security-gates.yml` | **A** | Canonical AdminBot security gates |
| `.github/workflows/ci-core.yml` | **C** | Old CI using old `./ci/setup_env.sh` + `./ci/lint_test.sh` |
| `.github/workflows/ci-full.yml` | **C** | Old full CI |
| `.github/workflows/deploy.yml` | **C** | Old deploy using requirements.txt |
| `.github/workflows/docs.yml` | **C** | Old Docusaurus deploy |
| `.github/workflows/deploy-docs.yml` | **C** | Duplicate docs deploy |
| `.github/workflows/plugin-release.yml` | **C** | Old plugin release workflow |
| `.github/workflows/openhands-resolver.yml` | **A** (keep) | OpenHands issue resolver — keep as-is |

---

## 28. Root-level files (mix)

### Keep
- `README.md` — main project readme
- `AGENTS.md` — agent instructions for AI tools
- `CHANGELOG.md` — project changelog
- `CODE_OF_CONDUCT.md` — governance
- `CONTRIBUTING.md` — contributor guide
- `VERSION` — version string
- `pytest.ini` — test configuration
- `mypy.ini` — type checking config

### Delete (C/D)
- `main.py` — old entrypoint (wraps legacy AgentRuntime)
- `config.py` — old root config
- `flowise_deploy.py` — old Flowise deployment
- `flowise-plugin.json` — old Flowise plugin manifest
- `mcp_services.json` — old MCP service config
- `RELEASE_NOTES_v1.0.0.md` — old release notes
- `RELEASE.md` — old release doc
- `REPAIR.sh` — old repair script
- `README-smolitux-ui-integration.md` — old Smolitux UI integration guide
- `INTEGRATION_GUIDE.md` — old integration guide
- `FULLSTACK_README.md` — old fullstack guide
- `Konsolidierung-und-Integration-redundanter-Implementierungen.md` — old planning doc
- `Modernisierung-von-ABrain-zur-Modular- Control-Plane-Architektur.md` — old migration doc
- `start_fullstack.sh` — old start script
- `status_check.sh` — old status script
- `SETUP_FIXES.md` — old setup fixes
- `test_system.sh` — old test script
- `install_openhands_deps.sh` — old install script
- `codex-init.sh` — old codex init
- `prepare_github_release.sh` — old release script
- `sidebars.js` — Docusaurus (no longer using Docusaurus)
- `legacy-runtime_devplan_todo.md` — old devplan
- `codex_research_notes.md` — old research notes
- `codex.tasks.json` — old task tracking
- `codex_progress.log` — session log
- `docker-compose.yml` — old multi-service compose
- `docker-compose.monitoring.yml` — old monitoring compose
- `docker-compose.production.yml` — old production compose
- `Dockerfile` — old service Dockerfile
- `Dockerfile.fallback` — old fallback
- `deploy/k8s/` — old k8s deployment
- `setup.py` — old setuptools config
- `package.json`, `package-lock.json` (root) — Docusaurus docs
- `test-requirements.txt` — old test requirements
- `.abrain/`, `.abrain_config` — old runtime state
- `.codex.json`, `.codex/` — old codex state
- `TODO-Liste für ABrain Entwicklungsplan.md` — old planning
- `TODO-Liste für ABrain Entwicklungsplan.pdf` — old planning PDF
- `Strategie und Konfigurationsdateien für den autonomen Codex-Agent.pdf` — old planning PDF
- `Analyse der ABrain Codebasis.pdf` — old analysis PDF
- `agent_profiles/` — old agent profile YAML files
- `README.plugin.md` — old plugin readme
- `CHANGELOG.md` (docs/) — duplicate, keep only root CHANGELOG.md
- `ci/` directory — old CI scripts (lint_test.sh, setup_env.sh)

---

## 29. `docs/` (mix — see Phase 6 report for detail)

### Keep
- `docs/architecture/CANONICAL_RUNTIME_STACK.md`
- `docs/architecture/decisions/phase5_phase6.md`
- `docs/integrations/adminbot/` (all files — active integration contract)
- `docs/reviews/` (all Phase review files — project history)
- `docs/README.md` if present

### Delete / consolidate
- All old use-cases (dozens of old scenario files)
- `docs/BenutzerHandbuch/` — old user manual for old UI
- `docs/Wiki/` — old planning docs
- `docs/cli/` — old CLI docs
- `docs/deployment/` — old deployment guides (k8s, etc.)
- `docs/development/` — old dev guides
- `docs/api/` — old OpenAPI/service API docs (superseded by api_gateway)
- `docs/architecture/` (all except CANONICAL_RUNTIME_STACK.md and decisions/) — old arch docs
- `docs/security/` — old security docs
- `docs/observability/` — old monitoring docs
- `docs/governance/` — old governance process docs
- Old top-level doc files: architecture_overview.md, api_reference.md, catalog.md, cli.md, cli_dev.md, cli_quickstart.md, config_reference.md, context_map.md, deployment.md, developer_setup.md, dev_managers.md, errors.md, flowise*.md, frontend*.md, install.md, llm_provider_overview.md, maintenance.md, mcp.md, metrics*.md, migration_status.md, models.md, orchestrator.md, overview.md, plugins.md, prompting.md, realtime.md, reasoning.md, release_checklist.md, RELEASE_NOTES.md, releases/, roadmap.md, roles.md, scripts.md, sdk/, service_audit.md, sessions.md, setup/, setup.md, smolitux-ui-integration.md, snapshots.md, test_strategy.md, tools.md, troubleshooting/, ui_migration_audit.md, index.html

---

## Summary Table

| Category | Count | Action |
|----------|-------|--------|
| A — Canonical, keep | ~25 dirs/modules | Keep as-is |
| B — Migrate then delete | 1 item: api_route decorator; 5 legacy functions in services/core.py | Inline api_route into api_gateway, remove legacy functions |
| C — Delete (code) | agents/, legacy runtime/, archive/, sdk/, training/, managers/, monitoring/, integrations/, benchmarks/, datastores/, security/, server/, tools/, api/, config/, mcp/, interfaces/mcp_v1/, ~40 core/*.py legacy files, ~9 services/ subdirs, ~30 old tests dirs, ~15 old scripts | Delete |
| D — Delete (docs/artefacts) | ~100+ old docs, PDFs, compose files, old CI workflows, root files | Delete |
