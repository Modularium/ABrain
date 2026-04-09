# ABrain Project Overview

## Kurzbeschreibung

ABrain ist der aktuelle Projektname für den gehärteten Multi-Agent- und Service-Stack in diesem Repository. Der technische Schwerpunkt des aktuellen Stands liegt auf einem stabilen Core mit kontrollierter Tool-Ausführung und einem dünnen, sicheren AdminBot-v2-Adapter.

## Hauptkomponenten

### Hardened Core

- `services/core.py`
- `core/execution/dispatcher.py`
- `core/tools/registry.py`
- `core/tools/handlers.py`
- `core/models/*`

Diese Schicht ist der bevorzugte Einstieg für kontrollierte Tool-Ausführung. Sie validiert Requests, kapselt feste Tool-Definitionen und verhindert rohe Direktpfade.

Der canonical runtime stack liegt in `services/*`. Die Kurzbegründung und die verworfenen Alternativen stehen in [CANONICAL_RUNTIME_STACK.md](./CANONICAL_RUNTIME_STACK.md).

### Canonical Agent Model

- `core/decision/*`
- `services/agent_registry/*` als Migrationskante
- `adapters/flowise/*` als Interop-Schicht

ABrain fuehrt nun ein eigenes kanonisches `AgentDescriptor`-Modell. Dieses Format ist die interne Wahrheit fuer spaeteres Routing, Planning und Bewertung. Flowise wird davon explizit getrennt als externer Interop- und UI-Layer behandelt. Die Details stehen in [AGENT_MODEL_AND_FLOWISE_INTEROP.md](./AGENT_MODEL_AND_FLOWISE_INTEROP.md).

### Decision Layer

- `core/decision/planner.py`
- `core/decision/candidate_filter.py`
- `core/decision/neural_policy.py`
- `core/decision/routing_engine.py`

Der kanonische Decision Layer trennt nun Planner, deterministische Kandidatenfilterung und verpflichtendes NeuralPolicyModel explizit. Das NN ist immer aktiv, ersetzt aber nicht die harte Sicherheitsgrenze. Es rankt nur bereits sicher gefilterte Kandidaten. Die Zielarchitektur steht in [DECISION_LAYER_AND_NEURAL_POLICY.md](./DECISION_LAYER_AND_NEURAL_POLICY.md).

### Execution Layer

- `core/execution/adapters/*`
- `core/execution/execution_engine.py`
- `core/decision/agent_creation.py`
- `core/decision/feedback_loop.py`

Der Execution Layer fuehrt eine bereits getroffene Routing-Entscheidung aus. Er kapselt statische Adapter fuer AdminBot, OpenHands, Codex, Claude Code, n8n und Flowise, ohne selbst neue Decision-Logik einzufuehren. OpenHands wird in F1 als self-hosted HTTP-Service angesprochen; Claude Code und Codex werden in F1 als kontrollierte headless CLI-Adapter behandelt. n8n kommt in F2 als kontrollierter Workflow-Executor hinzu; Flowise bleibt primaer Interop-Layer und wird nur zusaetzlich als kleiner Workflow-Execution-Adapter genutzt. Agent Creation und Feedback Loop liegen explizit neben dem Routing und bleiben vom gehärteten Core getrennt. Details stehen in [EXECUTION_LAYER_AND_AGENT_CREATION.md](./EXECUTION_LAYER_AND_AGENT_CREATION.md), [NATIVE_DEV_AGENT_ADAPTERS.md](./NATIVE_DEV_AGENT_ADAPTERS.md) und [WORKFLOW_ADAPTER_LAYER.md](./WORKFLOW_ADAPTER_LAYER.md).

### Learning System

- `core/decision/learning/*`

Das Learning-System sammelt strukturierte Trainingsdaten aus realen Executions, berechnet einen deterministischen Reward und trainiert das verpflichtende NeuralPolicyModel schrittweise nach. Es beeinflusst nur das Ranking innerhalb der bereits sicher gefilterten Kandidatenmenge.

Die Lernschicht ist im Runtime-Pfad bewusst best-effort: Learning- oder Trainingsfehler duerfen eine bereits erfolgreiche Execution nicht nachtraeglich scheitern lassen.

### API / FastAPI

- `server/main.py`
- `api/`
- `agentnn/mcp/`
- `interfaces/mcp_v1/`

Das Repo enthält mehrere API-basierte Einstiegspunkte und Bridges. Produktiv maßgeblich bleiben die gehärtete Core-Schicht und die `services/*`-Runtime. Der aktive MCP-Einstieg liegt in `interfaces/mcp_v1/` und bleibt eine dünne Protokollschicht vor dem gehärteten Core. Historische MCP- und Smolitux-Bridges sind `legacy (disabled)` und keine gleichrangigen Runtime-Pfade.

### Workflow Interop und historische Integrationen

- `adapters/flowise/*`
- `integrations/n8n-agentnn/*`
- `integrations/flowise-agentnn/*`
- `integrations/flowise-nodes/*`

Der kanonische F2-Pfad fuer Workflow-Ausfuehrung liegt im Execution Layer unter `core/execution/adapters/*`. Aeltere n8n- und Flowise-Integrationsartefakte unter `integrations/*` bleiben hoechstens `historical / legacy (not active runtime path)`, solange sie nicht explizit auf den neuen Foundations-Stack modernisiert wurden.

### AdminBot-Adapter

- `adapters/adminbot/*`
- `docs/integrations/adminbot/*`

Der Adapter bindet AdminBot v2 als einen spezialisierten Executor-Provider unter mehreren an. Aktuell freigegeben sind nur drei read-only Tools mit typisierten Inputs: `adminbot_system_status`, `adminbot_system_health` und `adminbot_service_status`. AdminBot bleibt dabei die Sicherheitsgrenze.

### SDK / CLI

- `sdk/`

Das SDK und die CLI existieren weiter und nutzen für gehärtete Listen-/Dispatch-Pfade die neue Service-Schicht.

### Frontend / Monitoring

- `frontend/agent-ui`
- `monitoring/`

Diese Bereiche bleiben Teil des Repositories, sind aber nicht der maßgebliche Referenzpfad für sicherheitsrelevante Integrationen. Führend bleiben die gehärtete Core-Schicht und die explizit dokumentierten AdminBot-Pfade.

## Path Labeling

Fuer spaetere Reviews gilt dieses kurze Schema:

- `canonical path`: aktiver Referenzpfad
- `legacy (disabled)`: historischer Runtime-Pfad, bewusst nicht aktiv
- `historical / legacy (not active runtime path)`: historische Doku oder Artefakte ohne aktiven Runtime-Vertrag

Die Kurzreferenz dazu steht in [legacy_labeling_scheme.md](../reviews/legacy_labeling_scheme.md).

## Aktueller Scope

Stabil und gezielt abgesichert sind aktuell vor allem:

- Tool-Dispatcher und feste Registry
- getypte Tool-Inputs und strukturierte Fehler
- Identity-Metadaten
- AdminBot-Sicherheitsinvarianten
- gezielte Kern- und Adapter-Tests

Noch nicht das Ziel dieses Schritts:

- Multi-Agent-Orchestrierung
- breite MCP-Tool-Expansion
- voll ausgereifte native Spezialadapter
- fortgeschrittenes kontinuierliches Training oder RL
- Umbenennung aller internen Paket- und Deploy-Slugs

## Bewusst verbleibende historische Identifiers

Einige technische Namen bleiben vorerst bestehen, z. B. `agentnn`, `agent_nn` oder `agent-nn` in Paket-, Helm- oder Image-Slugs. Diese sind Follow-up-Kandidaten für einen separaten, technisch riskanteren Migrationsschritt.
