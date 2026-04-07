# AGENT_NN_ADMINBOT_INTEGRATION_PLAN

## Ziel

AdminBot wird als externe Sicherheitsgrenze behandelt. ABrain integriert nur einen dünnen, typisierten Adapter für feste Leseoperationen.

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
