# Phase S5 - CLI Debug Review

**Datum:** 2026-04-13

## 1. Welche CLI-Funktionen hinzugekommen sind

Innerhalb der bestehenden kanonischen CLI `scripts/abrain` wurden additive
Developer-/Operator-Subcommands ergaenzt:

- `abrain task run`
- `abrain plan run`
- `abrain plan list`
- `abrain approval list`
- `abrain approval approve <approval_id>`
- `abrain approval reject <approval_id>`
- `abrain trace list`
- `abrain trace show <trace_id>`
- `abrain explain <trace_id>`
- `abrain agent list`
- `abrain health`
- Optionaler JSON-Modus ueber `--json`

## 2. Wie sie an den kanonischen Kern angebunden sind

### Einstiegspunkt

- Der einzige user-facing Einstiegspunkt bleibt `scripts/abrain`.
- `scripts/agentnn` bleibt ein duennes Alias auf `scripts/abrain`.

### Interne Implementierung

- Die neuen Kommandos delegieren aus `scripts/abrain` in
  `scripts/abrain_control.py`.
- `scripts/abrain_control.py` ist **kein zweiter CLI-Einstiegspunkt**, sondern
  nur die interne Python-Bridge fuer Parsing, JSON-Ausgabe und lesbare
  Darstellung.

### Kanonische Kernanbindung

- Schreib-/Run-Pfade gehen direkt ueber `services/core.py`:
  - `run_task`
  - `run_task_plan`
  - `approve_plan_step`
  - `reject_plan_step`
- Read-/Inspect-Pfade gehen ebenfalls direkt ueber `services/core.py`:
  - `list_pending_approvals`
  - `list_recent_traces`
  - `get_trace`
  - `get_explainability`
  - `list_recent_plans`
  - `list_agent_catalog`
  - `get_control_plane_overview`

### Konsolidierung

- `api_gateway/main.py` verwendet fuer `/control-plane/overview` jetzt dieselbe
  kanonische Aggregation `services.core.get_control_plane_overview`.
- Damit nutzen CLI und API dieselbe Sicht auf Agenten, Approvals, Traces,
  Plaene und Governance.

## 3. Welche Debug-/Inspect-Pfade jetzt verfuegbar sind

- Pending approvals lesen und direkt approve/reject ausloesen
- Letzte Traces listen
- Einzelne Trace-Snapshots lesen
- Explainability eines Trace gesondert lesen
- Letzte Planlaeufe inklusive Pending-Approval-Verknuepfung sehen
- Agent-Katalog des Kerns lesen
- Health-/Overview-Sicht inklusive Governance-Metadaten und lokaler Startpfade
  fuer Setup, API und MCP

Wichtig: Es wurde **kein neues Debug-Subsystem** gebaut. Die CLI macht
bestehende kanonische Datenpfade nur besser zugaenglich.

## 4. Welche historischen DX-Luecken damit geschlossen werden

Geschlossen werden die in Phase R klar benannten Luecken:

- Kein direkter Task-/Plan-Start aus dem Terminal
- Kein ergonomischer Zugriff auf Traces
- Kein ergonomischer Zugriff auf Approvals
- Kein ergonomischer Zugriff auf den Agent-Katalog
- Kein schneller Health-/Overview-Zugang fuer Operatoren
- Zu viel Friction durch `curl`, Postman oder direkte Modulimporte

Damit wird der stabile Kern schneller nutzbar, ohne die Phase-O-Bereinigung
zurueckzudrehen.

## 5. Explizite Bestaetigung

### Keine Parallelstruktur

- Es wurde keine zweite CLI neben `scripts/abrain` gebaut.
- Es wurde kein separates Admin-Tool und kein neues Dashboard-System gebaut.
- Es wurde kein zweiter API-/MCP-/Trace-Stack eingefuehrt.

### Kein Revival alter Strukturen

- Es wurde kein `sdk/`-Revival gebaut.
- Es wurde kein `agentnn/`- oder `managers/`-Revival eingefuehrt.
- `scripts/agentnn` bleibt reine Kompatibilitaetsschicht.

### Keine Business-Logik in der CLI

- Die CLI haelt keinen eigenen State.
- Die CLI rechnet keine Approval-, Routing- oder Governance-Logik nach.
- Die CLI greift nicht direkt auf SQLite-Dateien zu.
- Die CLI delegiert an dieselben Kernfunktionen, die auch MCP und API nutzen.

## 6. Architektur-Check

1. Wurde keine zweite CLI gebaut?
   Ja. `scripts/abrain` bleibt der einzige user-facing Einstiegspunkt.
2. Wurde kein `sdk/`- oder `agentnn/`-Revival gebaut?
   Ja. Es gibt nur eine interne Bridge-Datei unter `scripts/`.
3. Wurde keine Business-Logik in die CLI verlagert?
   Ja. Die CLI parst nur Eingaben, rendert Ausgaben und delegiert an den Kern.
4. Wurden Trace/Approval/Plan/Agent nur kanonisch zugaenglich gemacht?
   Ja. Alle Pfade gehen ueber `services/core.py`.
5. Ist S5 eine wertsteigernde DX-/Operator-Schicht?
   Ja. Der stabile Kern ist nach `./scripts/abrain setup` nun direkt aus der
   kanonischen CLI nutzbar und debugbar.
