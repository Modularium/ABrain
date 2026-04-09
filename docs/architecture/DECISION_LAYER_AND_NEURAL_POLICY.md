# Decision Layer And Neural Policy

## Rolle des Decision Layers

Der Decision Layer ist die kanonische Auswahl- und Bewertungslogik von ABrain. Er entscheidet, welcher bereits bekannte Agent fuer eine Aufgabe am besten geeignet ist. Er fuehrt keine Tools aus und ersetzt nicht den gehärteten Core.

Die Zielpipeline lautet:

`Task -> Planner -> RequiredCapabilities -> CandidateFilter -> NeuralPolicyModel -> RoutingDecision`

## Klare Trennung der Teilrollen

### Planner

Der Planner normalisiert die Aufgabe und leitet daraus `TaskIntent` und `required_capabilities` ab. V1 ist bewusst regelbasiert und nachvollziehbar.

### Candidate Filter

Der Candidate Filter ist die harte Sicherheits- und Constraint-Grenze. Er laesst nur Agenten durch, die:

- alle erforderlichen Capabilities besitzen
- nicht `offline` sind
- Source-/Execution-Constraints erfuellen
- das geforderte Trust-Level erreichen
- optionale Human-Approval- oder Certification-Constraints erfuellen

### NeuralPolicyModel

Das NeuralPolicyModel ist verpflichtend. Es rankt die bereits sicher gefilterten Kandidaten. Es darf keine Agenten ausserhalb dieser sicheren Kandidatenmenge wieder einbringen.

### RoutingEngine

Die RoutingEngine orchestriert Planner, Candidate Filter und Neural Policy und gibt eine reine Entscheidungsstruktur zurueck. Sie ist kein Executor und fuehrt keine Tools oder Adapter direkt aus.

## Warum das NN verpflichtend ist

ABrain soll nicht nur deterministisch filtern, sondern auch lernfaehig priorisieren. Deshalb ist das NeuralPolicyModel kein optionaler Hook, sondern Bestandteil jedes kanonischen Routinglaufs.

Wenn keine trainierten Gewichte vorhanden sind, wird ein deterministisch initialisiertes Startmodell verwendet. Es gibt keinen Pfad "Routing ohne NN".

## Warum das NN keine Sicherheitsgrenze ersetzt

Das NN ist eine Scoring-Schicht. Sicherheitsrelevante Grenzen bleiben deterministisch:

- Capability Coverage
- Availability
- Trust-/Policy-Constraints
- spaetere Human-Approval- und Certification-Checks

Erst danach darf das NN unter den sicheren Kandidaten ranken.

## NN-Inputs in V1

Das NeuralPolicyModel nutzt pro `(Task, Agent)`-Paar mindestens:

- Task Embedding
- Capability Match Score
- Agent Performance History
- Cost
- Latency
- Success Rate

Zusaetzlich nutzt V1:

- Trust Level
- Availability
- Load Factor
- Source Type
- Execution Kind
- Cost Profile
- Latency Profile
- Recent Failures
- Execution Count

## Output

Das Modell liefert einen Score pro sicheren Kandidaten. Die RoutingEngine sortiert nach diesem Score und waehlt den Top-Kandidaten aus.

## Grenzen dieses Schritts

Nicht Teil dieses Schritts:

- Execution Adapter Ansteuerung
- kontinuierliches Training
- RL-/Bandit-Strategien
- weitere Framework-Adapter
- MCP-Erweiterung

## Legacy-Abgrenzung

Historische Pfade wie `SupervisorAgent`, `NNManager`, der alte YAML-Regelrouter und der `MetaLearner` sind nicht mehr kanonische Wahrheit des Decision Layers. Falls sie fuer Altpfade noch existieren, bleiben sie historisch und duerfen die neue Pipeline nicht ersetzen.

## Folgephasen

Sinnvolle Folgephasen nach diesem Schritt:

- Agent Creation
- Execution Adapter Layer
- kontinuierliches Lernen und Feedback-Ingestion
- weitere spezialisierte Adapter fuer n8n, OpenHands, Codex oder Claude Code
- spaetere MCP-Tool-Erweiterung
