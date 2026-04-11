# Historical ABrain MCP V1 Server Usage

Hinweis: Der kanonische MCP-Pfad dieses Branches liegt unter `interfaces/mcp/*`.
Die aktuelle Referenz steht in [../guides/MCP_USAGE.md](../guides/MCP_USAGE.md).

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

## Primärer Einsatz: VS Code MCP

Der primäre lokale V1-Pfad ist VS Code MCP über stdio mit einem expliziten Interpreter oder dem installierten CLI-Entry.

Konfigurationsdatei unter Ubuntu 24:

```bash
~/.config/Code/User/mcp.json
```

Beispielkonfiguration mit stabilem CLI-Pfad:

```json
{
  "servers": {
    "abrain": {
      "type": "stdio",
      "command": "/home/dev/Agent-NN/.venv/bin/abrain-mcp-v1",
      "args": []
    }
  }
}
```

Alternative mit explizitem Python-Interpreter:

```json
{
  "servers": {
    "abrain": {
      "type": "stdio",
      "command": "/home/dev/Agent-NN/.venv/bin/python",
      "args": ["-m", "interfaces.mcp_v1.server"]
    }
  }
}
```

Wichtig:

- Beide Varianten sollen mit einem expliziten Venv-Pfad arbeiten.
- Die Modulvariante ist außerhalb des Repo-CWD nur stabil, wenn das Projekt in genau dieser `.venv` installiert wurde.
- Der CLI-Pfad ist für VS Code robuster, weil er nicht vom aktuellen Arbeitsverzeichnis abhängt.

## Installation des CLI-Entry

Für den empfohlenen Startpfad muss das Projekt in die Ziel-`venv` installiert sein:

```bash
/home/dev/Agent-NN/.venv/bin/python -m pip install -e /home/dev/Agent-NN --no-deps
```

Danach steht der historische Entry bereit unter:

```bash
/home/dev/Agent-NN/.venv/bin/abrain-mcp-v1
```

Wenn du Poetry statt `pip` nutzt, installiere das Projekt nicht mit `--no-root`, sondern als echtes Paket, damit der Console-Script-Entry erzeugt wird.

Der installierte historische CLI-Entry zeigt direkt auf `interfaces.mcp_v1.server:main`. Der kanonische Entry `abrain-mcp` zeigt in diesem Branch bereits auf `interfaces.mcp.server:main`.

## Manueller lokaler Start

Empfohlen:

```bash
/home/dev/Agent-NN/.venv/bin/abrain-mcp-v1
```

Alternative:

```bash
/home/dev/Agent-NN/.venv/bin/python -m interfaces.mcp_v1.server
```

## VS Code Ablauf

1. `mcp.json` unter `~/.config/Code/User/mcp.json` anlegen oder anpassen.
2. Den empfohlenen `abrain-mcp-v1`-Pfad oder den Python-Fallback mit absolutem Interpreter eintragen.
3. VS Code vollständig neu starten.
4. In der MCP-Ansicht prüfen, ob die vier ABrain-Tools sichtbar sind.
5. Bei Fehlern die Server-Logs in der VS-Code-Extension prüfen.

## Debug-Hinweise

- `No module named interfaces`: Das Projekt ist nicht in der gewählten `.venv` installiert oder VS Code startet mit einem anderen Interpreter.
- `command not found` fuer `abrain-mcp-v1`: Die editable Installation wurde in einer anderen `.venv` ausgefuehrt.
- Falscher Code-Stand wird geladen: ein globales `PYTHONPATH` zeigt auf einen anderen Checkout und übersteuert das installierte Paket.
- Keine Tools sichtbar: VS Code nach Änderungen an `mcp.json` komplett neu starten.
- Server startet, Tool-Calls scheitern: den Core separat mit den Standard-Pytests verifizieren.

## Claude Desktop als sekundäre Option

Claude Desktop kann denselben stdio-Server ebenfalls starten, ist in dieser Phase aber nur ein sekundaerer lokaler Client. Verwende dort fuer v1 bevorzugt den absoluten CLI-Pfad `/home/dev/Agent-NN/.venv/bin/abrain-mcp-v1`.

Typische manuelle Konfigurationsorte:

- Linux: `~/.config/Claude/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

Wenn der Pfad auf deinem System abweicht, öffne ihn direkt über Claude Desktop in den Developer-Einstellungen.

Nach dem Eintragen:

1. Claude Desktop komplett neu starten.
2. Den ABrain-MCP-Server in der Konfiguration aktiv lassen.
3. Nach dem Neustart prüfen, ob die vier Tools im MCP-UI sichtbar sind.

## Security-Hinweise

- nur feste Allowlist
- keine versteckten Parameter durch die JSON-Schemas
- kein direkter Zugriff auf Handler, Registry oder AdminBot-Client
- alle Tool-Calls laufen über `services.core.execute_tool(...)`
- Logging enthält nur `tool_name`, `correlation_id` und Ergebnisstatus
