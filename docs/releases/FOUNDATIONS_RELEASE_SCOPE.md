# Foundations Release Scope

## Enthalten

Der aktuelle Foundations-Release umfasst:

- `AgentDescriptor`, `Capability` und `AgentRegistry`
- Flowise-Import und -Export als Interop-Schicht
- `Planner`, `CandidateFilter`, `NeuralPolicyModel` und `RoutingEngine`
- `ExecutionEngine` mit statischer Adapterbasis
- Learning-System mit Dataset, Reward Model, OnlineUpdater, Trainer und Feedback Loop
- den gehärteten Core als Referenzpfad für Tool-Ausführung und AdminBot-Anbindung

## Nicht enthalten

Bewusst nicht Teil dieses Releases sind:

- Multi-Agent-Orchestrierung
- breite MCP Tool Expansion
- voll ausgereifte native OpenHands-/Codex-/Claude-Code-Adapter
- fortgeschrittenes kontinuierliches Training oder RL
- dynamische Plugin- oder Proxy-Architekturen

## Klare Grenzen

- Flowise ist nur Interop und UI, nicht interne Wahrheit.
- MCP bleibt nur Interface-Layer, nicht Kernlogik.
- Das NeuralPolicyModel bleibt verpflichtend, ersetzt aber keine Sicherheitsgrenzen.
- Candidate Filtering und Policy-Checks bleiben die harte Sicherheitsgrenze.
- AdminBot bleibt über den gehärteten Core angebunden.

## Erwarteter Einsatzbereich

Dieser Release ist als saubere, reviewbare und erweiterbare Basis für die nächste Ausbaustufe gedacht:

- sichere interne Tool-Ausführung
- kontrollierte Agentenauswahl
- erste trainierbare Routing-Optimierung
- vorbereiteter Ausbau weiterer Adapter, Orchestrierung und Interface-Flächen
