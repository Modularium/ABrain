# Phase R2 — Managers Source Basis

## Ziel

Vollständige Rekonstruktion der `managers/`-Quellbasis aus der Git-Historie vor Phase O.

---

## 1. Lösch-Commit

Alle `managers/`-Dateien wurden in einem einzigen Commit gelöscht:

```
157b6bbf  feat(phaseO): canonicalization cleanup — delete all legacy code, migrate survivors
```

Der Vorgänger-Snapshot `157b6bbf^` enthält den vollständigen Stand unmittelbar vor der Bereinigung.

---

## 2. managers/ Dateien im Snapshot

| Datei | Blob-Hash | Größe (geschätzt) |
|---|---|---|
| `managers/__init__.py` | e69de29b | leer |
| `managers/ab_testing.py` | 72c31c44 | ~700 Zeilen |
| `managers/adaptive_learning_manager.py` | 1cc4edf0 | ~400 Zeilen |
| `managers/agent_manager.py` | 8242fe01 | ~280 Zeilen |
| `managers/agent_optimizer.py` | 0e980b14 | ~400 Zeilen |
| `managers/cache_manager.py` | 43194aab | ~200 Zeilen |
| `managers/communication_manager.py` | 715da7d3 | ~250 Zeilen |
| `managers/deployment_manager.py` | 909445c4 | ~300 Zeilen |
| `managers/domain_knowledge_manager.py` | ef394e6a | ~300 Zeilen |
| `managers/enhanced_agent_manager.py` | 492d2ec4 | ~300 Zeilen |
| `managers/evaluation_manager.py` | c2f9ae0e | ~500 Zeilen |
| `managers/fault_tolerance.py` | b0670b86 | ~450 Zeilen |
| `managers/gpu_manager.py` | 9508f017 | ~600 Zeilen |
| `managers/hybrid_matcher.py` | e854a827 | ~340 Zeilen |
| `managers/knowledge_manager.py` | 2c8d1180 | ~250 Zeilen |
| `managers/meta_learner.py` | 2749d007 | ~380 Zeilen |
| `managers/model_manager.py` | 6242081a | ~450 Zeilen |
| `managers/model_registry.py` | ffee17ef | ~550 Zeilen |
| `managers/monitoring_system.py` | 5e2df525 | ~600 Zeilen |
| `managers/nn_manager.py` | 30ce659a | ~220 Zeilen |
| `managers/performance_manager.py` | fb53cb54 | ~450 Zeilen |
| `managers/security_manager.py` | 1930ad97 | ~350 Zeilen |
| `managers/specialized_llm_manager.py` | da68f4b0 | ~220 Zeilen |
| `managers/system_manager.py` | e34c4e24 | ~350 Zeilen |

**Gesamt: 24 Dateien, ca. 8.500 Zeilen Code**

---

## 3. Zugehörige Begleitdateien (ebenfalls gelöscht)

### Dokumentation
| Datei | Inhalt |
|---|---|
| `docs/dev_managers.md` | Kurzübersicht aller Manager (DE) |

### Tests
- Keine dedizierten Unit-Tests für `managers/` im Snapshot gefunden.
- Tests lagen in `tests/` (allgemein) und wurden bei Phase O ebenfalls bereinigt.

### MLflow-Integration
| Datei | Inhalt |
|---|---|
| `mlflow_integration/experiment_tracking.py` | ExperimentTracker — direkter Einsatz in `nn_manager.py`, `agent_optimizer.py`, `evaluation_manager.py`, `adaptive_learning_manager.py`, `model_manager.py`, `model_registry.py` |
| `mlflow_integration/model_tracking.py` | Modell-Versioning via MLflow |
| `mlflow_integration/client.py` | Thin wrapper um MLflow Client |

→ Die `mlflow_integration/`-Verzeichnis ist **noch heute vorhanden** (`mlflow_integration/experiment_tracking.py`, `client.py`, `model_tracking.py`).

### NN-Modell-Layer
| Pfad | Eingebundene Klassen in managers/ |
|---|---|
| `nn_models/agent_nn_v2.py` | `TaskMetrics` — importiert in `meta_learner.py`, `hybrid_matcher.py`, `nn_manager.py`, `specialized_llm_manager.py` |

→ `nn_models/` noch heute vorhanden als Verzeichnis.

### Config / Providers
| Datei | Nutzung in managers/ |
|---|---|
| `config/llm_config.py` | `OPENAI_CONFIG`, `LMSTUDIO_CONFIG` — importiert in `agent_manager.py`, `agent_optimizer.py` |
| `config/__init__.py` | `LLM_BACKEND` — importiert in `agent_manager.py` |

### Agents / WorkerAgent
| Datei | Nutzung |
|---|---|
| `agents/worker_agent.py` | Basis-Worker, importiert direkt in `agent_manager.py` |

### Utils
| Datei | Nutzung |
|---|---|
| `utils/logging_util.py` | `LoggerMixin` — importiert von fast allen Managern |
| `utils/agent_descriptions.py` | `get_agent_description`, `get_agent_embedding_text`, `get_task_requirements`, `match_task_to_domain` — in `nn_manager.py` |

### Embedding / RAG
| Datei | Nutzung |
|---|---|
| `langchain_huggingface` (extern) | Embeddings in `agent_manager.py`, `nn_manager.py` |
| `langchain_openai` (extern) | Embeddings in `agent_manager.py`, `agent_optimizer.py` |
| `langchain.vectorstores.Chroma` | In `agent_optimizer.py` für Domain-Knowledge-Vector-Store |

### Ebenfalls gelöschte Manager-ähnliche Dateien (aus anderen Verzeichnissen)
| Datei | Beschreibung |
|---|---|
| `legacy runtime/session/session_manager.py` | Session-Verwaltung |
| `core/llm_providers/manager.py` | LLM-Provider-Manager |
| `mcp/session_manager/{__init__,api,main,service}.py` | MCP-Session-Service |
| `monitoring/monitoring/api/data_manager.py` | Monitoring-API-Datamanager |
| `sdk/nn_models/model_manager.py` | SDK-seitiger Model-Manager |
| `services/coalition_manager/{config,main,routes,schemas,service}.py` | Coalition-Service |
| `services/federation_manager/{config,main,routes}.py` | Federation-Service |
| `services/session_manager/{Dockerfile,__init__,config,main,routes,schemas}.py` | Session-Service (Docker) |

---

## 4. Zeitliche Einordnung der managers/-Entwicklung

| Zeitraum | Entwicklungsphase | Zugehörige Commits |
|---|---|---|
| Früh (EcoSphereNetwork-Ära) | Basismodule — Iteration 1–2 | `fd13dd3c`, `b77c3034`, `a2627bc7` |
| Iteration 3–4 | NN-Integration, Local LLM | `44ba36cf`, `b62bb8c1` |
| Iteration 5–6 | Domain Knowledge, AgentGenerator | `134e60eb`, `8f29cc44` |
| Überwachungsphase | Monitoring, A/B Testing | `86b0bd51`, `e22fff1f` |
| Bereinigung Phase O | Alle gelöscht | `157b6bbf` |

---

## 5. Vollständigkeit der Quellbasis

Die Rekonstruktion ist vollständig für:
- Alle 24 `managers/`-Python-Dateien
- MLflow-Integrationscode (noch vorhanden)
- NN-Model-Layer (`nn_models/agent_nn_v2.py`)
- Konfigurations- und Utilities-Abhängigkeiten

Nicht mehr vollständig rekonstruierbar:
- `agents/worker_agent.py` (in Phase O gelöscht)
- Dedizierte Test-Suites für `managers/`
- Ggf. Trainings-Daten / gespeicherte Modell-Gewichte
