# Phase H Review: Multi-Agent Orchestration

## Neue Orchestrierungsbausteine

Phase H fuehrt diese kanonischen Bausteine ein:

- `core/decision/plan_models.py`
- `core/decision/plan_builder.py`
- `core/orchestration/orchestrator.py`
- `core/orchestration/result_aggregation.py`
- `services/core.py` mit `run_task_plan(...)`

## Wie der PlanBuilder funktioniert

Der `PlanBuilder` nutzt weiterhin den bestehenden `Planner`, um Intent, Domain und Capabilities zu bestimmen. Darauf aufbauend erzeugt er einen `ExecutionPlan`.

V1 bleibt regelbasiert:

- einfache Tasks -> Single-Step-Plan
- komplexere Code-Tasks -> mehrstufige Plaene wie `analyze -> implement -> test -> review`
- optionale kleine Parallelgruppen nur auf expliziten Markierungen

## Wie der PlanExecutionOrchestrator funktioniert

Der Orchestrator fuehrt einen `ExecutionPlan` ueber den vorhandenen Kern aus:

1. PlanStep lesen
2. Step-Level-Routing ausfuehren
3. optional Agent Creation fuer den Schritt
4. ExecutionEngine aufrufen
5. Feedback pro Schritt erfassen
6. Resultate aggregieren

Er fuehrt selbst keine Tool- oder Adapterlogik aus.

## Step-Level-Routing

Step-Level-Routing nutzt keinen zweiten Router. Die bestehende `RoutingEngine` wird fuer `PlanStep` wiederverwendet. Candidate Filtering bleibt die harte Grenze, das NeuralPolicyModel bleibt verpflichtend.

## Aggregation

Jeder Schritt erzeugt ein `StepExecutionResult`. Diese Einzelergebnisse werden anschliessend in ein `PlanExecutionResult` ueberfuehrt. Dadurch bleibt nachvollziehbar:

- welcher Schritt lief
- welcher Agent gewaehlt wurde
- welches Output entstand
- welche Warnings aggregiert wurden

## Learning pro Schritt

Der vorhandene `FeedbackLoop` bleibt erhalten und wird pro PlanStep aufgerufen. Das Learning-System benoetigt keinen Multi-Agent-Sonderpfad. Reward, Dataset und History bleiben damit anschlussfaehig auf Schritt-Ebene.

## Bewusste Grenzen von V1

- keine freie Schwarm-Architektur
- keine unendlichen Delegationsschleifen
- keine beliebige Agent-zu-Agent-Kommunikation
- keine graphbasierte Vollplanung
- Parallelitaet nur klein und kontrolliert
- Human-in-the-loop noch nicht Teil dieser Phase

## Sinnvolle Folgephase

Nach Phase H sind als naechste Schritte sinnvoll:

- Human approval / HITL
- tiefere Parallelitaet
- capability-based MCP expansion
- framework-spezifische Verfeinerung
