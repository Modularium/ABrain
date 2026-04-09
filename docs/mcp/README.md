# MCP in ABrain

ABrain stellt einen neuen MCP-v1-Server unter `interfaces/mcp_v1/*` bereit. Diese Schicht ist nur ein externer Interface-Layer vor dem kanonischen Core-Pfad.

## Aktueller Status

- aktiv: lokaler stdio-basierter MCP-v1-Server
- deaktiviert: historische HTTP-Pfade unter `agentnn/mcp/*`
- deaktiviert: historische Proxy-Pfade unter `mcp/plugin_agent_service/*`

## Canonical Path

`interfaces/mcp_v1/server.py` -> `services/core.py` -> `core/execution/dispatcher.py` -> `core/tools/registry.py` -> `core/tools/handlers.py`

## Wichtige Dokumente

- [MCP V1 Architektur](MCP_V1_SERVER.md)
- [MCP Server Usage](MCP_SERVER_USAGE.md)
- [Claude Desktop Beispielkonfiguration](claude_desktop_config.json)
