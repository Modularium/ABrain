# USAGE

## Voraussetzungen

- lokaler Unix-Socket für AdminBot
- Standardpfad: `/var/run/smolit_adminbot.sock`
- stabile Adapter-Identität: `agentnn-adminbot-adapter`
- konfigurierbarer Timeout im Client

## Beispiel: `adminbot_get_status`

```python
from core.models import RequesterIdentity, RequesterType
from services.core import execute_tool

result = execute_tool(
    "adminbot_get_status",
    {"target": "summary"},
    requested_by=RequesterIdentity(type=RequesterType.AGENT, id="worker-dev"),
    run_id="run-123",
    correlation_id="corr-456",
)
```

## Beispiel: `adminbot_get_health`

```python
from core.models import RequesterIdentity, RequesterType
from services.core import execute_tool

result = execute_tool(
    "adminbot_get_health",
    {"include_checks": True},
    requested_by=RequesterIdentity(type=RequesterType.AGENT, id="worker-dev"),
)
```

## Beispiel: `adminbot_get_service_status`

```python
from core.models import RequesterIdentity, RequesterType
from services.core import execute_tool

result = execute_tool(
    "adminbot_get_service_status",
    {"service_name": "ssh.service", "allow_nonsystem": False},
    requested_by=RequesterIdentity(type=RequesterType.AGENT, id="worker-dev"),
)
```

## Erwartete Antworten

Erfolg:

```python
{
    "ok": True,
    "result": {...},
    "warnings": [...],  # optional
    "audit_ref": "..."  # optional
}
```

Fehler:

```python
{
    "error_code": "...",
    "message": "...",
    "details": {...},   # optional
    "audit_ref": "...", # optional
    "warnings": [...],  # optional
}
```

## Deploy-Annahmen

- ABrain führt keine lokale Privilegentscheidung für AdminBot aus
- AdminBot entscheidet, ob der Request erlaubt ist
- der Adapter ist schrittweise erweiterbar, solange neue Operationen als feste, typisierte Tools hinzugefügt werden
