# Phase R — Domain 2: Decision / Routing / Agent Model
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**
- `managers/meta_learner.py` — PyTorch `nn.Module`-basierter MetaLearner. Kombiniert Task-Embeddings (768-dim) mit Agent-Feature-Vektoren (64-dim) via 3-Layer-MLP, gibt Score 0–1 aus. Hat `train_step()`, historische Performance-Tracking (`agent_metrics: Dict[str, List[TaskMetrics]]`), `training_history`.
- `managers/nn_manager.py` — NNManager: Wrapper um den MetaLearner. Koordiniert Training, Inferenz, Modell-Persistenz.
- `managers/hybrid_matcher.py` — HybridMatcher: Kombinierte Embedding-Similarity und NN-Scoring.
- `core/matching_engine.py` — Einfache String/Tag-Matching Engine für Agent-Auswahl.
- `core/routing/__init__.py` — HTTP-basiertes Routing: Schickt Anfragen an den `routing_agent` Microservice via HTTP.
- `services/agent_registry/` — Microservice für Agent-Registration und -Lookup.
- `training/agent_selector_model.py` (292 Zeilen) — Vollständiges PyTorch-Modell: Features werden aus TaskMetrics extrahiert, Model hat `predict()`, `update()`, Checkpoint-Save/Load.
- `training/data_logger.py` (355 Zeilen) — Loggt Trainings-Daten zu MLflow: Task-Features, Agent-Scores, Outcomes.

**Wie war die Architektur?**
- Routing war *hybrid*: Zuerst Tag-Matching, dann NN-Scoring, dann Embedding-Similarity — alle Schritte in verschiedenen Manager-Klassen verstreut.
- Training war *synchron blockierend*: `train_model()` wurde direkt in der Task-Pipeline aufgerufen.
- Agent-Registry war ein *eigener Microservice* mit eigenem Dockerfile und eigener SQLite/YAML-Persistenz.
- Keine formale `Capabilities`-Abstraction — Fähigkeiten wurden als String-Tags gespeichert.

**Welche Probleme gab es?**
- PyTorch/MLflow waren *harte Abhängigkeiten* für jede Anfrage.
- MetaLearner hatte 768-dim Embedding-Input, aber kein echtes Embedding-Modell war eingebaut: Der Input wurde oft als Zero-Vektor übergeben.
- Hybrides Routing war nicht formal definiert: Wann welcher Mechanismus dominiert war undokumentiert.
- Training konnte die Antwort-Latenz blockieren.
- Kein Capability-basiertes Filtern: Alle Agenten wurden als Kandidaten betrachtet, NN entschied allein.
- Keine formale `AgentDescriptor` Datenstruktur.

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`core/decision/` enthält:
- `routing_engine.py` — Haupt-Routing: `route_task(ctx)` → wählt Agent aus Registry, filtert Kandidaten, bewertet via neural policy, gibt `RoutingDecision` zurück.
- `neural_policy.py` — Leichtgewichtiger Policy-Scorer: `score(descriptor, context)` → Float. Kein PyTorch im Hot Path, nutzt Feature-Encoder.
- `agent_registry.py` — In-Memory Agent-Registry mit `AgentDescriptor` (capabilities, adapter_type, metadata).
- `candidate_filter.py` — Filtert Registry nach Capabilities, Verfügbarkeit.
- `capabilities.py` — Formale `AgentCapability` Enum.
- `feature_encoder.py` — Encodes Context → Float-Vektor für NN-Policy.
- `performance_history.py` — Historische Performance-Daten pro Agent.
- `scoring_models.py` — `ScoringResult` Dataclass.
- `task_intent.py` — Intent-Extraktion aus Task-String.
- `plan_builder.py` / `plan_models.py` / `planner.py` — Multi-Step-Plan-Generierung.
- `feedback_loop.py` — Feedback nach Task-Ausführung.
- `learning/` — dataset.py, trainer.py, online_updater.py, reward_model.py, persistence.py (alle leichtgewichtig, kein torch).
- `agent_creation.py` — Dynamische Agent-Erstellung.
- `agent_descriptor.py` — Formale Agent-Beschreibung.

**Wie ist es strukturiert?**
- Vollständig typisiert mit Pydantic-Modellen.
- Kein PyTorch im Hot Path — Learning ist best-effort und async-fähig.
- Capabilities sind formale Enums, kein String-Tag-Matching.
- Agent-Registry ist in-memory (kein Microservice).
- Klarer Routing-Pfad: filter → score → decide → record.

**Was wurde bewusst entfernt?**
- PyTorch MetaLearner (zu schwer für Core-Dep)
- MLflow Logging
- HTTP-basiertes Routing (Microservice-Aufruf)
- String-Tag-Matching (durch Capability-Enum ersetzt)

---

### Bewertung

**Was war früher schlechter?**
- Routing war aufgeteilt auf 3+ Klassen ohne klares Zusammenspiel.
- PyTorch als harte Dependency für jedes Routing-Lookup.
- Kein formales Capabilities-System.
- Training blockierte den Request-Pfad.

**Was ist heute besser?**
- Klarer, formaler Routing-Pfad mit definierten Interfaces.
- Capabilities sind typisiert und maschinenlesbar.
- Learning ist vollständig vom Request-Pfad getrennt (best-effort).
- Kein PyTorch im Core → leichtgewichtig, testbar ohne ML-Stack.

**Wo gab es frühere Stärken?**
- Der MetaLearner war ein *echter* neuronaler Ansatz: 768-dim Embeddings + Agent-Features → MLP Score. Obwohl der Ansatz problematisch implementiert war, war die Idee des echten Meta-Lernens wertvoller als der aktuelle lightweight Policy-Scorer.
- `training/data_logger.py` hatte *vollständiges MLflow-Tracking*: Jede Entscheidung wurde als Experiment geloggt. Das gibt eine historische Auswertbarkeit, die heute fehlt.
- `managers/performance_manager.py` hatte Latenz-Histogramme, Erfolgsraten und Trend-Analysen pro Agent.

---

### Gap-Analyse

**Was fehlt heute?**
- Kein echter Embedding-basierter Scorer: Der aktuelle FeatureEncoder ist ein einfacher numerischer Encoder ohne Semantik. Ein Task mit "write Python code" und "write Rust code" würden ähnlich encodiert.
- Kein MLflow/persistentes Experiment-Tracking der Routing-Entscheidungen.
- Kein expliziter Latenz-/Performance-Trend-Tracking pro Agent (PerformanceManager war reich an Metriken).
- Die `performance_history.py` ist vorhanden aber es ist unklar wie reich die Daten sind, die gespeichert werden.

**Welche Ideen sind verloren gegangen?**
- Semantisches Task-Embedding für besseres Matching (war in MetaLearner angelegt, aber nie mit echtem Embedding-Modell betrieben).
- A/B-Testing der Routing-Strategien (ABTestingManager).

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| MetaLearner (PyTorch MLP) | C — Idee wertvoll, Implementierung problematisch |
| MLflow Experiment-Tracking für Routing | C — wertvoll, aber heute als externes Tool |
| Semantisches Task-Embedding | C — wichtig für Routing-Qualität, aber neue Implementierung nötig |
| String-Tag-Matching | A — bewusst verworfen, Capability-Enum ist besser |
| Latenz-Trend-Tracking pro Agent | C — fehlt heute, wäre nützlich |
| HTTP-basiertes Routing | A — bewusst verworfen |
