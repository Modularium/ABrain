# Canonical Runtime Stack

## Entscheidung

Der eindeutige `canonical runtime stack` fuer ABrain ist `services/*` in Kombination mit dem gehaerteten Core unter `services/core.py` und `core/*`.

## Canonical Path

- Runtime-Services: `services/task_dispatcher`, `services/agent_registry`, `services/session_manager`, `services/vector_store`, `services/llm_gateway`, `services/routing_agent`
- Gehaertete In-Process-Referenz: `services/core.py`
- Feste Tool- und Execution-Schicht: `core/execution/dispatcher.py`, `core/tools/registry.py`, `core/tools/handlers.py`
- Produktiver Compose-Start: `docker-compose.yml`

## Warum `services/*`

- Der gehaertete Core liegt bereits im `services/*`-Umfeld und ist die sicherheitsrelevante Referenz.
- CLI- und Core-nahe Pfade nutzen bereits `services/*` statt der historischen `mcp/*`-Stubs.
- Ein zweiter produktiver Runtime-Stack wuerde den Red-Team-Befund zu Bypass-Risiken offen halten.
- Die `services/*`-Module sind strukturiert, explizit und besser an den aktuellen Core angepasst.

## Bewusst verworfene Alternativen

### `mcp/*` als produktiver Runtime-Stack

Verworfen, weil:

- dort parallele Dispatcher-/Registry-Implementierungen neben dem gehaerteten Core existieren,
- der bisherige Startpfad `mcp/*` alte Service- und Worker-Pfade produktiv hielt,
- historische MCP- und Plugin-Pfade bereits als Bypass-Risiko aufgefallen sind.

### Koexistenz von `services/*` und `mcp/*`

Bewusst nicht zugelassen. Es gibt keinen gleichrangigen zweiten Runtime-Pfad mehr.

## Legacy-Bereiche

Folgende Bereiche bleiben nur noch fuer Rueckverfolgbarkeit oder kontrollierte Abschaltung im Repo:

- `mcp/*` -> `legacy (disabled)`
- `agentnn/mcp/*` -> `legacy (disabled)`
- `api/smolitux_integration.py` und die `/smolitux/*`-Routen -> `legacy (disabled)`

Sie sind nicht Teil des produktiven Runtime-Vertrags.
