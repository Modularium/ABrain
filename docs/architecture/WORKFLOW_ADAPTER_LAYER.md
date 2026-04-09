# Workflow Adapter Layer

## Rolle von n8n und Flowise in ABrain

n8n und Flowise werden in ABrain als kontrollierte Workflow- und Interop-Systeme behandelt. Beide Systeme sind externe Ausfuehrungs- oder UI-Komponenten, nicht die interne Wahrheit des Repositories.

## Klare Trennung

- `ABrain` bleibt Decision Layer und Orchestrator.
- `n8n` wird in F2 als Workflow- und Automation-Executor eingebunden.
- `Flowise` bleibt primaer Interop- und UI-Layer und wird in F2 zusaetzlich als kleiner, kontrollierter Execution-Adapter nutzbar gemacht.
- Die interne Wahrheit bleibt `AgentDescriptor` plus Capability-Modell, Routing, ExecutionResult und Learning-Pfad.

## Warum Flowise weiterhin nicht die interne Wahrheit ist

Der bestehende Interop-Layer unter `adapters/flowise/*` bleibt ein bewusst kleiner Import-/Export-Pfad fuer Flowise-Artefakte. Der neue Flowise-Execution-Adapter unter `core/execution/adapters/flowise_adapter.py` ist davon logisch getrennt.

Das bedeutet:

- Import aus Flowise = Mapping auf `AgentDescriptor`
- Export nach Flowise = Projektion aus `AgentDescriptor`
- Execution ueber Flowise = kontrollierter Runtime-Aufruf fuer einen bereits bekannten Descriptor

Keiner dieser Pfade ersetzt das interne ABrain-Agentenmodell.

## Warum n8n als Workflow-Executor sinnvoll ist

n8n passt in ABrain als externer Automation-Executor fuer Integrations-, Backend- und Workflow-Aufgaben. In F2 wird dafuer bewusst nur ein kleiner, stabiler Webhook-Vertrag genutzt. ABrain baut in diesem Schritt weder einen generischen Workflow-Proxy noch einen beliebigen Node-Builder.

## Relevante Capability-Typen fuer Workflow-Agents

F2 nutzt vor allem Capability-IDs aus dieser kleinen Teilmenge:

- `workflow.execute`
- `workflow.automation`
- `flow.visual_agent`
- `flow.tool_orchestration`
- `data.transform`
- `docs.generate`
- `analysis.pipeline`

Diese IDs bleiben normale Capability-Strings im kanonischen Modell. Es wird keine zweite Workflow-spezifische Typwelt eingefuehrt.

## Vertraege in F2

### n8n

- kanonischer `source_type`: `n8n`
- kanonischer `execution_kind`: `workflow_engine`
- fester V1-Pfad: kontrollierter HTTP-POST gegen `webhook_url` oder `base_url + webhook_path`
- kein generischer beliebiger Workflow-Proxy
- kein frei aus Task-Input abgeleiteter Endpunkt

### Flowise Execution

- kanonischer `source_type`: `flowise`
- kanonischer `execution_kind`: `workflow_engine`
- fester V1-Pfad: kontrollierter Prediction-Call ueber `prediction_url` oder `base_url + chatflow_id`
- kein generischer Endpoint-Proxy
- keine Behauptung, dass damit die gesamte Flowise-Runtime abgedeckt sei

### Flowise Interop

- bleibt in `adapters/flowise/*`
- importiert und exportiert nur kleine Artefakte
- ist nicht Teil des Execution Layers

## Grenzen dieses Schritts

- kein vollstaendiger n8n-Node-Generator
- kein generischer Workflow-Proxy
- keine vollstaendige Flowise-Runtime- oder Agentflow-Neuimplementierung
- keine zweite Runtime im Kern
- keine MCP-Erweiterung
- keine Multi-Agent-Orchestrierung

## Historische Altartefakte

Im Repository existieren weiterhin aeltere Integrationsreste wie:

- `integrations/n8n-agentnn/*`
- `integrations/flowise-agentnn/*`
- `integrations/flowise-nodes/*`
- aeltere Integrationsdokumente unter `docs/integrations/*`

Diese Artefakte sind in F2 nicht der kanonische Runtime-Pfad. Sie gelten nur als `historical / legacy (not active runtime path)`, solange sie nicht explizit auf den neuen Foundations-Stack modernisiert werden.

## Folgephasen

Sinnvolle Folgephasen nach F2:

- tiefere Workflow-Synchronisierung
- framework-spezifisch reichere Adapter
- MCP Tool Expansion
- Multi-Agent-Orchestrierung
