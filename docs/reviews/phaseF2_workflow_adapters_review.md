# Phase F2 Review: Workflow Adapter Layer

## Neue Workflow-Adapter

F2 fuehrt zwei neue Execution-Adapter ein:

- `core/execution/adapters/n8n_adapter.py`
- `core/execution/adapters/flowise_adapter.py`

Beide Adapter haengen an der bestehenden statischen `ExecutionAdapterRegistry` und nutzen denselben `ExecutionResult`-Vertrag wie die bereits vorhandenen Adapter.

## n8n-Integration

n8n wird in F2 als kontrollierter Workflow- und Automation-Executor angesprochen. Der Adapter nutzt nur einen kleinen, reviewbaren HTTP-Vertrag:

- `webhook_url`
- oder `base_url + webhook_path`

Der Request-Body wird aus internem Task- und AgentDescriptor-Kontext auf ein stabiles Payload-Schema gemappt. Es gibt keinen generischen "call any workflow"-Pfad.

## Flowise als Execution-Adapter

Der bestehende Flowise-Interop-Layer bleibt unveraendert die Schicht fuer Import und Export kleiner Artefakte. Neu kommt nur ein separater Runtime-Adapter hinzu, der einen kontrollierten Prediction-Pfad fuer bekannte Descriptoren ansprechen kann.

Der Flowise-Execution-Adapter ist bewusst klein:

- `prediction_url`
- oder `base_url + chatflow_id`

Er bildet ABrain-Tasks auf einen festen Prediction-Request ab, ohne daraus eine zweite Runtime oder eine 1:1-Abbildung aller Flowise-Funktionen zu machen.

## Trennung zwischen Flowise-Interop und Flowise-Execution

Die Trennung bleibt explizit:

- `adapters/flowise/*` = Interop / UI / Artefakt-Mapping
- `core/execution/adapters/flowise_adapter.py` = kontrollierter Runtime-Adapter

Damit bleibt `AgentDescriptor` die interne Wahrheit. Flowise wird weder Kernmodell noch Decision Layer.

## Agent Creation fuer Workflow-Tasks

`core/decision/agent_creation.py` unterscheidet Workflow-Aufgaben in F2 explizit:

- `workflow_automation` oder backend-lastige Workflow-Aufgaben -> `n8n`
- `visual_agent_editable` oder `tool_orchestration_ui` -> `flowise`

Die Heuristik bleibt absichtlich klein und nachvollziehbar. Sie erzeugt weiterhin nur interne `AgentDescriptor`.

## Learning und Feedback

Die neuen Adapter liefern dieselbe `ExecutionResult`-Struktur wie andere Adapter. `FeedbackLoop`, `OnlineUpdater` und das Learning-System benoetigen deshalb keinen Workflow-Sonderpfad.

## Historische Integrationsreste

Im Repository verbleiben aeltere Integrationsartefakte, unter anderem:

- `integrations/n8n-agentnn/*`
- `integrations/flowise-agentnn/*`
- `integrations/flowise-nodes/*`
- aeltere Integrationsdokumente unter `docs/integrations/*`

Diese Artefakte bleiben in F2 bewusst ausserhalb des kanonischen Runtime-Pfads. Sie sind nur noch als `historical / legacy (not active runtime path)` einzuordnen.

## Bewusste Grenzen von F2

- kein generischer Workflow-Proxy
- kein vollstaendiger n8n-Node-Builder
- keine vollstaendige Flowise-Runtime-Neuimplementierung
- keine MCP-Erweiterung
- keine Multi-Agent-Orchestrierung

## Sinnvolle Folgephase

Nach F2 sind als naechste Schritte sinnvoll:

- tiefere framework-spezifische Adapter
- Multi-Agent-Orchestrierung
- MCP Tool Expansion
- reichere Synchronisationspfade fuer Workflow-Systeme
