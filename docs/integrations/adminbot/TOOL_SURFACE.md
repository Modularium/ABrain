# TOOL_SURFACE

## Default-Agent-Allowed

- `adminbot_system_status`
- `adminbot_system_health`
- `adminbot_service_status`

## Exakte Mappings

- `adminbot_system_status` -> `system.status`
- `adminbot_system_health` -> `system.health`
- `adminbot_service_status` -> `service.status`

## Bewusst ausgeschlossen

Diese Tools sind absichtlich nicht implementiert:

- `adminbot_resource_snapshot`
- `adminbot_journal_query`
- `adminbot_process_snapshot`
- `adminbot_service_restart`

## Begründung

Die implementierte Oberfläche bleibt lesend, klein und typisiert. Es gibt keinen generischen Tool-Proxy und keine freie Aktionsweiterleitung an AdminBot.
