# Phase I Review: HITL And Approval Layer

## Neue Approval-Bausteine

Phase I fuehrt diese Bausteine ein:

- `core/approval/models.py`
- `core/approval/store.py`
- `core/approval/policy.py`
- `core/orchestration/resume.py`
- Erweiterungen in `core/orchestration/orchestrator.py`
- neue Service-Einstiege in `services/core.py`

## Pause / Approve / Reject / Resume

Der Orchestrator prueft nach dem Step-Level-Routing, aber vor der Step-Execution, ob ein Approval noetig ist. Wenn ja:

1. `ApprovalRequest` erzeugen
2. Plan als `paused` markieren
3. keine Execution des sensiblen Schritts

Spaetere Entscheidungen laufen explizit:

- `approve` -> Plan wird genau am pausierten Schritt fortgesetzt
- `reject` -> Schritt wird sauber als administrativ abgelehnt markiert

## ApprovalPolicy

Die Policy bleibt deterministisch. Sie betrachtet:

- Step-Risk
- sensible Capability-Muster
- `source_type` und `execution_kind`
- Step-Metadaten wie `requires_human_approval`, `risky_operation` und `external_side_effect`

Es gibt kein ML und keine Blackbox in dieser Schicht.

## Zusammenspiel mit der Orchestrierung

Approval bleibt zentral im Orchestrator. Adapter bauen keine eigenen Approval-Workflows. Der bestehende Routing-/Execution-/Feedback-Pfad bleibt kanonisch; HITL fuegt nur einen kontrollierten Pausenpunkt davor ein.

## Learning bei Approve / Reject

- `approve` + spaetere Execution -> normaler Feedback-/Learning-Pfad
- `reject` -> keine normale Execution, daher kein normales Failure-Learning
- zusaetzliche Guard in `FeedbackLoop`: administrative Rejections werden nicht als Modell- oder Execution-Fehler verbucht

## Bewusste Grenzen von V1

- keine verteilte Approval-Infrastruktur
- kein generisches Chat-Review mit Menschen
- keine ML-basierte Risiko-Klassifikation
- keine automatische Low-Risk-Auto-Approve-Engine
- keine beliebige Agent-zu-Agent-Freigabe

## Sinnvolle Folgephase

Nach Phase I sind als naechste Schritte sinnvoll:

- capability-aware MCP expansion
- tiefere Governance- und Policy-Regeln
- reichere Human-Review-Surfaces
