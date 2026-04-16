# Phase R — Domain 1: Core Architecture
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Wie war die Architektur?**

Die ursprüngliche Architektur war monolithisch mit anschließendem Ausbau zu einem Pseudomicroservice-Modell. Die Hauptphasen:

1. **Monolith (Iteration 1–6):** Ein einzelner Python-Prozess mit allen Funktionen. Die zentralen Bausteine waren direkt eingebundene Klassen (Managers, Agents, Trainers). Die Kommunikation erfolgte synchron via Python-Objektreferenzen.

2. **Pseudomikroservices (v1.0.0 bis canonical pivot):** Jeder "Service" hatte ein eigenes Verzeichnis mit `main.py`, `routes.py`, `config.py`, `Dockerfile`, aber sie liefen meist im gleichen Prozess oder über `httpx`-Calls auf localhost. Die Trennung war mehr organisatorisch als architekturell.

**Welche Features existierten?**
- 24 Manager-Klassen (`managers/`): ABTestingManager, AdaptiveLearningManager, AgentManager, AgentOptimizer, CacheManager, CommunicationManager, DeploymentManager, DomainKnowledgeManager, EnhancedAgentManager, EvaluationManager, FaultToleranceManager, GPUManager, HybridMatcher, KnowledgeManager, MetaLearner, ModelManager, ModelRegistry, MonitoringSystem, NNManager, PerformanceManager, SecurityManager, SpecializedLLMManager, SystemManager
- 9 Service-Verzeichnisse (`services/`): agent_coordinator, agent_registry, agent_worker, coalition_manager, llm_gateway, session_manager, task_dispatcher, user_manager, vector_store
- 35+ Legacy-Flat-Files in `core/`: access_control, agent_bus, agent_evolution, coalitions, crypto, delegation, dispatch_queue, feedback_loop, governance, levels, llm_providers, matching_engine, memory_store, missions, privacy, reputation, rewards, roles, routing, self_reflection, session_store, skill_matcher, skills, teams, training, trust_circle, trust_evaluator, trust_network, voting

**Welche Probleme gab es?**
- **Keine klare Schichtentrennung:** Manager, Services und Core-Files überlappten sich. `AgentManager` und `NNManager` hatten ähnliche Verantwortlichkeiten. `training/` und `managers/adaptive_learning_manager.py` boten parallele Trainings-Pfade.
- **Zirkuläre Abhängigkeiten:** `legacy-runtime/` importierte aus `managers/`, `managers/` aus `core/`, `core/` aus `services/`. Keine definierten Modulgrenzen.
- **Zweite Wahrheit:** `core/feedback_loop.py` (alt) und `core/decision/feedback_loop.py` (neu) existierten gleichzeitig. `core/rewards.py` und `core/decision/learning/reward_model.py` idem.
- **Kein Policy-Enforcement:** Die Governance war rein konzeptuell (AgentContract-Dataclass). Es gab keinen durchgesetzten Policy-Enforcement-Pfad bei Task-Ausführung.
- **Nicht testbar ohne Infrastruktur:** Die meisten Manager importierten MLflow, PyTorch, oder andere schwere Deps. Unit-Tests waren kaum möglich ohne die gesamte ML-Infrastruktur.
- **Docker-Abhängigkeit:** Das System war konzeptuell auf Docker-Compose ausgelegt (v1.0.0 hatte 4+ docker-compose Files). Ohne Docker war Betrieb kompliziert.

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

Der kanonische Runtime-Stack ist:
```
Decision → Execution → Approval → Governance → Audit/Trace → Orchestration
```

Alle Schichten sind in `core/` als eigene Unterverzeichnisse implementiert:
- `core/decision/` — Routing, Neural Policy, Registry, Planner, Capabilities, Learning
- `core/execution/` — Dispatcher, ExecutionEngine, 6 Adapters
- `core/approval/` — HITL-Approval (Models, Policy, Store)
- `core/governance/` — PolicyEngine, PolicyRegistry, Enforcement
- `core/audit/` — TraceStore (SQLite), Trace Context, Exporters
- `core/orchestration/` — PlanExecutionOrchestrator, Resume, State (SQLite)

**Wie ist es strukturiert?**
- Ein einziger Service-Layer (`services/core.py`) verdrahtet alle kanonischen Schichten
- Ein einziges REST-API (`api_gateway/main.py`)
- Ein einziges MCP-Interface (`interfaces/mcp/`)
- Keine Parallelimplementierungen
- 161 Tests bestehen, 0 Fehler

**Was wurde bewusst entfernt?**
- Alle Manager-Klassen (ersetzt durch spezifische Layer-Module)
- Alle alten Service-Verzeichnisse (ersetzt durch `services/core.py`)
- Alle Legacy-Flat-Files in `core/` (ersetzt durch Schicht-Module)
- Docker-Compose (kein Containerinfrastruktur-Requirement mehr)

---

### Bewertung

**Was war früher schlechter?**
- Modulbegrenzungen waren unklar → Änderungen hatten unvorhersehbare Auswirkungen
- Parallele Implementierungen → kein Single Point of Truth
- Starke Abhängigkeiten (torch, mlflow, langchain) im Core → schwer zu installieren, zu testen
- Governance war nicht durchgesetzt, nur deklariert
- Kein formales Approval-/Audit-System

**Was ist heute besser?**
- Klare, lineare Schichtenarchitektur mit definierten Grenzen
- Single Source of Truth für jeden Belang
- Keine schweren ML-Deps im Kern (torch ist optional/absent)
- Governance, Approval und Audit sind strukturell erzwungen (nicht nur dokumentiert)
- Vollständig testbar ohne externe Infrastruktur

**Wo gab es frühere Stärken?**
- Die Manager-Klassen waren *reich an Features*: ABTestingManager hatte vollständige Experimente-Tracking-Logik, AdaptiveLearningManager hatte Online-Adaption, FaultToleranceManager hatte Retry/Circuit-Breaker-Muster.
- Der SystemManager konnte den Gesamtzustand des Systems überwachen (CPU, GPU, Memory, Queue-Status).
- Die Architektur war konzeptuell offen für plug-in Manager ohne Codeänderungen am Core.

---

### Gap-Analyse

**Was fehlt heute?**
- Kein SystemManager / Health-Aggregation-Layer: Heute gibt es Prometheus-Metriken und einen `/control-plane/overview`-Endpoint, aber keinen strukturierten Health-Manager der alle Subsysteme aggregiert.
- Kein Circuit-Breaker oder Retry-Logik im Execution Layer (FaultToleranceManager existierte früher).
- Kein formales Feature-Flag-System (ABTestingManager).
- Keine LLM-Provider-Abstraktion: Der kanonische Runtime hat keine direkte LLM-Anbindung mehr. Die Adapters (claudecode, codex, openhands) sind agentenspezifisch, aber es gibt kein generisches LLM-Gateway.

**Welche Ideen sind verloren gegangen?**
- Konzept des `AgentBus` (pub/sub): Die Agenten konnten Nachrichten untereinander asynchron austauschen. Heute ist die Kommunikation synchron über den Orchestrator.
- Konzept der formalen `AgentCoalition` mit Ziel, Leader und Strategie. Heute gibt es `run_plan` mit Steps, aber keine explizite Koalitions-Metapher.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| Manager-Pattern (plug-in) | Irrelevant — canonical layers sind besser |
| SystemManager/Health-Aggregation | Sinnvoll — fehlt heute |
| FaultToleranceManager (circuit breaker) | Sinnvoll — fehlt im Execution Layer |
| ABTestingManager | Irrelevant für aktuellen Fokus |
| Microservice-Struktur | Gefährlich — erzeugt Parallelarchitektur |
| AgentBus (pub/sub) | Historisch interessant; heute könnte Orchestrator diese Rolle übernehmen |
| LLM Gateway als Schicht | Sinnvoll — fehlt heute |
