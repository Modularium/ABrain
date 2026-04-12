# ABrain MCP V2 Usage

## Zweck

Der ABrain MCP-v2-Server stellt eine kleine, statische Tool-Oberflaeche ueber dem kanonischen Core bereit. Er ist capability-, policy-, approval- und trace-aware und fuehrt keine eigene Runtime-Logik aus.

Der bevorzugte Bootstrap fuer den lokalen MCP-Pfad ist:

```bash
./scripts/abrain setup
```

Wenn nur der MCP-/Entry-Point gezielt aufgefrischt werden soll, reicht auch:

```bash
./scripts/abrain setup cli
```

## Server starten

Direkt aus dem Repo-Checkout:

```bash
/home/dev/Agent-NN/.venv/bin/python -m interfaces.mcp.server
```

Alternativ ueber den Console-Entry nach einem frischen Paket-Install:

```bash
/home/dev/Agent-NN/.venv/bin/abrain-mcp
```

Der Wrapper `scripts/abrain_mcp.py` zeigt ebenfalls auf denselben v2-Server.

Wenn `abrain-mcp` auf einem alten Checkout oder einer alten editable Installation
noch auf einen veralteten Codepfad zeigt, regeneriert `./scripts/abrain setup cli`
den Entry-Point fuer den aktuellen Branchstand neu.

## Exponierte Tools

- `abrain.run_task`
- `abrain.run_plan`
- `abrain.approve`
- `abrain.reject`
- `abrain.list_pending_approvals`
- `abrain.get_trace`
- `abrain.explain`

## Beispiel: `abrain.run_task`

Request:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "abrain.run_task",
    "arguments": {
      "task_type": "system_status",
      "description": "Read current status",
      "input_data": {},
      "preferences": {}
    }
  }
}
```

Typische strukturierte Antwort:

```json
{
  "status": "success",
  "result": {
    "success": true
  },
  "trace_id": "trace-123",
  "explainability_summary": {
    "selected_agent": "adminbot-agent",
    "policy_decision": "allow",
    "reason": "selected adminbot-agent"
  },
  "warnings": []
}
```

## Beispiel: `abrain.run_plan`

Request:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "abrain.run_plan",
    "arguments": {
      "task_type": "workflow_automation",
      "description": "Run the workflow",
      "input_data": {},
      "options": {
        "allow_parallel": true
      }
    }
  }
}
```

Wenn Governance oder Approval greifen, liefert der Core einen pausierten Status statt direkter Ausfuehrung.

## Approval-Flow

1. `abrain.run_task` oder `abrain.run_plan` liefert `approval_required` bzw. `paused`.
2. Die Antwort enthaelt die `approval_id`.
3. Der Client ruft `abrain.approve` oder `abrain.reject` auf.
4. Der Core setzt den pausierten Plan reproduzierbar fort oder beendet ihn sauber.

## Trace / Explainability

- `abrain.get_trace` liefert den gespeicherten Trace mit Spans.
- `abrain.explain` liefert die Explainability-Records fuer denselben `trace_id`.

Damit koennen MCP-Clients nachtraeglich Routing-, Policy-, Approval- und Execution-Kontext inspizieren, ohne den Core zu umgehen.

## Fehlerbehandlung

- ungültige Eingaben erzeugen strukturierte JSON-RPC-Fehler
- Tool-Ausnahmen werden in strukturierte `error`-Antworten umgewandelt
- Policy-`deny` fuehrt zu einem Fehlerstatus vor Adapter-Ausfuehrung
- Approval-bedingte Pausen werden als normaler kontrollierter Status zurueckgegeben

## Grenzen von V2

- kein Streaming
- kein SSE
- kein dynamisches Tool-Loading
- keine freie Adapter-Ausfuehrung
- keine separate MCP-Runtime neben `services/core.py`

## Historischer Hinweis

Der fruehere v1-Codepfad `interfaces/mcp_v1/*` ist auf dem bereinigten Main
nicht mehr vorhanden. Historische Hinweise liegen nur noch als Dokumentation
unter `docs/mcp/`.
