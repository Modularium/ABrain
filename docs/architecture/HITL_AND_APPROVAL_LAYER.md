# HITL And Approval Layer

Diese Architektur beschreibt den Phase-I-Stand auf dem Branch `codex/phaseI-hitl-approval-layer`. Solange der Branch nicht gemerged ist, bleibt der Approval-Layer ein Review-/Merge-Kandidat und noch nicht Teil von `main` oder des Releases `v1.1.0`.

## Warum HITL jetzt sinnvoll ist

ABrain kann seit Phase H mehrstufige Plaene ausfuehren. Damit steigt der Bedarf, sensible Schritte kontrolliert anzuhalten, bevor externe Seiteneffekte, mutierende Repo-Aktionen oder systemnahe Ausfuehrungen tatsaechlich gestartet werden.

## Sicherheitsgrenze vs Approval Layer

- `CandidateFilter` und deterministische Policy-Pruefungen bleiben die harte Sicherheitsgrenze.
- Der Approval-Layer ersetzt diese Grenze nicht.
- HITL fuegt nur einen zusaetzlichen menschlichen Kontrollpunkt fuer sensible Schritte hinzu.

## Welche Schritte Approval brauchen koennen

V1 betrachtet insbesondere:

- hohe oder kritische Step-Risiken
- explizite Step-Metadaten wie `requires_human_approval`
- externe Seiteneffekte (`external_side_effect`)
- riskante Workflow-Ausfuehrungen
- systemnahe oder cloud-seitige mutierende Aktionen

## Pause / Approve / Reject / Resume

Der Flow ist explizit und serialisierbar:

1. PlanStep wird geroutet
2. ApprovalPolicy bewertet den konkret gewaehlten Step-Kontext
3. falls Approval noetig ist:
   - `ApprovalRequest` erzeugen
   - Plan als `paused` markieren
   - Schritt noch nicht ausfuehren
4. spaeter:
   - `approve` -> Plan genau am pausierten Schritt fortsetzen
   - `reject` -> Schritt sauber als abgelehnt markieren und Plan konsistent beenden

## Integration in Plan Execution

Approval liegt im Orchestrator direkt vor der Step-Execution. In diesem Branch laeuft davor bereits der deterministische Governance-Check. Dadurch sieht der Approval-Layer:

- den `PlanStep`
- den gerouteten Agenten
- `source_type` und `execution_kind`
- relevante Step-Metadaten

Der Orchestrator bleibt trotzdem nur Komposition ueber Routing, Execution und Feedback.

## Beziehung zu Claude Code Permissions

Claude Code, Codex und andere Adapter behalten ihre nativen Sicherheits- und Permission-Mechaniken. Der ABrain-Approval-Layer sitzt darueber auf Plan-/Step-Ebene. Er ersetzt keine adapterinternen Tool- oder Permission-Grenzen.

## Grenzen von V1

- kein generischer Chat mit einem Menschen mitten im Plan
- keine verteilte Approval-Infrastruktur
- keine ML-basierte Risiko-Klassifikation
- keine freie Agent-zu-Agent-Freigabe
- keine automatische Low-Risk-Auto-Approve-Engine

## Folgephasen

Sinnvolle naechste Schritte nach I:

- feinere Policy-Regeln
- automatische Vorentscheidung fuer Low-Risk-Schritte
- capability-aware MCP approval surface
- reichere Human-Review-Oberflaechen
