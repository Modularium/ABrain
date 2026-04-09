# USAGE

## Voraussetzungen

- lokaler Unix-Socket für AdminBot
- Standardpfad: `/run/adminbot/adminbot.sock`
- IPC-Framing: `u32` Length Prefix in Big-Endian plus JSON
- stabile Adapter-Identität: `agentnn-adminbot-adapter`
- konfigurierbarer Timeout im Client
- Wire-Request nutzt `params`, nicht `payload`
- Wire-Request setzt `dry_run` fest auf `false`
- Wire-Request setzt `timeout_ms` aus dem konfigurierten Client-Timeout

## Beispiel: `adminbot_system_status`

```python
from core.models import RequesterIdentity, RequesterType
from services.core import execute_tool

result = execute_tool(
    "adminbot_system_status",
    {},
    requested_by=RequesterIdentity(type=RequesterType.AGENT, id="worker-dev"),
    run_id="run-123",
    correlation_id="corr-456",
)
```

## Beispiel: `adminbot_system_health`

```python
from core.models import RequesterIdentity, RequesterType
from services.core import execute_tool

result = execute_tool(
    "adminbot_system_health",
    {},
    requested_by=RequesterIdentity(type=RequesterType.AGENT, id="worker-dev"),
)
```

## Beispiel: `adminbot_service_status`

```python
from core.models import RequesterIdentity, RequesterType
from services.core import execute_tool

result = execute_tool(
    "adminbot_service_status",
    {"service_name": "ssh.service"},
    requested_by=RequesterIdentity(type=RequesterType.AGENT, id="worker-dev"),
)
```

## Erwartete Antworten

Erfolg:

```python
{
    "request_id": "...",
    "status": "...",
    ...  # weitere AdminBot-v2-Erfolgsfelder sind peer-abhaengig
}
```

Bei `execute_tool(...)` wird im Fehlerfall `CoreExecutionError` geworfen. Die strukturierte AdminBot-Fehlerinformation liegt dann in `exc.error`:

```python
from core.models import CoreExecutionError

try:
    execute_tool("adminbot_system_status", {})
except CoreExecutionError as exc:
    error = exc.error
    assert error.error_code == "..."
    assert error.message == "..."
    assert error.details == {...}      # optional
    assert error.details["request_id"] == "..."
    assert error.details["status"] == "error"
    assert error.details["retryable"] is False
```

## Deploy-Annahmen

- ABrain führt keine lokale Privilegentscheidung für AdminBot aus
- AdminBot entscheidet, ob der Request erlaubt ist
- der Adapter ist schrittweise erweiterbar, solange neue Operationen als feste, typisierte Tools hinzugefügt werden
- in dieser Phase bleiben `resource.snapshot`, `journal.query`, `process.snapshot` und `service.restart` bewusst außerhalb der produktiven Tool-Fläche
