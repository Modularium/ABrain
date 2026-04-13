# MCP V1 Review Summary

## Neuer MCP-v1-Server

Der neue Server liegt unter `interfaces/mcp_v1/server.py` und ist bewusst nicht unter den historischen Legacy-MCP-Pfaden implementiert.

## Exponierte Tools

- `list_agents`
- `adminbot_system_status`
- `adminbot_system_health`
- `adminbot_service_status`

## Mapping auf den gehärteten Core

Jeder erfolgreiche `tools/call` läuft ausschließlich über `services.core.execute_tool(...)`. Der Dispatcher übernimmt danach die normale Ausführung über feste Registry und feste Handler.

## Umgesetzte Security-Grenzen

- feste Allowlist
- kein generischer Proxy
- JSON-Schema plus Core-Validierung
- strukturierte Fehler
- JSON-Logging mit `tool_name` und `correlation_id`
- kein Remote-Transport in V1

## Alte MCP-Pfade, die nicht genutzt werden

- `legacy runtime/mcp/*`
- `mcp/plugin_agent_service/*`
- historische `/v1/mcp/*`-HTTP-Proxy-Pfade

## Hinzugefügte Tests

- `tests/mcp/test_mcp_v1_server.py`
- Valid-Call, Unknown-Tool, Invalid-Schema, Core-Pfad-Absicherung
- stdio-JSON-RPC-Simulation

## Sinnvolle Follow-ups außerhalb von V1

- weitere read-only Tools nach Review
- optional zusätzlicher Transport nach separater Sicherheitsfreigabe
- später eventuell kontrollierter `dispatch_task`
- belastbarer Rate-Limit-/Abuse-Guard
