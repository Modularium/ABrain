# ADMINBOT_AGENT_CONTRACT

## Grundsatz

Dieser Adapter ist ausschließlich für Agent-Nutzung ausgelegt.

- `requested_by.type` gegenüber AdminBot ist immer `agent`
- keine Human-Session-Vererbung
- keine lokale Operator-Identität als Fallback
- keine eigene Autorisierung oder Policy-Entscheidung in ABrain

## Erlaubte Inputs

### `adminbot_get_status`

- `target`: optional
- erlaubt: `daemon`, `summary`
- Default: `summary`

### `adminbot_get_health`

- `include_checks`: optional `bool`
- Default: `true`

### `adminbot_get_service_status`

- `service_name`: Pflichtfeld
- `allow_nonsystem`: optional `bool`, Default `false`
- `service_name` ist zeichenbasiert validiert und nicht frei erweiterbar

## Nicht erlaubt

- freie Actions
- freie Parameter-Mengen
- generische Metadata- oder Payload-Passthroughs
- Shell-, systemd-, D-Bus- oder polkit-Aufrufe in ABrain

## Fehlervertrag

AdminBot-Fehler werden semantisch nicht verschleiert:

- `error_code`
- `message`
- optionale `details`
- optional `audit_ref`
- optionale `warnings`

Nur reine Transport-/Protokollfehler werden lokal übersetzt:

- `ADMINBOT_UNAVAILABLE`
- `ADMINBOT_TIMEOUT`
- `ADMINBOT_PROTOCOL_ERROR`
