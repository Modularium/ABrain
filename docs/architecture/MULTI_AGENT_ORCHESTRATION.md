# Multi-Agent Orchestration

Diese Architektur beschreibt den Phase-H-Stand auf dem Branch `codex/phaseH-multi-agent-orchestration`. Solange der Branch nicht gemerged ist, bleibt die Multi-Agent-Orchestrierung ein Review-/Merge-Kandidat und noch nicht Teil von `main` oder des Releases `v1.1.0`.

## Warum Multi-Agent-Orchestrierung jetzt sinnvoll ist

Der Foundations-Stack von ABrain kann bereits Intent bestimmen, sichere Kandidaten filtern, mit dem verpflichtenden NeuralPolicyModel ranken, ausfuehren und pro Execution lernen. Der naechste sinnvolle Schritt ist daher nicht eine neue Runtime, sondern eine kontrollierte Plan Execution ueber genau diesen vorhandenen Kern.

## Single-Agent Routing vs Multi-Step Plan Execution

- Single-Agent Routing:
  eine Aufgabe wird als ein Schritt betrachtet, ein Agent wird gewaehlt, dann ausgefuehrt.
- Multi-Step Plan Execution:
  eine Aufgabe wird in mehrere kontrollierte Schritte zerlegt, pro Schritt wird erneut derselbe kanonische Routing- und Execution-Pfad genutzt.

## Rollen der Kernbausteine

- `Planner`: bestimmt weiterhin Intent, Domain und RequiredCapabilities
- `PlanBuilder`: zerlegt einen Task in `PlanStep[]`
- `PlanExecutionOrchestrator`: fuehrt einen `ExecutionPlan` ueber Routing und Execution aus
- `RoutingEngine`: waehlt pro Schritt sichere Kandidaten und ranked sie mit dem NN
- `ExecutionEngine`: fuehrt die Entscheidung aus
- `FeedbackLoop`: sammelt pro Schritt Performance- und Lernsignale

## Supervisor-/Manager-Prinzip in ABrain

ABrain bleibt der zentrale Orchestrator. Spezialisierte Agenten bleiben Worker. Multi-Agent-Orchestrierung bedeutet deshalb:

- keine freie Agent-zu-Agent-Kommunikation
- keine unkontrollierten Delegationsschleifen
- keine zweite Manager-Wahrheit neben dem kanonischen Kern

Legacy-Pfade wie `SupervisorAgent`, `NNManager` oder `MetaLearner` werden nicht reaktiviert.

## Wann Schritte sequenziell sind

Sequenziell bleibt der Standard. Schritte werden nacheinander ausgefuehrt, wenn:

- spaetere Schritte Inputs aus frueheren Schritten benoetigen
- die Aufgabe ein geordnetes Arbeitsmuster hat, etwa `analyze -> implement -> test -> review`
- keine ausdrueckliche Parallelgruppe markiert ist

## Wann kontrollierte Parallelitaet erlaubt ist

V1 erlaubt Parallelitaet nur sehr begrenzt:

- nur fuer explizit markierte `allow_parallel_group`
- nur fuer unabhaengige Schritte innerhalb derselben Gruppe
- keine freie Schwarm-Logik

Der Default bleibt sequenziell.

## Wie Ergebnisse aggregiert werden

Jeder Schritt erzeugt ein strukturiertes `StepExecutionResult`. Diese Ergebnisse werden zu einem `PlanExecutionResult` aggregiert. Das Endresultat bleibt damit nachvollziehbar:

- welcher Schritt lief
- welcher Agent gewaehlt wurde
- welche Warnings entstanden
- welches Endergebnis gebildet wurde

## Sicherheitsgrenzen

Die Sicherheitsgrenzen bleiben unveraendert:

- `CandidateFilter` bleibt die harte Grenze vor dem NN
- das NeuralPolicyModel ranked nur sichere Kandidaten
- kein Agent ausserhalb der sicheren Kandidatenmenge kann ausgewaehlt werden
- keine direkte Tool- oder Adapter-Logik im Orchestrator

## Grenzen dieser Phase

- keine freie Agent-zu-Agent-Kommunikation
- keine unendlichen Delegationsschleifen
- keine graphbasierte Vollplanung
- keine komplexe Human-in-the-loop-Steuerung
- Parallelitaet bleibt klein und kontrolliert

## Folgephasen

Sinnvolle Folgephasen nach H:

- Human approval / HITL
- tiefere Parallelitaet
- capability-aware MCP expansion
- framework-spezifische Verfeinerung der Orchestrierung
