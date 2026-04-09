# Native Dev Agent Adapters

## Rolle von OpenHands, Codex und Claude Code in ABrain

OpenHands, Codex und Claude Code sind in ABrain Ausfuehrungskomponenten fuer Entwicklungs- und Code-Aufgaben. Sie werden nicht als interne Wahrheit modelliert, sondern als explizite `ExecutionAdapter` hinter dem bestehenden Foundations-Stack.

## Klare Trennung

- `ABrain` bleibt Decision Layer und Orchestrator.
- Dev-/Code-Agents gehoeren zum Execution Layer.
- Routing, Capability-Filterung und Neural Ranking bleiben in `core/decision/*`.
- Die eigentliche Ausfuehrung bleibt in `core/execution/*`.

## Warum diese Adapter nicht zur internen Wahrheit werden

Die interne Wahrheit bleibt `AgentDescriptor` plus Capability-Modell. OpenHands, Codex und Claude Code werden nur ueber statische Adapter angesprochen. Es gibt:

- keine zweite Registry
- keinen generischen Command-Proxy
- keine Plugin-Discovery
- keine direkte Kopplung der Entscheidungsschicht an externe Dev-Agenten

## Adapter-Profile in F1

### OpenHands

- Rolle: local/self-hosted dev execution
- kanonischer `source_type`: `openhands`
- kanonischer `execution_kind`: `http_service`
- V1-Pfad: `POST /api/v1/app-conversations`
- kein Streaming-Zwang
- keine implizite Session-Engine ausserhalb des Adapters

### Claude Code

- Rolle: headless CLI execution
- kanonischer `source_type`: `claude_code`
- kanonischer `execution_kind`: `local_process`
- V1-Pfad: `claude -p ... --output json`
- optional konfigurierbar: `cwd`, `allowed_tools`, `permission_mode`
- kein interaktiver Modus

### Codex

- Rolle: kontrollierter CLI-basierter Dev-Agent in F1
- kanonischer `source_type`: `codex`
- kanonischer `execution_kind`: `local_process`
- V1-Pfad: `codex exec --json ...`
- optional konfigurierbar: `cwd`, `model`, `sandbox_mode`, `approval_mode`
- langfristig bevorzugter Zielpfad: App-Server-/JSON-RPC-Integration

## Typische Capabilities

Die nativen Dev-Agenten tragen typischerweise Capabilities wie:

- `code.generate`
- `code.refactor`
- `code.analyze`
- `repo.modify`
- `tests.run`
- `docs.write`
- optional `review.code`

## Grenzen von F1

- keine Multi-Agent-Orchestrierung
- keine Live-Synchronisierung mit externen Dev-Agent-Sitzungen
- keine vollstaendige Session- oder Workspace-Verwaltung ausserhalb der Adapter
- keine App-Server-Vollintegration fuer Codex
- keine MCP-Erweiterung

## Folgephasen

Sinnvolle Folgephasen nach F1:

- vertiefte Adapter mit mehr nativer API-Abdeckung
- feinere capability-aware selection refinement
- Multi-Agent-Orchestrierung
- Codex App Server Full Adapter
