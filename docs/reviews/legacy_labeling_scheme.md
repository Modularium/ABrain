# Legacy Labeling Scheme

Dieses Repository verwendet fuer Review- und Sicherheitskontext drei kurze
Begriffe:

## `canonical path`

Der aktive und bevorzugte Referenzpfad fuer aktuelle Runtime-, Integrations-
oder Sicherheitsfragen.

Beispiel:

- `services/core.py`
- `core/execution/dispatcher.py`
- `core/tools/*`

## `legacy (disabled)`

Ein historisch gewachsener Runtime- oder Codepfad, der noch im Repository
vorhanden ist, aber nicht mehr als aktive oder freigegebene Schnittstelle gilt.
Wenn erreichbar, soll er explizit ablehnen statt implizit weiterarbeiten.

Beispiel:

- frueherer Plugin-Agent-Proxy unter `mcp/plugin_agent_service/*`
- frueherer MCP-Tool-Proxy unter `agentnn/mcp/*`

## `historical / legacy (not active runtime path)`

Dokumentation, Indizes, Review-Berichte oder Artefakte mit historischem Wert,
die nicht als aktuelle Runtime- oder API-Vertragsquelle zu lesen sind.

Beispiel:

- historische API-Seiten fuer deaktivierte Pfade
- Review-Berichte
- historische OpenAPI-Hinweise ohne aktive Runtime-Entsprechung

## Review-Regel

- Fuer Sicherheits- und Integrationsfragen ist zuerst der `canonical path`
  maßgeblich.
- `legacy (disabled)` beschreibt vorhandene, aber absichtlich nicht aktive
  Runtime-Pfade.
- `historical / legacy (not active runtime path)` beschreibt reine Dokumentation
  oder Referenzmaterial ausserhalb des aktiven Runtime-Vertrags.
