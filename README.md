# ABrain

ABrain ist der aktuelle Projektname für den gehärteten Multi-Agent- und Service-Stack in diesem Repository. Der sicherheitsrelevante Schwerpunkt des aktuellen Stands liegt auf einer kleinen Core-Schicht mit festem Dispatcher-/Registry-System und einem dünnen, strikt typisierten AdminBot-v2-Adapter. AdminBot wird dabei als spezialisierter Executor-Provider unter mehreren behandelt, nicht als Leitarchitektur des Repos.

Der Arbeitsbaum und einige interne Paket-, Deploy- und Repo-Slugs heißen derzeit noch `Agent-NN`, `agentnn` oder `agent-nn`. Diese technischen Identifiers bleiben in diesem Schritt bewusst erhalten, um keine Import-, Publish- oder Deployment-Regressionen auszulösen.

## Aktueller Fokus

- canonical runtime stack: `services/*`
- gehärtete Tool-Ausführung über `services/core.py`
- feste Tool-Registry in `core/tools/registry.py`
- kontrollierter Dispatcher in `core/execution/dispatcher.py`
- getypte Tool- und Identity-Modelle in `core/models/*`
- sicherer, read-only AdminBot-v2-Adapter in `adapters/adminbot/*`

Der historische `mcp/*`-Stack, `agentnn/mcp/*`-Bridges und die Smolitux-Altpfade sind nicht mehr produktiv. Sie bleiben nur als `legacy (disabled)` im Repository.

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

## Entwicklungsstatus

Für neue sicherheitsrelevante Integrationen gilt der gehärtete Core als Referenzpfad. Ältere Bereiche und historische Dokumente bleiben im Repository nur dort erhalten, wo sie für Betrieb, Migration oder Rückverfolgbarkeit noch relevant sind; sie sind nicht gleichrangig mit dem Core-/AdminBot-Pfad.

## Wichtige Dokumente

- [Projektüberblick](docs/architecture/PROJECT_OVERVIEW.md)
- [Canonical Runtime Stack](docs/architecture/CANONICAL_RUNTIME_STACK.md)
- [Core Refactor](docs/architecture/CORE_REFACTOR.md)
- [Development Setup](docs/setup/DEVELOPMENT_SETUP.md)
- [AdminBot Integration Plan](docs/integrations/adminbot/AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md)
- [AdminBot Security Invariants](docs/integrations/adminbot/SECURITY_INVARIANTS.md)
- [Rename Plan](docs/reviews/abrain_rename_plan.md)
