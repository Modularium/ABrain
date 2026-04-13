# Phase S5 - CLI Inventory und DX-Luecken

**Datum:** 2026-04-13

## 1. Welche CLI-Funktionen heute schon existieren

### Kanonische Einstiegspunkte

- `scripts/abrain` ist bereits die kanonische Bash-CLI.
- `scripts/abrain` ist nur ein duennes Kompatibilitaets-Wrapper-Skript, das
  direkt an `scripts/abrain` delegiert.
- `scripts/setup.sh` ist der kanonische Bootstrap fuer `.venv`, Dependencies,
  editable Install, API-/MCP-Smokes und UI-Build.
- `scripts/abrain_mcp.py` ist nur ein Wrapper fuer den MCP-v2-stdio-Server.
- `pyproject.toml` definiert genau einen Console-Entry-Point: `abrain-mcp`.
  Es gibt keinen zweiten Python-CLI-Einstiegspunkt fuer den operativen Kern.

### Bereits vorhandene `abrain`-Kommandos

- Setup und Konfiguration: `setup`, `config`
- Operations: `start`, `stop`, `restart`, `logs`, `deploy`
- Diagnose und Wartung: `status`, `validate`, `doctor`, `repair`, `test`, `clean`
- Allgemein: `version`, `help`

### Bereits vorhandene Kernpfade ausserhalb der CLI

- `services/core.py` bietet bereits kanonische Run-, Approval-, Trace-, Plan-
  und Agent-Helper.
- `api_gateway/main.py` exponiert diese Kernpfade bereits unter
  `/control-plane/*`.
- `interfaces/mcp/server.py` exponiert denselben Kern fuer MCP v2.

## 2. Welche historischen DX-Luecken R/R2 identifiziert haben

### Aus Phase R

`docs/reviews/phaseR/phaseR_historical_comparison_cli_setup.md` und
`docs/reviews/phaseR/phaseR_lost_value_analysis.md` benennen konsistent:

- Es fehlt ein Developer-CLI fuer `task run`, `plan run`, `agent list`,
  `trace list` und `approval list`.
- Debugging ist unnoetig langsam, weil Entwickler fuer Kernpfade auf
  `curl`/REST oder direkte Modulaufrufe ausweichen muessen.
- `abrain status` ist vorhanden, aber nicht als reichhaltige
  Kern-/Control-Plane-Sicht ausgepraegt.

`docs/reviews/phaseR/phaseR_final_assessment.md` bewertet genau diese
Developer-CLI als hoch priorisierte Rueckgewinnung, aber ausdruecklich ohne
Rueckfall in historische Parallelstrukturen.

### Aus Phase R2

Die R2-Analysen bestaetigen, dass kleine read-only oder control-plane-nahe
CLI-Erweiterungen sinnvoll sind, solange sie nicht in ein `managers/`- oder
zweites Runtime-System kippen:

- `phaseR2_managers_final_assessment.md`: Ein leichter Agent-Health-Monitor als
  CLI/Ops-Tool ist architektonisch vertretbar.
- `phaseR2_managers_reimplementation_candidates.md`: ein CLI-basierter
  `health-check` ist als read-only Analyse explizit als kleiner, risikoarmer
  Kandidat genannt.
- `phaseR2_agent_concepts_assessment.md`: Ein `AgentHealthMonitor` soll heute
  eher CLI-Tool oder leichter Hintergrundprozess sein, nicht eigener Manager.

## 3. Welche Kernfunktionen heute schon per Service existieren, aber nicht ergonomisch zugaenglich sind

### In `services/core.py`

- `run_task`
- `run_task_plan`
- `list_pending_approvals`
- `approve_plan_step`
- `reject_plan_step`
- `list_recent_traces`
- `get_trace`
- `get_explainability`
- `list_recent_plans`
- `list_recent_governance_decisions`
- `list_agent_catalog`
- `get_governance_state`

### Im API-Gateway

- `POST /control-plane/tasks/run`
- `POST /control-plane/plans/run`
- `GET /control-plane/approvals`
- `POST /control-plane/approvals/{approval_id}/approve`
- `POST /control-plane/approvals/{approval_id}/reject`
- `GET /control-plane/traces`
- `GET /control-plane/traces/{trace_id}`
- `GET /control-plane/traces/{trace_id}/explainability`
- `GET /control-plane/plans`
- `GET /control-plane/agents`
- `GET /control-plane/overview`

### UX-Befund

Der stabile Kern ist bereits vorhanden. Die Luecke ist nicht Architektur,
sondern Ergonomie: Entwickler und Operatoren koennen den Kernpfad zwar nutzen,
aber bisher nicht schnell genug ueber die kanonische CLI.

## 4. Warum keine zweite CLI noetig ist

- `scripts/abrain` existiert bereits als kanonischer Einstiegspunkt.
- `scripts/abrain` ist bewusst nur noch Kompatibilitaetsalias, kein zweites
  Produkt und keine zweite Runtime.
- Die fehlende Funktionalitaet betrifft Subcommands, nicht eine fehlende
  Plattform.
- Ein zweites CLI-Tool wuerde dieselben Kernfunktionen nochmals verpacken und
  genau die historische Fragmentierung erneut erzeugen, die in Phase O/R
  bewusst entfernt wurde.
- Die richtige S5-Richtung ist daher: `scripts/abrain` erweitern, intern nur
  duenn an `services/core.py` delegieren und keinen neuen Stack aufmachen.
