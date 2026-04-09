# ABRAIN_ADMINBOT_INTEGRATION_PLAN

## Ziel

AdminBot v2 wird als externe Sicherheitsgrenze behandelt. ABrain integriert nur einen dünnen, typisierten Adapter für feste Leseoperationen.

ABrain bleibt universeller Orchestrator und Decision Layer. AdminBot ist in diesem Modell nur ein spezialisierter lokaler Executor-Provider unter mehreren.

## Platzierung im Repo

- `core/models/adminbot.py`
- `adapters/adminbot/client.py`
- `adapters/adminbot/service.py`
- `core/tools/handlers.py`
- `core/tools/registry.py`
- `core/execution/dispatcher.py`
- `services/core.py`

## Schichtenmodell

Der einzige erlaubte Pfad ist:

1. Tool-Aufruf über `services/core.py`
2. Validierung und Dispatch in `core/execution/dispatcher.py`
3. Feste Tool-Definition in `core/tools/registry.py`
4. Exakter Handler in `core/tools/handlers.py`
5. Feste Action-Zuordnung in `adapters/adminbot/service.py`
6. Lokaler Unix-Socket-IPC in `adapters/adminbot/client.py`

## AdminBot-v2-Vertrag

- Socket-Pfad: `/run/adminbot/adminbot.sock`
- Framing: `u32` Length Prefix in Big-Endian plus JSON-Payload
- produktiv freigegebene Actions in dieser Phase:
  - `system.status`
  - `system.health`
  - `service.status`
- bewusst noch nicht freigegeben:
  - `resource.snapshot`
  - `journal.query`
  - `process.snapshot`
  - `service.restart`

## Warum kein generischer Proxy

- Keine freie Action-Auswahl
- Keine freie JSON-Weitergabe vom Modell an AdminBot
- Keine zweite Security Engine in ABrain
- Keine Umgehung der AdminBot-Policy-Grenze

## Korrelation und Audit

- `run_id` und `correlation_id` werden aus `ToolExecutionRequest` übernommen
- `requested_by` wird gegenüber AdminBot immer hart auf `type="agent"` gesetzt
- Die Adapter-ID ist stabil: `agentnn-adminbot-adapter`
- `audit_ref` und `warnings` aus AdminBot-Fehlern bleiben erhalten
