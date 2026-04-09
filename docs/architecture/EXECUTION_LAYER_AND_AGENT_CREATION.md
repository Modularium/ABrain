# Execution Layer And Agent Creation

## Rolle des Execution Layers

Der Execution Layer fuehrt aus, was der Decision Layer bereits entschieden hat. Er nimmt eine `RoutingDecision`, waehlt den passenden `ExecutionAdapter` fuer den gewaehlten `AgentDescriptor` und liefert ein strukturiertes Ergebnis zurueck.

## Klare Trennung

### Decision Layer

Der Decision Layer entscheidet:

- Planner
- CandidateFilter
- NeuralPolicyModel
- RoutingEngine

### Execution Layer

Der Execution Layer fuehrt aus:

- Adapter-Auswahl
- Adapter-Validierung
- Task-Ausfuehrung
- Ergebnisstrukturierung

## Adapter-Konzept

Jeder externe Agent wird ueber einen expliziten `ExecutionAdapter` angesprochen. Adapter sind statisch registriert und werden nicht dynamisch aus externen Quellen geladen.

## Unterstuetzte Adapter-Typen in V1

- `system_executor`: AdminBot ueber den gehärteten Core
- `http_service`: OpenHands als self-hosted Dev-Agent
- `local_process`: Codex oder Claude Code im headless CLI-Modus
- `workflow_engine`: noch kein V1-Executor, nur als Zieltyp fuer spaetere Erweiterung modelliert

## Agent Creation

Wenn kein existierender Agent gut genug ist, kann ABrain einen neuen `AgentDescriptor` erzeugen. V1 erzeugt nur interne Descriptoren und registriert sie im kanonischen `AgentRegistry`.

Heuristik in V1:

- `system` -> AdminBot / `system_executor`
- `code` -> OpenHands / `http_service`, Claude Code / `local_process` oder Codex / `local_process`
- `workflow` -> Flowise / `workflow_engine`
- bevorzugte Source Types koennen ueber Execution Hints eingeengt werden

## Feedback Loop

Der Feedback Loop aktualisiert nach jeder Ausfuehrung die `PerformanceHistory`:

- Success Rate
- durchschnittliche Latenz
- Kosten
- Failure Count

Zusätzlich erzeugt der aktuelle Foundations-Stand Trainingssamples und kann das `NeuralPolicyModel` inline in kleinen Schritten nachtrainieren. Dieser Lernpfad bleibt bewusst best-effort und darf erfolgreiche Executions nicht nachtraeglich fehlschlagen lassen.

## Gesamtpipeline

`Task -> Planner -> CandidateFilter -> NeuralPolicyModel -> RoutingDecision -> ExecutionAdapter -> ExecutionResult -> FeedbackUpdate`

## Grenzen dieses Schritts

Nicht Teil von V1:

- Multi-Agent-Orchestrierung
- MCP-Erweiterung
- UI- oder Flowise-Sync
- verteilte Execution
