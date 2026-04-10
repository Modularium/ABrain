# Audit And Explainability Layer

## Warum Audit / Explainability jetzt sinnvoll ist

Mit Multi-Step-Planung, Approval und Governance reicht ein einzelnes Endresultat nicht mehr aus. ABrain muss nachvollziehbar machen, wie eine Aufgabe zerlegt, welcher Agent gewaehlt, welche Policy getroffen, ob Approval angefordert und ob Learning ausgelöst wurde.

## Trace vs Audit Log vs Explainability

- `Trace`: der zusammenhaengende Ablauf einer Anfrage oder Plan-Ausfuehrung
- `Span`: ein zeitlich begrenzter Teilabschnitt innerhalb eines Traces
- `Audit Log`: persistente, spaeter abrufbare Fakten ueber diesen Ablauf
- `Explainability`: kompakte, menschenlesbare Beschreibung, warum Routing und Governance zu einem konkreten Ergebnis kamen

## Was V1 nachvollziehbar macht

- Routing-Entscheidungen inkl. betrachteter und verworfener Kandidaten
- Policy-Entscheidungen inkl. gematchter Regeln und gewonnener Prioritaet
- Approval-Pause, Approval-Entscheidung und Resume
- Adapter-Ausfuehrung mit Erfolg, Warnungen, Dauer und optionalen Kosten
- Feedback- und Learning-Hook inkl. Reward, Dataset-Update und Training-Trigger

## V1-Modelle

V1 nutzt drei Kernobjekte:

- `TraceRecord`: Top-Level-Record fuer eine Anfrage oder Plan-Ausfuehrung
- `SpanRecord`: verschachtelte Teiloperation mit Status, Attributen und Events
- `ExplainabilityRecord`: kompakter Snapshot fuer Routing- und Policy-Erklaerbarkeit

Die Persistenz liegt in `core/audit/trace_store.py` als kleine SQLite-Datei. Das orientiert sich an OTel-Grundideen wie Trace/Span/Event, ohne ein externes Backend zu erzwingen.

## Integration in den vorhandenen Kern

Der Trace-Layer fuehrt keine zweite Runtime ein. Er haengt sich best-effort an die kanonischen Pfade:

- `run_task(...)`
- `run_task_plan(...)`
- `approve_plan_step(...)` / `reject_plan_step(...)`
- `PlanExecutionOrchestrator`
- `resume_plan(...)`

Die eigentliche Reihenfolge bleibt:

`Task -> Routing -> Governance -> (Approval?) -> Execution -> Feedback / Learning -> Result`

Tracing beschreibt diesen Pfad nur. Es ersetzt weder CandidateFilter noch Governance noch Approval.

## Explainability fuer Routing und Governance

Routing-Explainability speichert vor allem:

- welche Kandidaten gerankt wurden
- welche Kandidaten vom CandidateFilter ausgeschlossen wurden
- welcher Agent gewaehlt wurde
- welcher Score verwendet wurde

Governance-Explainability speichert:

- welche Regeln gematcht haben
- welche Regel gewann
- welcher Effekt herauskam: `allow`, `deny`, `require_approval`

## Approval-Lifecycle

Approval-Ereignisse werden als Span-Events erfasst:

- `approval_requested`
- `approval_pending`
- `approval_approved`
- `approval_rejected`
- `plan_resumed`

Approval bleibt dabei derselbe bestehende HITL-Pfad. Der Trace-Layer dokumentiert ihn nur.

## Best-Effort-Prinzip

Tracing darf die Hauptpipeline nicht destabilisieren. Wenn Trace-Erzeugung, Span-Persistenz oder Explainability-Speicherung fehlschlagen:

- die eigentliche Decision-/Execution-Pipeline laeuft weiter
- Trace-Warnungen werden lokal gesammelt
- es gibt keinen harten Runtime-Abbruch nur wegen Tracing

## OTel-/Export-Vorbereitung

V1 fuehrt keine externe OTel-Infrastruktur ein. Die Modelle orientieren sich aber bewusst an Trace-/Span-/Event-Konzepten, damit spaetere Exporter oder Dashboards sauber aufsetzen koennen. Der optionale Exporter-Contract liegt klein in `core/audit/exporters/base.py`.

## Grenzen dieses Schritts

- kein volles Observability-Frontend
- kein fertiges SIEM
- keine globale verteilte Trace-Infrastruktur
- keine vollstaendige Replay-Engine
- keine Forensik-Plattform
- keine MCP-spezifische Explainability-Oberflaeche

## Sinnvolle Folgephasen

- externe OTel- oder Log-Exporter
- UI / Dashboard fuer Traces und Explainability
- Replay- und Debug-Werkzeuge fuer komplexe Plaene
- spaetere MCP-Expose fuer Audit-/Explainability-Abfragen
