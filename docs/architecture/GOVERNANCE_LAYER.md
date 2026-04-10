# Governance Layer

## Rolle der Governance Engine

Der Governance-Layer erweitert ABrain um eine deterministische Runtime-Enforcement-Schicht zwischen Routing und Execution.

Die Zielpipeline in diesem Branch lautet:

`Task -> Planner / Routing -> PolicyEngine -> (Approval?) -> Execution -> Feedback`

Policies sind dabei keine Dokumentationshilfe, sondern harte Laufzeitregeln. Sie werden fuer jede konkrete, bereits geroutete Aktion ausgewertet.

## Unterschied zu anderen Schichten

### CandidateFilter

`CandidateFilter` bleibt die harte Sicherheits- und Constraint-Grenze vor dem NeuralPolicyModel. Er bestimmt, welche Agenten ueberhaupt als sichere Kandidaten in Frage kommen.

Die Governance-Schicht ersetzt diesen Filter nicht. Sie bewertet erst danach die bereits ausgewaehlte Aktion und kann sie zusaetzlich erlauben, blockieren oder fuer Approval markieren.

### NeuralPolicyModel

Das `NeuralPolicyModel` bleibt verpflichtend und ranked nur sichere Kandidaten. Es ist lernfaehig, aber keine Governance- oder Sicherheitslogik.

### Approval Layer

Der Approval-Layer ist ein menschlicher Kontrollpunkt fuer sensible Schritte. Die Governance Engine kann `require_approval` zurueckgeben und damit denselben Pause-/Resume-Pfad nutzen. Approval ersetzt aber keine Policy-Regeln.

## Policy-Regeln

Die kanonischen Modelle liegen unter:

- `core/governance/policy_models.py`
- `core/governance/policy_registry.py`
- `core/governance/policy_engine.py`
- `core/governance/enforcement.py`

Eine Policy-Regel kann aktuell auf folgende Dimensionen matchen:

- `capability`
- `agent_id`
- `source_type`
- `execution_kind`
- `risk_level`
- `external_side_effect`
- `max_cost`
- `max_latency`
- `requires_local`

Die drei moeglichen Effekte sind:

- `allow`
- `deny`
- `require_approval`

## Evaluation und Prioritaet

Die Evaluation bleibt deterministisch:

1. passende Regeln sammeln
2. nach `priority` sortieren
3. bei gleicher Prioritaet gewinnt `deny` vor `require_approval` vor `allow`

Wenn keine Regel matcht, gilt `allow`.

## Enforcement

Die Governance Engine laeuft verpflichtend:

- in `run_task(...)`
- in `run_task_plan(...)`
- im Step-Level-Orchestrierungspfad vor jeder Step-Execution

Es gibt in diesem Branch keinen kanonischen Execution-Pfad ohne Policy-Check.

## Beispiele

### Cloud-Kostenlimit

Eine Regel kann teure Cloud-Code-Generierung blockieren, sobald ein konfigurierter Kostenschwellenwert ueberschritten wird.

### Sensitiver System- oder Workflow-Step

Eine Regel kann fuer mutierende oder externe Side-Effects `require_approval` erzwingen und damit den bestehenden Approval-Store und Resume-Pfad nutzen.

### Local-only Policy

Eine Regel kann nicht-lokale Ausfuehrungen fuer bestimmte Kontexte blockieren, ohne CandidateFilter oder Adapter-Mechaniken zu ersetzen.

## Erweiterbarkeit

V1 nutzt eine kleine, reviewbare Registry mit JSON- oder optional YAML-basiertem Laden. Es gibt keine dynamische Code-Ausfuehrung, keine Plugins und keine Blackbox.

## Grenzen dieses Schritts

- keine ML-basierte Policy-Entscheidung
- keine MCP-spezifische Governance-Oberflaeche
- keine verteilte Governance-Infrastruktur
- keine Adapter-spezifischen Freigabe-Workflows
- keine Ersetzung bestehender nativer Sicherheitsmechanismen externer Agenten

Die Governance-Schicht ist bewusst eine kleine, kanonische Runtime-Enforcement-Engine fuer den vorhandenen ABrain-Kern.
