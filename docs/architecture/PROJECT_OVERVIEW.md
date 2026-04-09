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

### API / FastAPI

- `server/main.py`
- `api/`
- `agentnn/mcp/`
- `interfaces/mcp_v1/`

Das Repo enthält mehrere API-basierte Einstiegspunkte und Bridges. Produktiv maßgeblich bleiben die gehärtete Core-Schicht und die `services/*`-Runtime. Der aktive MCP-Einstieg liegt in `interfaces/mcp_v1/` und bleibt eine dünne Protokollschicht vor dem gehärteten Core. Historische MCP- und Smolitux-Bridges sind `legacy (disabled)` und keine gleichrangigen Runtime-Pfade.

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

- breite Architektur-Neuschreibung
- Umbenennung aller internen Paket- und Deploy-Slugs
- Ausweitung des AdminBot-Scope
- flächendeckende Modernisierung aller Legacy-Bereiche

## Bewusst verbleibende historische Identifiers

Einige technische Namen bleiben vorerst bestehen, z. B. `agentnn`, `agent_nn` oder `agent-nn` in Paket-, Helm- oder Image-Slugs. Diese sind Follow-up-Kandidaten für einen separaten, technisch riskanteren Migrationsschritt.
