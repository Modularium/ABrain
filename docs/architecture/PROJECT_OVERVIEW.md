# ABrain Project Overview

## Kurzbeschreibung

ABrain ist der aktuelle Projektname für den gehärteten Multi-Agent- und Service-Stack in diesem Repository. Der technische Schwerpunkt des aktuellen Stands liegt auf einem stabilen Core mit kontrollierter Tool-Ausführung und einem dünnen, sicheren AdminBot-Adapter.

## Hauptkomponenten

### Hardened Core

- `services/core.py`
- `core/execution/dispatcher.py`
- `core/tools/registry.py`
- `core/tools/handlers.py`
- `core/models/*`

Diese Schicht ist der bevorzugte Einstieg für kontrollierte Tool-Ausführung. Sie validiert Requests, kapselt feste Tool-Definitionen und verhindert rohe Direktpfade.

### API / FastAPI

- `server/main.py`
- `api/`
- `agentnn/mcp/`

Das Repo enthält mehrere FastAPI-basierte Einstiegspunkte und Bridges. Nicht alle davon sind gleich modernisiert; für neue sicherheitsrelevante Integrationen bleibt die gehärtete Core-Schicht führend.

### AdminBot-Adapter

- `adapters/adminbot/*`
- `docs/integrations/adminbot/*`

Der Adapter bietet nur drei read-only Tools mit typisierten Inputs. AdminBot bleibt dabei die Sicherheitsgrenze.

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

Die Kurzreferenz dazu steht in [legacy_labeling_scheme.md](/home/dev/Agent-NN/docs/reviews/legacy_labeling_scheme.md).

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
