# ABrain Development Setup

## Ziel

Diese Anleitung beschreibt den aktuellen, ehrlichen Entwicklungs- und Prüfpfad für den gehärteten ABrain-Stand. Der Arbeitsbaum und einige interne Paketpfade heißen derzeit noch `Agent-NN` bzw. `agentnn`; das ist während der Rename-Migration beabsichtigt.

Der canonical runtime stack ist `services/*`. Historische Bereiche unter `mcp/*`, `agentnn/mcp/*` und `/smolitux/*` sind `legacy (disabled)`.

## Voraussetzungen

- Python 3.10+
- `venv`
- optional: Poetry
- optional: Node.js 18+ für das Frontend

## Minimaler Prüfpfad für den gehärteten Core

Wenn Sie nur den stabilisierten Core und den AdminBot-Adapter verifizieren wollen:

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

Gezielte Kern- und Adapter-Tests:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/adapters/test_adminbot_client.py \
  tests/adapters/test_adminbot_tools.py \
  tests/core/test_execution_dispatcher.py \
  tests/core/test_tool_registry.py \
  tests/services/test_core.py
```

Syntaxprüfung der gehärteten Kernmodule:

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
  adapters/adminbot/client.py \
  adapters/adminbot/service.py
```

## Sicherheitskontext

- ABrain besitzt eine gehärtete Core-Schicht über Dispatcher, Registry und getypte Tool-Inputs.
- Der AdminBot-Adapter bleibt strikt read-only im erlaubten Scope.
- AdminBot bleibt die Sicherheitsgrenze; ABrain baut keine zweite lokale Security Engine.

## Wichtige weiterführende Dokumente

- [`PROJECT_OVERVIEW.md`](../architecture/PROJECT_OVERVIEW.md)
- [`CANONICAL_RUNTIME_STACK.md`](../architecture/CANONICAL_RUNTIME_STACK.md)
- [`CORE_REFACTOR.md`](../architecture/CORE_REFACTOR.md)
- [`AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md`](../integrations/adminbot/AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md)
- [`SECURITY_INVARIANTS.md`](../integrations/adminbot/SECURITY_INVARIANTS.md)
