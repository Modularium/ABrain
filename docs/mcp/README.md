# MCP in ABrain

Der kanonische MCP-Pfad dieses Branches liegt unter `interfaces/mcp/*`. Diese Schicht ist nur ein externer Interface-Layer vor dem kanonischen Core-Pfad.

## Aktueller Status

- aktiv: lokaler stdio-basierter MCP-v2-Server
- entfernt aus dem Codebestand: MCP v1 unter `interfaces/mcp_v1/*`
- deaktiviert: historische HTTP-Pfade unter `agentnn/mcp/*`
- deaktiviert: historische Proxy-Pfade unter `mcp/plugin_agent_service/*`

MCP v2 ist der einzige unterstuetzte Runtime-Entry fuer MCP.

Der bevorzugte lokale Bootstrap fuer diesen Pfad ist `./scripts/abrain setup`.

## Canonical Path

`interfaces/mcp/server.py` -> `services/core.py` -> `decision -> governance -> approval -> execution -> learning -> audit`

## Wichtige Dokumente

- [MCP V2 Architektur](../architecture/MCP_V2_INTERFACE.md)
- [Setup One-Liner Flow](../architecture/SETUP_ONE_LINER_FLOW.md)
- [Setup And Bootstrap Flow](../architecture/SETUP_AND_BOOTSTRAP_FLOW.md)
- [MCP Usage](../guides/MCP_USAGE.md)
- [Historische MCP V1 Usage](MCP_SERVER_USAGE.md)
- [VS Code MCP Beispielkonfiguration](vscode_mcp_config.json)
