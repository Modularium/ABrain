# Scripts

Dieses Verzeichnis enthaelt nur noch wenige kanonische Einstiegspunkte:

- `abrain`: kanonische Bash-CLI fuer Setup, Diagnose, lokale Smokes sowie
  Developer-/Operator-Zugriffe auf Task, Plan, Approval, Trace und Agent-Katalog
- `agentnn`: duerner Legacy-Wrapper, der direkt an `abrain` delegiert
- `abrain_mcp.py`: Python-Wrapper fuer den MCP-v2-stdio-Server
- `abrain_control.py`: interne Python-Bridge fuer die neuen Control-Plane-
  Subcommands von `abrain` (kein zweiter user-facing Einstiegspunkt)
- `setup.sh`: kanonischer Bootstrap fuer `.venv`, Python-Abhaengigkeiten,
  editable Installation, API-/MCP-Smokes und den UI-Build

Der kanonische Einstieg ist `./scripts/abrain setup`.

`./scripts/abrain setup ...` delegiert direkt an `setup.sh`. Verfuegbare
gezielte Schritte fuer Wiederholung oder Diagnose sind `env`, `deps`, `cli`,
`api`, `mcp`, `ui` und `all`.

Fuer die taegliche Kerninspektion stehen jetzt additive Subcommands direkt unter
`abrain` bereit:

- `./scripts/abrain task run ...`
- `./scripts/abrain plan run ...`
- `./scripts/abrain plan list`
- `./scripts/abrain approval list|approve|reject`
- `./scripts/abrain trace list|show`
- `./scripts/abrain explain <trace_id>`
- `./scripts/abrain agent list`
- `./scripts/abrain health [--json]`

Alles andere aus frueheren Shell-Setups wurde im bereinigten Main entfernt.
