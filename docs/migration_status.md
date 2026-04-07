# Migration Status

> Status: Historischer Snapshot. Diese Tabelle dokumentiert ältere Migrationsschritte und ist nicht der maßgebliche Architekturstatus für den gehärteten ABrain-Core.

Altmodul → Neues Modul / Status

- `api/server.py` → `api_gateway/main.py` / ✓
- `cli/*` → `sdk/cli/main.py` / ✓
- `services/critic_agent` → `services/agent_worker/demo_agents/critic_agent.py` / ✓
- `nn_models/deprecated` → archived / ✗
