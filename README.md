# ABrain

ABrain ist der aktuelle Projektname für den gehärteten Multi-Agent- und Service-Stack in diesem Repository. Der sicherheitsrelevante Schwerpunkt des aktuellen Stands liegt auf einer kleinen Core-Schicht mit festem Dispatcher-/Registry-System und einem dünnen, strikt typisierten AdminBot-v2-Adapter. AdminBot wird dabei als spezialisierter Executor-Provider unter mehreren behandelt, nicht als Leitarchitektur des Repos.

Der Arbeitsbaum und einige interne Paket-, Deploy- und Repo-Slugs heißen derzeit noch `Agent-NN`, `agentnn` oder `agent-nn`. Diese technischen Identifiers bleiben in diesem Schritt bewusst erhalten, um keine Import-, Publish- oder Deployment-Regressionen auszulösen.

## Aktueller Fokus

- canonical runtime stack: `services/*`
- gehärtete Tool-Ausführung über `services/core.py`
- feste Tool-Registry in `core/tools/registry.py`
- kontrollierter Dispatcher in `core/execution/dispatcher.py`
- getypte Tool- und Identity-Modelle in `core/models/*`
- kanonisches Agentenmodell in `core/decision/*`
- kanonischer Decision Layer mit Planner, Candidate Filtering und verpflichtendem NeuralPolicyModel
- trainierbares Learning-System fuer das NeuralPolicyModel in `core/decision/learning/*`
- getrennter Execution Layer mit statischen Adaptern, Agent Creation und Feedback Loop
- native Dev-/Code-Agent-Adapter fuer OpenHands, Codex und Claude Code im Execution Layer
- Workflow-Adapter-Layer fuer n8n und Flowise im Execution Layer
- Multi-Agent-Orchestrierung mit PlanBuilder, Step-Level-Routing und strukturierter Aggregation
- HITL-/Approval-Layer mit Pause, Approve, Reject und Resume fuer sensible PlanSteps
- verpflichtender Governance-Layer mit deterministischem Policy-Check vor jeder Execution
- Branch-Vorschau fuer einen Audit-/Explainability-/Trace-Layer mit internen Traces, Spans und Explainability-Records
- sicherer, read-only AdminBot-v2-Adapter in `adapters/adminbot/*`
- MCP-v1-Interface-Schicht in `interfaces/mcp_v1/*`
- Flowise-Interop-Layer in `adapters/flowise/*`

Der historische `mcp/*`-Stack, `agentnn/mcp/*`-Bridges und die Smolitux-Altpfade sind nicht mehr produktiv. Sie bleiben nur als `legacy (disabled)` im Repository.

Aktueller Foundations-Release-Stand: `v1.1.0`.

## Wichtige Komponenten

### Hardened Core

- `services/core.py`
- `core/execution/dispatcher.py`
- `core/tools/registry.py`
- `core/tools/handlers.py`
- `core/models/tooling.py`
- `core/models/identity.py`
- `core/models/errors.py`

### AdminBot-Adapter

- `adapters/adminbot/client.py`
- `adapters/adminbot/service.py`
- `core/models/adminbot.py`
- `docs/integrations/adminbot/*`

### Agent Model / Flowise Interop

- `core/decision/*`
- `adapters/flowise/*`
- `docs/architecture/AGENT_MODEL_AND_FLOWISE_INTEROP.md`

Der Flowise-Pfad ist bewusst nur ein Import-/Export- und UI-Layer. Er ist weder Teil des Decision Layers noch Teil des Execution Layers und definiert keine interne Wahrheit.

### Decision Layer

- `core/decision/planner.py`
- `core/decision/candidate_filter.py`
- `core/decision/neural_policy.py`
- `core/decision/routing_engine.py`
- `docs/architecture/DECISION_LAYER_AND_NEURAL_POLICY.md`

### Execution Layer

- `core/execution/adapters/*`
- `core/execution/execution_engine.py`
- `core/decision/agent_creation.py`
- `core/decision/feedback_loop.py`
- `docs/architecture/EXECUTION_LAYER_AND_AGENT_CREATION.md`
- `docs/architecture/NATIVE_DEV_AGENT_ADAPTERS.md`
- `docs/architecture/WORKFLOW_ADAPTER_LAYER.md`

OpenHands, Codex, Claude Code, n8n und Flowise werden dabei nur als kontrollierte `ExecutionAdapter` eingebunden. Sie sind nicht Teil der internen Wahrheit und ersetzen weder Decision Layer noch gehärteten Core.

### Workflow Adapter Layer

- `core/execution/adapters/n8n_adapter.py`
- `core/execution/adapters/flowise_adapter.py`
- `adapters/flowise/*`
- `docs/architecture/WORKFLOW_ADAPTER_LAYER.md`

n8n wird in F2 als kontrollierter Workflow-Executor angesprochen. Flowise bleibt primaer Interop-/UI-Layer und ist nur zusaetzlich als kleiner, strikt begrenzter Execution-Adapter verfuegbar. Alte Integrations- und Plugin-Reste unter `integrations/*` sind nicht der kanonische Runtime-Pfad.

### Multi-Agent Orchestration

- `core/decision/plan_models.py`
- `core/decision/plan_builder.py`
- `core/orchestration/*`
- `services/core.py` mit `run_task_plan(...)`
- `docs/architecture/MULTI_AGENT_ORCHESTRATION.md`

ABrain kann Aufgaben damit in mehrere kontrollierte Schritte zerlegen, pro Schritt erneut den kanonischen Routing-Pfad anwenden, Ergebnisse aggregieren und Feedback pro Schritt erfassen. Das ist bewusst keine freie Schwarm-Architektur und keine zweite Runtime.

### HITL / Approval Layer

- `core/approval/*`
- `core/orchestration/resume.py`
- `docs/architecture/HITL_AND_APPROVAL_LAYER.md`

Der Approval-Layer liegt in diesem Branch oberhalb des bestehenden Routing-/Execution-Pfads. Er pausiert sensible Schritte strukturiert, erzeugt serialisierbare `ApprovalRequest`s und setzt einen Plan nach `approve` oder `reject` reproduzierbar fort. Er ersetzt weder CandidateFilter noch adapterinterne Permission-Mechaniken.

### Governance Layer

- `core/governance/*`
- `docs/architecture/GOVERNANCE_LAYER.md`

Der Governance-Layer erzwingt auf `main` deterministische Runtime-Policies nach Routing und vor Execution. Er kann Aktionen erlauben, blockieren oder in denselben Approval-Pfad ueberfuehren. CandidateFilter bleibt dabei die harte Sicherheitsgrenze vor dem NN; Governance ist eine zusaetzliche Enforcement-Schicht fuer die konkret ausgewaehlte Aktion.

### Audit / Explainability Layer

- `core/audit/*`
- `docs/architecture/AUDIT_AND_EXPLAINABILITY_LAYER.md`

Der Audit-/Trace-Layer liegt in diesem Branch als naechste kleine Kernschicht oberhalb des bestehenden Stacks. Er fuehrt interne Traces, Spans und Explainability-Records fuer Routing, Governance, Approval, Execution und Learning ein. Er ist bewusst best-effort, ersetzt keine Sicherheitsgrenzen und fuegt keine zweite Runtime hinzu.

### Learning System

- `core/decision/learning/dataset.py`
- `core/decision/learning/reward_model.py`
- `core/decision/learning/online_updater.py`
- `core/decision/learning/trainer.py`
- `core/decision/learning/persistence.py`

### MCP V1 Interface

- `interfaces/mcp_v1/server.py`
- `scripts/abrain_mcp.py`
- `docs/mcp/*`

### Weitere Bereiche

- `server/main.py` und `api/` für REST-/Bridge-Einstiege
- `sdk/` für CLI und SDK
- `frontend/agent-ui` für die React-Oberfläche
- `monitoring/` für Monitoring-Assets und Zusatz-UI

## Quick Start

### Minimaler Prüfpfad für den gehärteten Stand

```bash
cd <repo-root>
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install pydantic pytest

python -m pytest -o python_files='test_*.py' \
  tests/adapters/test_adminbot_client.py \
  tests/adapters/test_adminbot_tools.py \
  tests/core/test_execution_dispatcher.py \
  tests/core/test_tool_registry.py \
  tests/services/test_core.py
```

### Breitere lokale Entwicklungsumgebung

```bash
cd <repo-root>
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optional mit Poetry:

```bash
poetry install --no-root
```

### Frontend lokal starten

```bash
cd <repo-root>/frontend/agent-ui
npm install
npm run dev
```

## Test- und Verifikationskommandos

Gezielte Kern- und Adapter-Tests:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/adapters/test_adminbot_client.py \
  tests/adapters/test_adminbot_tools.py \
  tests/core/test_execution_dispatcher.py \
  tests/core/test_tool_registry.py \
  tests/services/test_core.py
```

Syntaxprüfung der gehärteten Module:

```bash
.venv/bin/python -m py_compile \
  api/endpoints.py \
  server/main.py \
  services/core.py \
  services/__init__.py \
  sdk/cli/commands/agent.py \
  core/__init__.py \
  core/tools/__init__.py \
  core/agents/runtime.py \
  core/execution/dispatcher.py \
  core/models/adminbot.py \
  core/models/errors.py \
  core/models/identity.py \
  core/models/tooling.py \
  core/tools/registry.py \
  core/tools/handlers.py \
  adapters/adminbot/client.py \
  adapters/adminbot/service.py
```

## Sicherheitshinweise

- ABrain führt AdminBot nicht generisch fern.
- Der AdminBot-v2-Adapter bietet nur feste, typisierte read-only Tools.
- AdminBot bleibt die Sicherheitsgrenze.
- Der gehärtete Core darf nicht durch direkte Legacy-Aufrufe umgangen werden.
- MCP v1 bleibt nur eine externe Protokollschicht vor dem kanonischen Core-Pfad.

## Entwicklungsstatus

Für neue sicherheitsrelevante Integrationen gilt der gehärtete Core als Referenzpfad. Ältere Bereiche und historische Dokumente bleiben im Repository nur dort erhalten, wo sie für Betrieb, Migration oder Rückverfolgbarkeit noch relevant sind; sie sind nicht gleichrangig mit dem Core-/AdminBot-Pfad.

Der aktuelle Release-Scope auf `main` umfasst den Foundations-Stack plus Multi-Agent-Orchestrierung, HITL-/Approval-Layer und Governance-Layer. Der Audit-/Explainability-/Trace-Layer liegt in diesem Branch als Review-/Merge-Kandidat vor und ist noch nicht Teil von `main` oder des Releases `v1.1.0`. Breite MCP-Expansion, externe Observability-Backends und weiter vertiefte Spezialadapter sind ebenfalls noch nicht Teil dieses Releases.

## Wichtige Dokumente

- [Projektüberblick](docs/architecture/PROJECT_OVERVIEW.md)
- [Canonical Runtime Stack](docs/architecture/CANONICAL_RUNTIME_STACK.md)
- [Agent Model And Flowise Interop](docs/architecture/AGENT_MODEL_AND_FLOWISE_INTEROP.md)
- [Decision Layer And Neural Policy](docs/architecture/DECISION_LAYER_AND_NEURAL_POLICY.md)
- [Execution Layer And Agent Creation](docs/architecture/EXECUTION_LAYER_AND_AGENT_CREATION.md)
- [Native Dev Agent Adapters](docs/architecture/NATIVE_DEV_AGENT_ADAPTERS.md)
- [Workflow Adapter Layer](docs/architecture/WORKFLOW_ADAPTER_LAYER.md)
- [Multi-Agent Orchestration](docs/architecture/MULTI_AGENT_ORCHESTRATION.md)
- [HITL And Approval Layer](docs/architecture/HITL_AND_APPROVAL_LAYER.md)
- [Governance Layer](docs/architecture/GOVERNANCE_LAYER.md)
- [Audit And Explainability Layer](docs/architecture/AUDIT_AND_EXPLAINABILITY_LAYER.md)
- [Foundations Release Scope](docs/releases/FOUNDATIONS_RELEASE_SCOPE.md)
- [Foundations Release Notes](docs/releases/RELEASE_NOTES_FOUNDATIONS.md)
- [MCP Architektur](docs/architecture/MCP_V1_SERVER.md)
- [MCP Usage](docs/mcp/MCP_SERVER_USAGE.md)
- [Core Refactor](docs/architecture/CORE_REFACTOR.md)
- [Development Setup](docs/setup/DEVELOPMENT_SETUP.md)
- [AdminBot Integration Plan](docs/integrations/adminbot/AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md)
- [AdminBot Security Invariants](docs/integrations/adminbot/SECURITY_INVARIANTS.md)
- [Rename Plan](docs/reviews/abrain_rename_plan.md)
- [Rename And Release Audit](docs/reviews/repo_rename_and_release_audit.md)
