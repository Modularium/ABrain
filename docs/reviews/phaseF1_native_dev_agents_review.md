# Phase F1 Native Dev Agents Review

## Implementierte und geschärfte Adapter

Phase F1 schärft die vorhandene Adapterbasis für:

- `OpenHandsExecutionAdapter`
- `ClaudeCodeExecutionAdapter`
- `CodexExecutionAdapter`

Alle drei bleiben statische `ExecutionAdapter` in der vorhandenen `ExecutionAdapterRegistry`.

## OpenHands

OpenHands ist als self-hosted HTTP-Service angebunden. Der Adapter nutzt in F1 nur den klaren V1-Pfad `POST /api/v1/app-conversations`, behandelt Timeouts und HTTP-/Transportfehler strukturiert und erzeugt ein normales `ExecutionResult`.

## Claude Code

Claude Code ist als headless CLI-Executor angebunden. Der Adapter nutzt `claude -p ... --output json`, bleibt nicht-interaktiv und erlaubt in F1 nur einen kleinen, kontrollierten Konfigurationssatz wie `cwd`, `allowed_tools` und `permission_mode`.

## Codex

Codex ist in F1 bewusst nur als ehrlicher CLI-V1-Pfad angebunden. Der Adapter nutzt `codex exec --json ...`, behandelt Timeouts und Protokollfehler strukturiert und markiert den langfristig bevorzugten Zielpfad als App-Server-/JSON-RPC-Integration.

## Agent Creation

Die bisher grobe Code-Heuristik wurde in F1 differenziert:

- self-hosted oder local-preferred -> OpenHands
- policy-driven/headless CLI -> Claude Code
- cloud/high-capability/large task -> Codex

Die Erzeugung bleibt intern und erzeugt nur `AgentDescriptor`, keine direkte externe Provisionierung.

## Learning und Feedback

Alle nativen Dev-Agenten nutzen denselben `ExecutionResult`-, Feedback- und Learning-Pfad wie die bisherigen Adapter. Es gibt keinen separaten Lern-Sonderpfad pro Adapter.

## Bewusste Grenzen

- keine vollstaendige native OpenHands-Session-Steuerung
- keine Codex-App-Server-Vollintegration
- keine interaktive Claude-Code-Nutzung
- keine generische Proxy- oder Plugin-Architektur

## Sinnvolle naechste Phase

- n8n- oder Flowise-Runtime-Integration
- Multi-Agent-Orchestrierung
- Codex App Server Full Adapter
- spaetere MCP-Expansion auf Basis des gehärteten Core-Pfads
