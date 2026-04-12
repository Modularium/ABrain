# Scripts

Dieses Verzeichnis enthaelt nur noch wenige kanonische Einstiegspunkte:

- `abrain`: kanonische Bash-CLI fuer Diagnose, Konfiguration und lokale Smokes
- `agentnn`: duerner Legacy-Wrapper, der direkt an `abrain` delegiert
- `abrain_mcp.py`: Python-Wrapper fuer den MCP-v2-stdio-Server
- `setup.sh`: kanonischer Bootstrap fuer `.venv`, Python-Abhaengigkeiten,
  editable Installation, API-/MCP-Smokes und den UI-Build

Der kanonische Einstieg ist `./scripts/abrain setup`.

`./scripts/abrain setup ...` delegiert direkt an `setup.sh`. Verfuegbare
gezielte Schritte fuer Wiederholung oder Diagnose sind `env`, `deps`, `cli`,
`api`, `mcp`, `ui` und `all`.

Alles andere aus frueheren Shell-Setups wurde im bereinigten Main entfernt.
