# Model Context Protocol Integration

Die historischen MCP-HTTP-Pfade unter `agentnn/mcp/*` sind `legacy (disabled)` und gehoeren nicht zum canonical runtime stack.

## Aktueller Status

- `GET /v1/mcp/ping` bleibt nur als minimale Erreichbarkeitsprobe erhalten.
- Die historischen Execute-, Context-, Session-, Agent- und Tool-Endpunkte liefern bewusst `410 Gone`.
- Der canonical runtime stack ist `services/*`; die Referenzentscheidung steht in [CANONICAL_RUNTIME_STACK.md](architecture/CANONICAL_RUNTIME_STACK.md).

## Warum deaktiviert

- Der gehaertete Core und die produktive Ausfuehrung liegen in `services/core.py` und `services/*`.
- Ein zweiter aktiver MCP-Runtime-Pfad wuerde parallele Execution- und Bypass-Pfade offen halten.
- Historische generische MCP-Proxies sind bewusst stillgelegt.

## Canonical Ersatz

- Tool-Ausfuehrung: `services/core.py`
- Dispatcher/Registry-Laufzeit: `services/task_dispatcher`, `services/agent_registry`
- Produktiver Compose-Start: `docker-compose.yml`
