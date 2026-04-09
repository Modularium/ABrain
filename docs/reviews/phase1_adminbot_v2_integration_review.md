# Phase 1 AdminBot v2 Integration Review

## Geaenderter Adapterstand

- `adapters/adminbot/client.py` spricht jetzt AdminBot v2 ueber `/run/adminbot/adminbot.sock`
- das IPC-Framing wurde von newline-delimited JSON auf `u32` Length Prefix in Big-Endian plus JSON umgestellt
- `adapters/adminbot/service.py` mappt nur noch feste v2-Actions
- der Wire-Request nutzt jetzt `params` statt des inkompatiblen Felds `payload`
- alte v1-nahe Tool- und Action-Namen wurden im gehärteten Core ersetzt

## Angebundene AdminBot-v2-Actions

- `adminbot_system_status` -> `system.status`
- `adminbot_system_health` -> `system.health`
- `adminbot_service_status` -> `service.status`

## Neu registrierte Tools im gehärteten Core

- `adminbot_system_status`
- `adminbot_system_health`
- `adminbot_service_status`

## Ersetzte Altpfade und Alt-Namen

- `adminbot_get_status` wurde durch `adminbot_system_status` ersetzt
- `adminbot_get_health` wurde durch `adminbot_system_health` ersetzt
- `adminbot_get_service_status` wurde durch `adminbot_service_status` ersetzt
- alter Socket-Pfad `/var/run/smolit_adminbot.sock` wurde durch `/run/adminbot/adminbot.sock` ersetzt
- newline-delimited JSON wurde durch length-prefixed IPC ersetzt

## Identity und Korrelationsfelder

- `requested_by.type` wird intern hart auf `agent` gesetzt
- `requested_by.id` wird intern auf die stabile Adapter-ID gesetzt
- `request_id` wird pro Request neu gesetzt
- `tool_name` wird fest pro Handler gesetzt
- `dry_run` wird fest auf `false` gesetzt
- `timeout_ms` wird aus dem konfigurierten Client-Timeout abgeleitet
- aus `ToolExecutionRequest` werden `run_id` als `agent_run_id` und `correlation_id` uebernommen
- ABrain trifft weiterhin keine eigene Policy- oder Capability-Entscheidung fuer AdminBot

## Reale v2-Responseform

- Responses enthalten mindestens `request_id` und `status`
- Fehler kommen als `status = "error"` mit verschachteltem `error.code`, `error.message`, optionalen `error.details` und optionalem `error.retryable`
- ABrain mappt diese Fehler strukturtreu auf `CoreExecutionError`

## Tests

- `tests/adapters/test_adminbot_client.py`
- `tests/adapters/test_adminbot_tools.py`
- `tests/integration/test_adminbot_v2_real.py` bestaetigt gegen einen laufenden Peer den v2-Wire-Vertrag mit `params`, `dry_run`, `timeout_ms` sowie der Responseform `request_id` + `status` + `result`
- bestehende Core- und Service-Tests laufen weiter gegen den gehärteten Einstiegspfad

## Bewusst offene Follow-ups

- `adminbot_resource_snapshot` ist in dieser Phase noch nicht freigegeben
- `adminbot_journal_query` bleibt vorerst ausserhalb der produktiven Tool-Flaeche
- `adminbot_process_snapshot` bleibt vorerst ausserhalb der produktiven Tool-Flaeche
- `adminbot_service_restart` bleibt spaeterer, separat zu gateender Mutationspfad

## Fazit

ABrain integriert AdminBot v2 damit als normalen, read-only Executor-Provider ueber den gehärteten Core. Die Integrationsschicht bleibt fest verdrahtet, klein und frei von generischen Action- oder Payload-Passthroughs.
