# Phase R — Sources and Scope

**Date:** 2026-04-12
**Branch:** `codex/phaseR-historical-re-review`
**Purpose:** Document which historical sources were analyzed, why they are relevant, and which time periods are decisive.

---

## 1. Analyzed Sources

### 1.1 Git History

The repository has a full linear history from the initial commit (`0ac1788a`) to the current branch tip on `codex/setup-one-liner-bootstrap`. The decisive reference points are:

| Commit / Range | Label | Significance |
|---|---|---|
| `0ac1788a` – `b77c3034` | **Iteration 0–1** | Initial commit, base functionality, stabilization |
| `fdcdb96f` – `44ba36cf` | **Iteration 2–3** | Agent selection, NN integration, local LLM integration |
| `e8b1155d` – `a8887761` | **Iteration 4–6** | Domain knowledge, agent creation/improvement, monitoring, A/B testing, enhanced training |
| `d809b366` – `489c0ab4` | **v1.0.0 fullstack** | v1.0.0 full-stack release with start scripts |
| `c2b4579d` | **Canonical pivot** | Establish canonical services-based runtime, disable legacy MCP stack |
| `0ee65ae5` – `4fdbb2c3` | **Phase 1** (adminbot) | AdminBot v2 integration |
| `54c3b92a` – `07fb16ba` | **Phases 2b–L** | MCP v1 server, MCP v2, canonical runtime, adapters, learning, governance, audit, orchestration, approval |
| `8e491ce` | **Phase M** | Control plane evolution (React UI) |
| `160fed1a` – `ef7dbdea` | **Phase N** | Persistent state (SQLite) |
| `157b6bbf` | **Phase O** | Canonicalization cleanup — delete ~200 legacy dirs/files, 1133 files changed |
| `66af8f11` – `1dade0e4` | **Post-Phase O** | Naming, setup, onboarding |

### 1.2 Branches Analyzed

All branches reachable from `git branch -a` were reviewed. Decisive branches:

**Canonical feature branches (completed, merged into main):**
- `codex/phase1-adminbot-v2-integration`
- `codex/phase2-canonical-runtime` / `codex/phase2b-mcp-v1-server` / `codex/phase3-mcp-v1-integration`
- `codex/phaseA-agent-model-flowise-interop`
- `codex/phaseB-decision-layer-neural-policy`
- `codex/phaseC-execution-layer-agent-creation`
- `codex/phaseD-learning-system` / `codex/phaseD-learning-system-fix`
- `codex/phaseE-stabilization-release-rename`
- `codex/phaseF1-native-dev-code-adapters` / `codex/phaseF2-workflow-adapter-layer`
- `codex/phaseH-multi-agent-orchestration`
- `codex/phaseI-hitl-approval-layer`
- `codex/phaseJ-policy-governance-layer`
- `codex/phaseK-audit-explainability-trace-layer`
- `codex/phaseL-mcp-v2-interface`
- `codex/phaseM-control-plane-evolution`
- `codex/phaseN-persistent-state`
- `codex/phaseO-canonicalization-cleanup`

**Remote experimental branches (not merged, represent abandoned or exploratory work):**
- `remotes/origin/codex/add-peer-rating-and-reputation-system`
- `remotes/origin/codex/add-user-management-system`
- `remotes/origin/codex/aktiviere-dynamisches-routing-mit-meta-learning`
- `remotes/origin/codex/aktiviere-openhands-integration-produktiv`
- `remotes/origin/codex/analysiere-abrain-architektur-und-dokumentiere-defizite`
- `remotes/origin/codex/api-freeze-und-versionierung-vorbereiten`
- `remotes/origin/codex/complete-n8n-and-abrain-integration`
- Various short-lived `codex/analysiere-*` / `codex/erstelle-*` / `codex/behebe-*` branches

### 1.3 Deleted Directories (Phase O cleanup — commit `157b6bbf`)

The Phase O commit deleted 1133 files and ~200 directories. Key deleted top-level directories:

| Directory | Content | LOC deleted (approx.) |
|---|---|---|
| `agents/` | SupervisorAgent, ChatbotAgent, AgentFactory, AgentGenerator, AgentImprover, AgentCreator, AgenticWorker, OpenHandsAgent, SoftwareDevAgent, DomainKnowledgeManager, AgentCommunicationHub | ~3,800 |
| `legacy-runtime/` | CLI runtime: auth, catalog, context/context_map, mcp (client, gateway, server, ws), prompting, reasoning (ContextReasoner, ToolVoteSelector), session (SessionManager, SessionOrchestrator), storage (ContextStore, SnapshotStore) | ~700 |
| `managers/` | ABTestingManager, AdaptiveLearningManager, AgentManager, AgentOptimizer, CacheManager, CommunicationManager, DeploymentManager, DomainKnowledgeManager, EnhancedAgentManager, EvaluationManager, FaultToleranceManager, GPUManager, HybridMatcher, KnowledgeManager, MetaLearner, ModelManager, ModelRegistry, MonitoringSystem, NNManager, PerformanceManager, SecurityManager, SpecializedLLMManager, SystemManager | ~2,500 |
| `training/` | AgentSelectorModel, DataLogger, FederatedLearning, ReinforcementLearning, Trainer | ~1,000 |
| `monitoring/` | Python monitoring dashboard + React TSX dashboard (`agen-nn_dashboard.tsx`), Grafana config, system_monitor.py | ~500 |
| `sdk/` | SDK CLI, python_agent_nn client, nn_models client, templates | ~600 |
| `integrations/` | flowise-legacy-runtime plugin, flowise-nodes, n8n-legacy-runtime | ~400 |
| `core/` (legacy flat files) | 35 flat .py files: access_control, agent_bus, agent_evolution, coalitions, crypto, delegation, dispatch_queue, feedback_loop, governance, levels, llm_providers (5 files), matching_engine, memory_store, missions, privacy, reputation, rewards, roles, routing, self_reflection, session_store, skill_matcher, skills, teams, training, trust_circle, trust_evaluator, trust_network, voting | ~2,000 |
| `services/` (9 subdirs) | agent_coordinator, agent_registry, agent_worker, coalition_manager, llm_gateway, session_manager, task_dispatcher, user_manager, vector_store | ~1,500 |
| `mcp/` | Old MCP v1 microservice package (8 sub-services) | ~800 |
| `utils/` | logging_util (MLflow/torch/JSON), api_utils, agent_descriptions, document_manager, flowise helper, knowledge_base, prompts/prompts_v2, optional_torch | ~1,900 |
| `security/` | input_filter.py | ~100 |
| `tools/` (root) | generate_flowise_nodes, generate_flowise_plugin, package_plugin, validate_plugin_manifest, cli_docgen, registry | ~600 |
| `archive/` | ui_legacy (legacy_frontend, monitoring_dashboard), example/sample agents | ~400 |

**Also deleted:**
- ~80 legacy test files
- ~100 old documentation files (BenutzerHandbuch, Wiki, deployment, api, cli docs, etc.)
- All Docker/Compose files, Dockerfiles
- All legacy CI workflows (6 workflows)
- All legacy shell scripts (~30 .sh files)
- Legacy PDFs, planning documents

### 1.4 Surviving Documentation (Still Present)

- `docs/architecture/` — 18 files covering each canonical phase
- `docs/reviews/` — 25+ phase review files (phaseD through phaseO)
- `docs/integrations/adminbot/` — 6 files (active contract)
- `ROADMAP.md` / `Roadmap.md` — historical planning docs
- PDFs: "Entwicklungsplan", "Integration von ABrain in n8n und Flowise", "Modernisierung"

---

## 2. Why These Sources Are Relevant

### Git History
Git history is the authoritative record of architectural decisions, feature additions, and deliberate removals. The commit messages are structured (feat/fix/refactor/chore) and provide explicit rationale for each change.

### Phase O as the Pivot
Phase O (`157b6bbf`) is the most significant historical event: ~60% of the codebase was deliberately deleted. The `phaseO_full_repo_inventory.md` classifies every deleted item as A/B/C/D and provides rationale. This is the primary source for understanding *what* was removed and *why*.

### Pre-Phase-O State
The `157b6bbf^` tree (the commit immediately before Phase O) preserves the full pre-cleanup state. All deleted code can be reconstructed via `git show 157b6bbf^:<path>`.

### Experimental Remote Branches
Several remote branches (never merged) represent abandoned implementations: user management, peer rating/reputation, dynamic routing with meta-learning. These represent ideas that were explored but never landed.

---

## 3. Decisive Time Periods

| Period | Date Range | What Happened |
|---|---|---|
| **Origins** | 2024 (initial commits) | Initial monolithic ABrain design, EcoSphereNetwork era |
| **Iteration 1–6** | early 2025 | Rapid feature addition: domain knowledge, agent creation, monitoring, A/B testing, LLM integration |
| **v1.0.0 Fullstack** | 2025 | Full-stack release, heavy multi-service architecture |
| **Canonical Pivot** | 2026-04-09 (`c2b4579d`) | Hard cut from microservices to canonical runtime stack |
| **Phase A–O** | 2026-04-09 – 2026-04-11 | Systematic layered build-up (decision → execution → governance → approval → audit → orchestration → MCP v2 → control plane → persistent state) |
| **Phase O** | 2026-04-11 | Mass deletion: ~200 dirs/files, 60% of codebase removed |
| **Post-Phase O** | 2026-04-12 | Naming cleanup, one-liner setup, onboarding |

---

## 4. Key Files for Deep Historical Reference

| File (in git history) | Path | Content |
|---|---|---|
| Deleted MetaLearner | `managers/meta_learner.py` | PyTorch nn.Module meta-learning for agent selection |
| Deleted AgentFactory | `agents/agent_factory.py` | LLM-driven agent generation from task requirements |
| Deleted AgentBus | `core/agent_bus.py` | Pub/sub message queue between agents |
| Deleted LLMProviders | `core/llm_providers/` | OpenAI, Anthropic, local GGUF, HF providers |
| Deleted VectorStore | `services/vector_store/service.py` | ChromaDB + in-memory vector store with embeddings |
| Deleted LLMGateway | `services/llm_gateway/service.py` | LLM routing/gateway with session awareness |
| Deleted Delegation | `core/delegation.py` | Agent-to-agent delegation with scoped grants |
| Deleted Coalitions | `core/coalitions.py` | Agent coalition formation with goal/leader/members |
| Deleted TrustEvaluator | `core/trust_evaluator.py` | Trust score calculation from history |
| Deleted Monitoring Dashboard | `monitoring/agen-nn_dashboard.tsx` | Rich React dashboard with mock data |
| Deleted ContextReasoner | `legacy-runtime/reasoning/context_reasoner.py` | Majority vote + tool vote reasoning |
| Deleted SessionManager (legacy-runtime) | `legacy-runtime/session/session_manager.py` | Multi-agent session with WS broadcast |
| Historical ROADMAP | `ROADMAP.md` | Full original planning list with Phases 1–5 |
