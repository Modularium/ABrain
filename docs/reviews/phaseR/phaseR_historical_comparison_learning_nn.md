# Phase R — Domain 4: Learning / Feedback / NN
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**

`training/` (vollständiges ML-Trainingspaket):
- `agent_selector_model.py` (292 Zeilen) — PyTorch-Modell für Agent-Selektion: Feature-Extraktion aus TaskMetrics, `predict()`, `update()`, `train_batch()`, `save_checkpoint()` / `load_checkpoint()`. Nutzt `torch.nn.Linear`, `torch.optim.Adam`.
- `data_logger.py` (355 Zeilen) — MLflow-Tracking-Client: Loggt Experiments, Runs, Parameter, Metriken, Artefakte. Hat `CustomJSONEncoder` für Dataclasses, Enums, numpy Arrays, torch Tensors.
- `reinforcement_learning.py` (92 Zeilen) — Q-Learning für Agent-Selection: Reward-basiertes Update, `get_best_agent()`.
- `federated.py` (44 Zeilen) — Federated Learning Skeleton (FedAvg-Ansatz).
- `train.py` (242 Zeilen) — Training-Orchestration: Lädt Daten, erstellt Model, Trainingsloop mit Epochs.

`managers/`:
- `meta_learner.py` — PyTorch nn.Module MetaLearner: Task-Embedding (768-dim) + Agent-Features (64-dim) → 3-Layer-MLP → Score 0–1. Historisches Performance-Tracking.
- `adaptive_learning_manager.py` — Online-Adaption: Passt Lernraten und Gewichtungen basierend auf Feedback an.
- `ab_testing.py` — A/B-Test-Framework: Erstellt Varianten, misst Erfolgsraten, bestimmt statistischen Gewinner.
- `evaluation_manager.py` — Evaluiert Modelle: Accuracy, F1, Precision, Recall pro Agent.
- `model_manager.py` / `model_registry.py` — Modell-Verwaltung: Laden, Speichern, Versionierung von ML-Modellen.

`utils/logging_util.py` (243 Zeilen):
- MLflow-Integration direkt in der Logging-Utility.
- `CustomJSONEncoder` serialisiert PyTorch-Tensors und numpy Arrays.
- Unterstützte strukturiertes JSON-Logging und File-Logging.

**Wie war die Architektur?**
- Zentrales ML-Training-Subsystem mit PyTorch als primärer Framework.
- MLflow als Experiment-Tracker (separater MLflow-Server nötig, `mlruns/`-Verzeichnis noch im Repo).
- Training war *synchron* und konnte den Haupt-Task-Pfad blockieren.
- Separate `mlruns/` Artefakte und `models/` / `nn_models/` Verzeichnisse.
- Federated Learning war als Konzept vorhanden aber nur als Skeleton.

**Welche Probleme gab es?**
- PyTorch + MLflow = schwere Installations-Deps (~1GB+ download).
- Training blockierte Response-Latenz (`train_model()` direkt in `services/core.py`).
- MetaLearner hatte 768-dim Input aber kein Embedding-Modell → Zero-Vektor-Problem.
- MLflow-Server musste separat gestartet werden → kompliziertes Setup.
- `mlruns/` wurde in Git committed → Repository-Bloat.
- Federated Learning war nie produktiv (nur Skeleton).

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`core/decision/learning/` (5 Dateien):
- `dataset.py` — `LearningDataset`: Sammelt (context, agent_id, outcome)-Tuples. In-memory mit optionaler JSON-Persistenz.
- `reward_model.py` — `RewardModel`: Einfaches Scoring basierend auf Latenz, Erfolg, Qualität-Feedback. Kein PyTorch.
- `trainer.py` — `PolicyTrainer`: Batch-Training des PolicyScorers (leichtgewichtig). Best-effort.
- `online_updater.py` — `OnlineUpdater`: Inkrementelles Update nach jedem Task. Asynchron, blockiert nicht.
- `persistence.py` — Persistiert den Zustand des PolicyScorers zu JSON.

`core/decision/feedback_loop.py` — Verbindet Task-Ausführungsergebnisse mit dem Learning-System.
`core/decision/performance_history.py` — Hält historische Performance-Daten pro Agent.
`core/audit/` — Vollständiger Trace pro Task (kann für Learning genutzt werden).

**Wie ist es strukturiert?**
- Kein PyTorch, kein MLflow.
- Training ist vollständig non-blocking (best-effort, async).
- Persistenz via JSON (nicht ML-Artefakt-Storage).
- Keine separaten Dienste nötig.

**Was wurde bewusst entfernt?**
- PyTorch (zu schwer, kein echter Mehrwert ohne echtes Embedding-Modell).
- MLflow (zu komplex für das aktuelle Stadium).
- Synchrones Training im Request-Pfad.
- Federated Learning (zu früh).

---

### Bewertung

**Was war früher schlechter?**
- PyTorch/MLflow waren overhead ohne realen Mehrwert (kein echtes Embedding-Modell).
- Synchrones Training blockierte den Request-Pfad.
- MLflow-Server als externe Dependency.
- `mlruns/` in Git = Repository-Bloat.

**Was ist heute besser?**
- Kein Installations-Overhead.
- Non-blocking, best-effort Learning.
- Vollständig testbar ohne ML-Stack.
- Trace-Store (SQLite) bietet ein solides Fundament für späteres ML.

**Wo gab es frühere Stärken?**
- Der `data_logger.py` war ein *echter Experiment-Tracker*: Jede Entscheidung, jedes Training wurde in MLflow protokolliert. Das ermöglichte historische Analyse und Vergleich von Policy-Versionen.
- Der MetaLearner war ein *echter ML-Ansatz*: Wenn ein echtes Embedding-Modell vorhanden gewesen wäre, hätte es semantisches Routing ermöglicht.
- `training/reinforcement_learning.py` war ein einfaches aber klares Q-Learning-Gerüst für task-basiertes Lernen.
- A/B-Testing (`ab_testing.py`) ermöglichte *kontrollierte Routing-Experimente*.
- Federated Learning als Konzept (auch wenn nie implementiert) war eine architekturell interessante Idee für Multi-Node-Deployments.

---

### Gap-Analyse

**Was fehlt heute?**
- Kein Experiment-Tracker: Es ist nicht möglich, Policy-Versionen zu vergleichen oder "hat Policy v2 besser geroutet als Policy v1?" zu beantworten.
- Kein ML-Modell-Registry: Früher gab es `ModelRegistry` für Versionsverwaltung.
- Kein A/B-Testing der Routing-Policy.
- Der aktuelle `RewardModel` ist sehr einfach (Latenz + Erfolg + Qualitäts-Score). Semantisches Routing fehlt komplett.
- `performance_history.py` ist vorhanden, aber unklar wie reich die gespeicherten Daten sind und ob sie ausgewertet werden.

**Welche Ideen sind verloren gegangen?**
- Semantisches Task-Embedding für das Routing: War im MetaLearner angelegt, aber nie mit echtem Embedding-Modell verbunden.
- Federated Learning (Multi-Node Policy-Training).
- Kontrollierte A/B-Tests von Policy-Varianten.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| PyTorch MetaLearner (768-dim) | C — Idee sinnvoll, aber neues Embedding-Modell nötig |
| MLflow Experiment-Tracking | C — als externes Tool, nicht im Core |
| Synchrones Training im Request-Pfad | A — bewusst verworfen |
| Q-Learning für Routing | C — interessant, neues Design nötig |
| A/B-Testing der Routing-Policy | C — wertvoll, als eigene Schicht implementierbar |
| Federated Learning | B — historisch interessant, heute irrelevant |
| Data Logger für Policy-Decisions | D — **kritisch wertvoll**: heute fehlt jede Auswertbarkeit der Policy-Entscheidungen |
