# Agent Model And Flowise Interop

## Warum ABrain ein eigenes kanonisches Agentenmodell hat

ABrain soll Agenten framework-unabhaengig bewerten, auswaehlen, vergleichen und spaeter auch planen koennen. Dafuer braucht das System ein eigenes, stabiles Kernformat. Ein externes UI- oder Workflow-Format darf diese interne Wahrheit nicht bestimmen.

## Warum Flowise NICHT das interne Kernformat ist

Flowise ist auf visuelle Flows, Node-Graphen und Editor-Beduerfnisse ausgerichtet. ABrain braucht dagegen ein kompaktes Descriptor-Modell fuer Routing, Planung, Bewertung und Persistenz. Flowise ist deshalb kompatibler Interop, aber nicht die interne Wahrheit.

## Rolle von Flowise

- Import eines unterstuetzten Flowise-Artefakts in einen `AgentDescriptor`
- Export eines unterstuetzten `AgentDescriptor` in ein kleines Flowise-kompatibles Artefakt
- visuelle UI und manuelle Nachbearbeitung fuer geeignete Agenten

## Rolle des ABrain-Agentenmodells

- interne Wahrheit fuer Agent-Metadaten
- Grundlage fuer spaeteres Routing, Planning und Bewertung
- framework-unabhaengige Persistenz
- Quelle fuer Interop-Adapter in andere Richtungen

## Kanonische Kernmodelle in diesem Schritt

- `Capability` in `core/decision/capabilities.py`
- `AgentDescriptor` in `core/decision/agent_descriptor.py`
- `AgentRegistry` in `core/decision/agent_registry.py`

Die Registry-/Service-Welt bleibt dabei migrationsfaehig: `services/agent_registry/schemas.py` und `services/agent_registry/service.py` koennen jetzt zwischen `AgentInfo` und `AgentDescriptor` mappen, ohne die bestehende Service-Schnittstelle zu brechen.

## Unterstuetzte Flowise-Teilmenge in V1

### Importierbar

1. Kleine agentenartige Artefakte mit diesen Feldern:
   - `id`
   - `name`
   - `description`
   - `type == "agent"`
   - `tools`
   - `capabilities`
   - `llm`
   - `created_at`
   - `version`
   - `metadata`
2. Einfache Chatflow-Exporte mit:
   - `id`
   - `name`
   - `type`
   - `nodes`
   - `edges`

### Exportierbar

Nur ein kleines agentenartiges Flowise-Zielartefakt:

- `id`
- `name`
- `description`
- `type == "agent"`
- `tools`
- `capabilities`
- `llm`
- `created_at`
- `version`
- `metadata`

## Was ignoriert oder nur als Metadata uebernommen wird

- unbekannte Top-Level-Felder werden nicht auf Kernfelder gemappt
- unterstuetzte, aber nicht kanonische Flowise-Daten landen kontrolliert in `descriptor.metadata`
- bei Chatflow-Importen werden Node-/LLM-Hinweise nur als Metadata uebernommen
- Knotenpositionen, UI-State, Editor-spezifische Settings, Credentials und komplexe Kantenlogik werden nicht zur internen Wahrheit

## Was bewusst NICHT unterstuetzt wird

- vollstaendige Rekonstruktion beliebiger komplexer Flowise-Agentflows
- Live-Synchronisierung mit einem Flowise-Server
- Flowise als Persistenz- oder Wahrheitsmodell
- generische Framework-Abbildung beliebiger Fremdformate

## Grenzen dieses Schritts

- kein RoutingEngine-Umbau
- kein Planner-Umbau
- kein verpflichtendes NeuralPolicyModel
- keine neuen Runtime-Pfade
- kein generisches Plugin-/Proxy-System

## Folgephasen

- `RoutingEngine` auf Basis von `AgentDescriptor` und `Capability`
- `Planner`, der Descriptoren aktiv auswaehlt
- NN-Scoring bzw. `NeuralPolicyModel`
- weitere Adapter fuer n8n, OpenHands, Codex und Claude Code
