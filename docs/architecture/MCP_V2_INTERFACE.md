# ABrain MCP V2 Interface

## Rolle im System

Der MCP-v2-Server ist in ABrain nur ein duennes Interface ueber dem kanonischen Core. Er transportiert Requests von externen MCP-Clients in den bestehenden Laufzeitpfad und fuehrt keine eigene Tool-, Adapter- oder Routing-Logik aus.

## Canonical Path

```text
interfaces/mcp/server.py
  -> interfaces/mcp/tool_registry.py
  -> interfaces/mcp/handlers/*
  -> services/core.py
  -> Decision -> Governance -> Approval -> Execution -> Learning -> Audit
```

## Design-Prinzipien

- capability-first statt tool-first: exponiert werden nur kanonische Entry Points wie `abrain.run_task` oder `abrain.run_plan`
- policy-aware: jede Ausfuehrung laeuft durch denselben Governance-Pfad wie interne Aufrufe
- approval-aware: `require_approval` fuehrt zu einem pausierten Ergebnis plus `approval_id`, nicht zu direkter Adapter-Ausfuehrung
- explainability by default: jede Antwort kann `trace_id` und eine kompakte Explainability-Zusammenfassung tragen
- kein Direktzugriff auf Adapter: die MCP-Schicht ruft nur `services/core.py` auf

## Exponierte Tools

- `abrain.run_task`
- `abrain.run_plan`
- `abrain.approve`
- `abrain.reject`
- `abrain.list_pending_approvals`
- `abrain.get_trace`
- `abrain.explain`

Diese Tool-Liste ist statisch in `interfaces/mcp/tool_registry.py` hinterlegt.

## JSON-RPC / MCP V2 Verhalten

- Transport: stdio
- Protokollstil: JSON-RPC 2.0 mit MCP-aehnlichen `initialize`, `tools/list` und `tools/call` Methoden
- Input-Validierung: Pydantic-Modelle mit `extra="forbid"`
- Fehlerform: strukturierte JSON-RPC-Fehler statt Prozessabbruch

Der kanonische lokale Bootstrap fuer diesen Einstieg ist `./scripts/abrain setup cli`.
Damit wird die editable Installation aufgefrischt und der Console-Entry
`abrain-mcp` fuer denselben v2-Server neu erzeugt.

## Sicherheitsgrenzen

- kein Plugin-Loading
- keine dynamische Tool-Discovery
- keine generische Registry- oder Adapter-Exposition
- keine zweite Runtime
- kein Policy- oder Approval-Bypass

CandidateFilter bleibt weiterhin die harte Grenze vor dem NeuralPolicyModel. MCP greift erst oberhalb der vorhandenen Core-Pipeline an und ersetzt diese Sicherheitsmechanismen nicht.

## Approval-Flow

Wenn ein MCP-Aufruf zu `require_approval` fuehrt:

1. `abrain.run_task` oder `abrain.run_plan` liefert einen pausierten Status.
2. Die Antwort enthaelt die `approval_id`.
3. Der Client nutzt `abrain.approve` oder `abrain.reject`.
4. Die Fortsetzung erfolgt wieder ueber den kanonischen Resume-Pfad im Core.

## Explainability / Trace

Der MCP-v2-Server greift fuer Rueckverfolgbarkeit nur auf vorhandene Core-Funktionen zu:

- `services.core.get_trace(...)`
- `services.core.get_explainability(...)`

Dadurch bleibt Audit-/Trace-Logik zentral im Kern und wird nicht in der Interface-Schicht dupliziert.

## Nicht-Ziele von V2

- kein Streaming
- kein SSE
- kein zweiter Dispatcher
- kein Adapter-Debug-Bypass
- kein generisches Tool- oder Plugin-System
- keine komplette MCP-Spezifikation ueber den benoetigten Kernumfang hinaus

## Historische Abgrenzung

`interfaces/mcp_v1/*` wurde aus dem bereinigten Main entfernt. Historische
Kontextdokumente liegen nur noch unter `docs/mcp/`. Der kanonische MCP-Einstieg
liegt unter `interfaces/mcp/*`.
