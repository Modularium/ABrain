# Phase B Decision Layer Neural Policy Review

## Neue Module

Eingefuehrt wurden:

- `core/decision/task_intent.py`
- `core/decision/planner.py`
- `core/decision/candidate_filter.py`
- `core/decision/performance_history.py`
- `core/decision/feature_encoder.py`
- `core/decision/scoring_models.py`
- `core/decision/neural_policy.py`
- `core/decision/routing_engine.py`

## Planner

Der Planner normalisiert `TaskContext`-, `ModelContext`- oder Mapping-Eingaben und bildet sie deterministisch auf `required_capabilities` ab. V1 ist absichtlich regelbasiert statt implizit oder LLM-getrieben.

## Candidate Filtering

Der Candidate Filter ist die harte Sicherheitsgrenze. Er prueft:

- Capability Coverage
- Availability
- Trust Level
- Source-/Execution-Constraints
- optionale Human-Approval- und Certification-Hooks

Nur diese sicheren Kandidaten werden an das NeuralPolicyModel weitergegeben.

## NeuralPolicyModel

Das NeuralPolicyModel ist verpflichtend. Es besteht in V1 aus:

- deterministischem FeatureEncoder
- kleinem MLP-Scoring-Modell
- klarer Lade-/Fallback-Strategie

Wenn keine trainierten Gewichte vorhanden sind, wird ein deterministisches Startmodell geladen. Es gibt keinen Pfad ohne NN-Scoring.

## Genutzte Features

V1 nutzt pro `(Task, Agent)`-Paar:

- Task Embedding
- Capability Match Score
- Success Rate
- Average Latency
- Average Cost
- Recent Failures
- Execution Count
- Load Factor
- Trust Level
- Availability
- Cost Profile
- Latency Profile
- Source Type
- Execution Kind

## RoutingEngine

Die RoutingEngine orchestriert:

1. Planner
2. CandidateFilter
3. NeuralPolicyModel
4. Top-Kandidat-Auswahl

Sie liefert eine `RoutingDecision` mit Ranking, Auswahl und Diagnostik. Sie fuehrt keine Tasks aus.

## Legacy-Abgrenzung

Nicht mehr kanonisch fuer den Decision Layer:

- `SupervisorAgent`
- `NNManager`
- alter YAML-Regelrouter
- `MetaLearner`

Der Routing-Service wurde stattdessen zu einer duenneren Huelle auf die neue RoutingEngine reduziert.

## Tests

Hinzugekommen sind gezielte Tests fuer:

- Planner
- Candidate Filter
- Performance History
- Neural Policy
- Routing Engine
- Routing-Service-Wrapper

## Folgephasen

Sinnvolle naechste Schritte:

- Agent Creation
- Execution Adapter Layer
- spaetere kontinuierliche Lernschleife
- weitere spezialisierte Adapter
- kontrollierte MCP-Erweiterungen
