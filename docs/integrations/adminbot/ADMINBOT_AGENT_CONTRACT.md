# ADMINBOT_AGENT_CONTRACT

## Grundsatz

Dieser Adapter ist ausschließlich für Agent-Nutzung ausgelegt und spricht das AdminBot-v2-IPC-Protokoll.

- `requested_by.type` gegenüber AdminBot ist immer `agent`
- keine Human-Session-Vererbung
- keine lokale Operator-Identität als Fallback
- keine eigene Autorisierung oder Policy-Entscheidung in ABrain
- Socket-Pfad: `/run/adminbot/adminbot.sock`
- Framing: `u32` Length Prefix in Big-Endian plus JSON
- Request-Felder: `version`, `request_id`, optional `correlation_id`, `requested_by`, `tool_name`, optional `agent_run_id`, `action`, `params`, `dry_run`, `timeout_ms`

## Erlaubte Inputs

### `adminbot_system_status`

- kein Tool-Payload-Feld
- `params` ist leer
- keine freien Filter oder Targets

### `adminbot_system_health`

- kein Tool-Payload-Feld
- `params` ist leer
- keine freien Check-Parameter

### `adminbot_service_status`

- `service_name`: Pflichtfeld
- `service_name` liegt unter `params.service_name`
- `service_name` ist zeichenbasiert validiert und nicht frei erweiterbar

## Feste Action-Mappings

- `adminbot_system_status` -> `system.status`
- `adminbot_system_health` -> `system.health`
- `adminbot_service_status` -> `service.status`

## Nicht erlaubt

- freie Actions
- freie Parameter-Mengen
- generische Metadata- oder Payload-Passthroughs
- Shell-, systemd-, D-Bus- oder polkit-Aufrufe in ABrain

## Fehlervertrag

AdminBot-v2-Antworten enthalten mindestens `request_id` und `status`.

Fehlerantworten enthalten unter `error` mindestens:

- `code`
- `message`
- optionale `details`
- optional `retryable`

ABrain hebt diese Fehler als `CoreExecutionError` an und übernimmt `code`, `message` und `details` semantisch direkt. `request_id`, `status` und `retryable` bleiben in `details` erhalten.

Nur reine Transport-/Protokollfehler werden lokal übersetzt:

- `ADMINBOT_UNAVAILABLE`
- `ADMINBOT_TIMEOUT`
- `ADMINBOT_PROTOCOL_ERROR`
