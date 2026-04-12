# Phase R2 — Managers Domain Map

## Funktionale Gruppierung der alten managers/-Welt

---

## Gruppe A — Agent Orchestration / Supervision

### Aufgabe
Verwaltung des Lebenszyklus von Agenten: Erstellung, Auswahl, Aktualisierung, Deaktivierung.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `agent_manager.py` | `AgentManager` | WorkerAgent-Registry, Embedding-basierte Auswahl, HybridMatcher-Delegation |
| `enhanced_agent_manager.py` | `EnhancedAgentManager` | Asynchroner Lifecycle, MLflow-Integration, periodische Optimierung |

### Reife / Produktivität
- **Mittel** — funktionsfähige Basislogik, aber stark an alte WorkerAgent-Klasse gekoppelt
- Synchrone und asynchrone Implementierungen parallel vorhanden (Architekturkonfusion)
- MLflow-Logging direkt in Agent-Lifecycle-Methoden vermischt

---

## Gruppe B — Routing / Matching / Task Selection

### Aufgabe
Intelligente Auswahl des besten Agenten für eine Aufgabe.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `hybrid_matcher.py` | `HybridMatcher` | Kombination aus Embedding-Kosinus-Ähnlichkeit + MetaLearner-NN-Score + historischer Performance |
| `nn_manager.py` | `NNManager` | HuggingFace-Embeddings, requirement matching, ExperimentTracker, adaptive confidence threshold |
| `meta_learner.py` | `MetaLearner` | PyTorch MLP (768+64→256→1), trainiert auf Task-Embedding × Agent-Features → Erfolgswahrscheinlichkeit |

### Reife / Produktivität
- **Hoch konzeptionell, niedrig praktisch**
- MetaLearner war die stärkste Idee: neuronale Kombination von Task + Agent-Feature-Vektoren
- Aber: schwere externe Abhängigkeiten (torch, langchain, HuggingFace), nicht isolierbar
- NNManager hatte self-adjusting confidence threshold — interessantes adaptives Element

---

## Gruppe C — Memory / Context / Session

### Aufgabe
Persistenz von Sitzungszustand, Kontext, Agentenwissen.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `knowledge_manager.py` | `KnowledgeManager` | Verwaltung von Wissensbasis-Dokumenten |
| `domain_knowledge_manager.py` | `DomainKnowledgeManager` | Domain-spezifische Wissenspflege und -abruf |
| `cache_manager.py` | `CacheManager` | Embedding-/Inference-Caching |

### Reife / Produktivität
- **Niedrig** — einfache Wrapper, keine echte Persistenz-Strategie
- Keine strukturierte State-Serialisierung
- KnowledgeManager weitgehend Wrapper um Langchain-Objekte

---

## Gruppe D — Learning / Training / Feedback

### Aufgabe
Lernschleifen: Feedback aus Agenten-Ausführungen → Modell-Updates.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `adaptive_learning_manager.py` | `AdaptiveLearningManager` | Experiment-Management, Neural Architecture Search (random perturbation), MLflow |
| `meta_learner.py` | `MetaLearner.train_step()` | One-step SGD update via BCELoss |
| `nn_manager.py` | `NNManager.update_model()` | Performance history, confidence threshold adaptation |

### Reife / Produktivität
- **Niedrig-Mittel** — `AdaptiveLearningManager._evaluate_variant()` war ein Platzhalter (np.random)
- `MetaLearner.train_step()` war echtes PyTorch-Training, aber ohne persistente Datenbasis
- Kein strukturiertes Dataset, kein Replay-Buffer, keine Reward-Funktion

---

## Gruppe E — Trust / Scoring / Evaluation

### Aufgabe
Qualitätsbewertung von Agenten-Ausführungen.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `evaluation_manager.py` | `EvaluationManager` | Per-Agent-Metriken (response_time, token_count, api_cost, success_rate, user_rating), A/B-Test-Framework (scipy), Cost-Tracking |
| `meta_learner.py` | `MetaLearner._get_historical_performance()` | Gewichtetes Score-Aggregat aus response_time, confidence, user_feedback, task_success |
| `ab_testing.py` | `ABTesting`, `ABTest`, `Variant` | Vollständiges A/B-Test-Framework mit scipy-Statistik, Signifikanztests, MLflow-Logging |

### Reife / Produktivität
- **Hoch** — `EvaluationManager` war der ausgereifteste Manager im Portfolio
- A/B-Testing (`ab_testing.py`) war vollständig implementiert mit scipy t-Tests
- Cost-Tracking mit MLflow-Integration vorhanden

---

## Gruppe F — LLM Provider Abstraction

### Aufgabe
Abstraktion über verschiedene LLM-Backends (OpenAI, LM Studio, HuggingFace lokal).

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `specialized_llm_manager.py` | `SpecializedLLMManager` | Domain-spezifische Modell-Configs, Training-Status, Best-Model-Selektion |
| `model_manager.py` | `ModelManager` | Lädt Modelle von LOCAL / HUGGINGFACE / OPENAI, MLflow-tracking |
| `config/llm_config.py` | — | `OPENAI_CONFIG`, `LMSTUDIO_CONFIG` — YAML-/Dict-basiert |

### Reife / Produktivität
- **Mittel** — `ModelManager` hatte gute Struktur mit klarem Source-Enum
- `SpecializedLLMManager` war konzeptionell interessant: domain-spezifische Modell-Auswahl
- Aber: OpenAI-API hatte Bugs (`.aretrive` statt `.aretrieve`)
- Keine echte Abstraktion über alle Backends hinweg

---

## Gruppe G — Agent Generation / Improvement

### Aufgabe
Automatische Erstellung und Verbesserung von Agenten-Konfigurationen.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `agent_optimizer.py` | `AgentOptimizer` | Domain-Bestimmung via Chroma/Embeddings, Prompt-Optimierung, Leistungsbewertung, MLflow |
| `adaptive_learning_manager.py` | `AdaptiveLearningManager` | NAS — Architektur-Varianten generieren und evaluieren |

### Reife / Produktivität
- **Mittel** — `AgentOptimizer.determine_domain()` war konzeptionell stark: Embedding-basierte Domain-Erkennung
- Prompt-Optimierung war Basis-Template-Filling, kein echter LLM-basierter Ansatz
- NAS-Loop in `AdaptiveLearningManager` war ein Stub (zufällige Metriken)

---

## Gruppe H — Workflow / Coordination / Delegation

### Aufgabe
Koordination zwischen mehreren Agenten, Task-Delegation.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `communication_manager.py` | `CommunicationManager` | Asynchrone Nachrichten zwischen Agenten |
| `system_manager.py` | `SystemManager` | Task-Semaphore (max_concurrent_tasks), Backup/Restore |

### Reife / Produktivität
- **Niedrig** — `CommunicationManager` war ein einfacher In-Memory-Message-Bus
- Keine echte Workflow-Engine, kein Plan-Konzept
- `SystemManager.task_semaphore` war die einzige primitive Concurrency-Control

---

## Gruppe I — Telemetry / MLflow / Logging

### Aufgabe
Metriken sammeln, Experimente tracken, Systemzustand loggen.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `monitoring_system.py` | `MonitoringSystem` | Thread-basiertes Echtzeit-Monitoring, MetricBuffer mit Threshold-Alerts, psutil (CPU/Memory/GPU), MLflow |
| `evaluation_manager.py` | `EvaluationManager` | Agent-Metriken, Cost-Tracking, System-Metriken |
| `mlflow_integration/experiment_tracking.py` | `ExperimentTracker` | Thin wrapper, in fast allen Managern genutzt |

### Reife / Produktivität
- **Hoch konzeptionell** — `MonitoringSystem` hatte reife Struktur: MetricConfig, MetricBuffer, AlertSeverity, Threshold-Checks
- Thread-basiert (psutil-Loop) war einfach und funktional
- MLflow-Logging war allgegenwärtig, aber inkonsistent eingebunden

---

## Gruppe J — System Health / Optimization / Infrastructure

### Aufgabe
Ressourcenverwaltung, Skalierung, Deployment.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `performance_manager.py` | `PerformanceManager` | Redis-Cache für Inference, Batch-Processing-Queue, Worker-Load-Balancing |
| `gpu_manager.py` | `GPUManager` | NVML-basiertes GPU-Monitoring, Mixed Precision, Distributed Training Setup, CUDA-Graph-Optimization |
| `fault_tolerance.py` | `FaultHandler` | Prozess-Recovery, GPU-Fehler-Behandlung, Signal-Handler |
| `deployment_manager.py` | `DeploymentManager` | Docker-basiertes Deployment |
| `system_manager.py` | `SystemManager` | Backup/Restore, psutil-Metriken |

### Reife / Produktivität
- `GPUManager` — technisch sehr detailliert, aber kaum relevant ohne echten GPU-Workload
- `FaultHandler` — PyTorch-Distributed-Fokus, zu speziell
- `PerformanceManager` — Redis-Dependency, guter Ansatz für Caching aber overengineered
- `DeploymentManager` — Docker-API-Abhängigkeit, nicht portable

---

## Gruppe K — Model Registry / Versioning

### Aufgabe
Versionierung und Auswahl von ML-Modellen.

### Klassen/Dateien
| Datei | Hauptklasse | Kernfunktion |
|---|---|---|
| `model_registry.py` | `ModelRegistry` | PyTorch state_dict-Versionierung, Hash-basierte IDs, MLflow-Logging, compare_versions, get_best_version |
| `model_manager.py` | `ModelManager` | Modell-Loading (LOCAL/HF/OpenAI), Versions-Listing |

### Reife / Produktivität
- **Hoch konzeptionell** — `ModelRegistry` war ausgereift: Hash-IDs, max_versions, get_best_version, DataFrame-Vergleich
- Aber ausschließlich auf PyTorch-Modelle ausgerichtet
- MLflow-Doppelspurig neben eigenem Registry (Redundanz)

---

## Zusammenfassung: Reifegrade pro Gruppe

| Gruppe | Reife | Architekturqualität | Praktischer Wert |
|---|---|---|---|
| A – Agent Orchestration | Mittel | Schlecht (Kopplung) | Niedrig |
| B – Routing / Matching | Hoch (Idee) | Mittel | Mittel |
| C – Memory / Context | Niedrig | Schlecht | Sehr niedrig |
| D – Learning / Feedback | Niedrig-Mittel | Schlecht (Stub) | Niedrig |
| E – Trust / Scoring / Evaluation | Hoch | Mittel | **Hoch** |
| F – LLM Provider Abstraction | Mittel | Mittel | Mittel |
| G – Agent Generation | Mittel | Schlecht | Mittel |
| H – Workflow / Coordination | Niedrig | Schlecht | Niedrig |
| I – Telemetry / MLflow | Hoch | Mittel | **Hoch** |
| J – System Health / Infra | Hoch (Technik) | Schlecht (Overeng.) | Niedrig |
| K – Model Registry | Hoch | Gut (für PyTorch) | Mittel |
