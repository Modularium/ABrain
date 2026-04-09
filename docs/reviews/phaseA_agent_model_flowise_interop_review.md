# Phase A Agent Model Flowise Interop Review

## Neue Kernmodelle

- `Capability` in `core/decision/capabilities.py`
- `AgentDescriptor` in `core/decision/agent_descriptor.py`
- `AgentRegistry` in `core/decision/agent_registry.py`

## Flowise-Interop-Schicht

- `adapters/flowise/importer.py`
- `adapters/flowise/exporter.py`
- `adapters/flowise/models.py`

Import und Export laufen bewusst ueber eine kleine, dokumentierte Teilmenge. Weder Flowise noch ein anderes externes Format werden zur internen Wahrheit.

## Unterstuetzte Flowise-Teilmenge

- kleine agentenartige Artefakte mit `id`, `name`, `description`, `tools`, `capabilities`, `llm`, `created_at`, `version`
- einfache Chatflow-Exporte mit `name`, `nodes`, `edges`, die nur teilweise in Descriptor-Metadata uebernommen werden

## Bewusst NICHT unterstuetzt

- vollstaendige Rekonstruktion komplexer Chatflow-Semantik
- Live-Sync mit Flowise-Servern
- generische 1:1-Abbildung beliebiger Flowise-Strukturen
- Flowise als Persistenz- oder Entscheidungsmodell

## Trennung ABrain intern / Flowise extern

- intern fuehrend: `AgentDescriptor`
- extern kompatibel: Flowise Import/Export
- unbekannte oder editor-spezifische Flowise-Felder werden nicht zu Kernfeldern
- nur kontrollierte Teilmengen landen in `descriptor.metadata`

## Service-/Registry-Anbindung

`services/agent_registry/schemas.py` kann jetzt zwischen `AgentInfo` und `AgentDescriptor` mappen. `services/agent_registry/service.py` bietet zusaetzlich `register_descriptor`, `get_descriptor` und `list_descriptors`, ohne die bestehende API-Schnittstelle hart umzubauen.

## Hinzugefuegte Tests

- `tests/decision/test_capabilities.py`
- `tests/decision/test_agent_descriptor.py`
- `tests/decision/test_agent_registry.py`
- `tests/adapters/test_flowise_importer.py`
- `tests/adapters/test_flowise_exporter.py`
- `tests/registry/test_descriptor_mapping.py`

## Sinnvolle Folgephase

- RoutingEngine auf Basis von `AgentDescriptor`
- Planner ueber Descriptoren und Capabilities
- NeuralPolicyModel / NN-Scoring
- weitere externe Adapter fuer n8n, OpenHands, Codex und Claude Code
