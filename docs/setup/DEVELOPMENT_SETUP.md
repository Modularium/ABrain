# ABrain Development Setup

## Ziel

Diese Anleitung beschreibt den aktuellen, ehrlichen Entwicklungs- und Prüfpfad für den gehärteten ABrain-Stand. Der Arbeitsbaum und einige interne Paketpfade heißen derzeit noch `Agent-NN` bzw. `agentnn`; das ist während der Rename-Migration beabsichtigt.

Der canonical runtime stack ist `services/*`. Historische Bereiche unter `mcp/*`, `agentnn/mcp/*` und `/smolitux/*` sind `legacy (disabled)`.

## Voraussetzungen

- Python 3.10+
- `venv`
- optional: Poetry
- optional: Node.js 18+ für das Frontend

## Minimaler Prüfpfad für den aktuellen Foundations-Stand

Wenn Sie den aktuellen Foundations-Stand mit Decision-, Execution- und Learning-Layer verifizieren wollen:

```bash
cd <repo-root>
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install pydantic pytest httpx

python -m pytest -o python_files='test_*.py' \
  tests/decision \
  tests/execution \
  tests/adapters \
  tests/core \
  tests/services \
  tests/integration/test_node_export.py
```

## Vollere lokale Entwicklungsumgebung

Für breitere Arbeit am Repo:

```bash
cd <repo-root>
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Falls Poetry im Projekt bevorzugt wird:

```bash
poetry install --no-root
```

## Frontend lokal starten

```bash
cd <repo-root>/frontend/agent-ui
npm install
npm run dev
```

## Wichtige Prüfkommandos

Foundations-Tests:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/decision \
  tests/execution \
  tests/adapters \
  tests/core \
  tests/services \
  tests/integration/test_node_export.py
```

Syntaxprüfung der Foundations-Module:

```bash
.venv/bin/python -m py_compile \
  api/endpoints.py \
  server/main.py \
  services/core.py \
  core/tools/__init__.py \
  core/execution/dispatcher.py \
  core/tools/registry.py \
  core/tools/handlers.py \
  core/models/tooling.py \
  core/models/identity.py \
  core/models/errors.py \
  core/models/adminbot.py \
  core/decision/__init__.py \
  core/decision/agent_creation.py \
  core/decision/agent_descriptor.py \
  core/decision/agent_registry.py \
  core/decision/candidate_filter.py \
  core/decision/capabilities.py \
  core/decision/feature_encoder.py \
  core/decision/feedback_loop.py \
  core/decision/neural_policy.py \
  core/decision/performance_history.py \
  core/decision/planner.py \
  core/decision/routing_engine.py \
  core/decision/scoring_models.py \
  core/decision/task_intent.py \
  core/decision/learning/dataset.py \
  core/decision/learning/online_updater.py \
  core/decision/learning/persistence.py \
  core/decision/learning/reward_model.py \
  core/decision/learning/trainer.py \
  adapters/adminbot/client.py \
  adapters/adminbot/service.py \
  adapters/flowise/__init__.py \
  adapters/flowise/models.py \
  adapters/flowise/importer.py \
  adapters/flowise/exporter.py \
  core/execution/__init__.py \
  core/execution/execution_engine.py \
  core/execution/adapters/__init__.py \
  core/execution/adapters/base.py \
  core/execution/adapters/registry.py \
  core/execution/adapters/adminbot_adapter.py \
  core/execution/adapters/openhands_adapter.py \
  core/execution/adapters/claude_code_adapter.py \
  core/execution/adapters/codex_adapter.py \
  services/routing_agent/service.py
```

## Sicherheitskontext

- ABrain besitzt eine gehärtete Core-Schicht über Dispatcher, Registry und getypte Tool-Inputs.
- Der aktuelle Foundations-Release erweitert diesen Referenzpfad um kanonisches Agentenmodell, Decision Layer, Execution Layer und Learning-System.
- Der AdminBot-Adapter bleibt strikt read-only im erlaubten Scope.
- AdminBot bleibt die Sicherheitsgrenze; ABrain baut keine zweite lokale Security Engine.

## Wichtige weiterführende Dokumente

- [`PROJECT_OVERVIEW.md`](../architecture/PROJECT_OVERVIEW.md)
- [`CANONICAL_RUNTIME_STACK.md`](../architecture/CANONICAL_RUNTIME_STACK.md)
- [`CORE_REFACTOR.md`](../architecture/CORE_REFACTOR.md)
- [`AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md`](../integrations/adminbot/AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md)
- [`SECURITY_INVARIANTS.md`](../integrations/adminbot/SECURITY_INVARIANTS.md)
