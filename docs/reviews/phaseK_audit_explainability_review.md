# Phase K Audit / Explainability Review

## Neue Bausteine

Phase K fuehrt einen kleinen, kanonischen Audit-/Trace-Layer ein:

- `core/audit/trace_models.py`
- `core/audit/trace_store.py`
- `core/audit/context.py`
- optionaler Exporter-Contract unter `core/audit/exporters/*`

Zusammen mit den Integrationen in `services/core.py`, `core/orchestration/orchestrator.py` und `core/orchestration/resume.py` deckt dieser Layer nun den vorhandenen Kern end-to-end ab.

## Traces und Spans

V1 modelliert:

- `TraceRecord` fuer eine gesamte Anfrage oder Plan-Ausfuehrung
- `SpanRecord` fuer Routing, Planning, Governance, Approval, Execution und Learning
- `TraceEvent` fuer Approval- und Fehlerereignisse

Die Persistenz ist bewusst klein und lokal via SQLite umgesetzt. Es gibt keinen Zwang zu einem externen Observability-Backend.

## Routing / Policy / Approval / Execution / Learning Explainability

- Routing speichert betrachtete Kandidaten, verworfene Kandidaten, ausgewaehlten Agenten und Score
- Governance speichert gematchte Regeln, Gewinner-Regel und Effekt
- Approval speichert `approval_requested`, `approval_pending`, `approval_approved`, `approval_rejected` und `plan_resumed`
- Execution speichert Adapter, Dauer, Erfolg, Warnungen und strukturierte Fehler
- Learning speichert Reward, Dataset-Update, Training-Trigger und Lernwarnungen

## Best-Effort-Integration

Tracing ist absichtlich keine harte Betriebsabhaengigkeit. Fehler in Trace-Erzeugung, Span-Speicherung oder Explainability-Persistenz fuehren nicht zum Abbruch der Hauptpipeline. Die Runtime bleibt fuehrend; der Trace-Layer dokumentiert sie nur.

## Bewusste Grenzen von V1

- kein grosses Dashboard
- kein verteiltes Trace-System
- keine Replay-Engine
- keine vollstaendige Forensik-Plattform
- keine neue Runtime
- keine Sicherheits- oder Governance-Ersatzlogik

## Sinnvolle naechste Schritte

- MCP v2 / capability-aware exposure fuer Audit-Daten
- richer Dashboards und Debug-Oberflaechen
- persistentere Orchestrierungszustandsanalyse
- Replay- und Forensics-Tools fuer komplexe Multi-Step-Pfade
