# ABrain MCP V1 Server Usage

## Zweck

Der ABrain MCP v1 Server exponiert genau vier feste Tools für lokale MCP-Clients. Er ist nur eine Protokollschicht vor `services/core.execute_tool(...)`.

## Exponierte Tools

- `list_agents`
- `adminbot_system_status`
- `adminbot_system_health`
- `adminbot_service_status`

## Nicht exponiert

- `dispatch_task`
- generische Tool-Ausführung
- freie JSON-Weitergabe
- mutierende AdminBot-Operationen
- historische MCP-/Plugin-Proxies

## Lokaler Start

Direkt aus dem Repo:

```bash
cd /home/dev/Agent-NN
.venv/bin/python -m interfaces.mcp_v1.server
```

Über den CLI-Wrapper:

```bash
abrain-mcp
```

## Claude Desktop

Die Beispielkonfiguration liegt in [claude_desktop_config.json](claude_desktop_config.json).

Typische manuelle Konfigurationsorte:

- Linux: `~/.config/Claude/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

Wenn der Pfad auf deinem System abweicht, öffne ihn direkt über Claude Desktop in den Developer-Einstellungen.

Nach dem Eintragen:

1. Claude Desktop komplett neu starten.
2. Den ABrain-MCP-Server in der Konfiguration aktiv lassen.
3. Nach dem Neustart prüfen, ob die vier Tools im MCP-UI sichtbar sind.

Hinweis:
Anthropic empfiehlt aktuell für lokale MCP-Server zunehmend Desktop Extensions. Die hier hinterlegte JSON-Konfiguration ist für den manuellen lokalen Dev-Start gedacht.

## Security-Hinweise

- nur feste Allowlist
- keine versteckten Parameter durch die JSON-Schemas
- kein direkter Zugriff auf Handler, Registry oder AdminBot-Client
- alle Tool-Calls laufen über `services.core.execute_tool(...)`
- Logging enthält nur `tool_name`, `correlation_id` und Ergebnisstatus
