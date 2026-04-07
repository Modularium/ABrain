# TOOL_SURFACE

## Default-Agent-Allowed

- `adminbot_get_status`
- `adminbot_get_health`
- `adminbot_get_service_status`

## Exakte Mappings

- `adminbot_get_status` -> `get_status`
- `adminbot_get_health` -> `get_health`
- `adminbot_get_service_status` -> `get_service_status`

## Bewusst ausgeschlossen

Diese Tools sind absichtlich nicht implementiert:

- `adminbot_tail_audit`
- `adminbot_restart_service`
- `adminbot_validate_policy`
- `adminbot_run_gate`

## Begründung

Die implementierte Oberfläche bleibt lesend, klein und typisiert. Es gibt keinen generischen Tool-Proxy und keine freie Aktionsweiterleitung an AdminBot.
