# Phase R2 — Agent-seitige Konzepte: Assessment

## 1. AgentFactory / AgentGenerator

### Früher
- `AgentManager.create_new_agent()`: Erstellt WorkerAgent mit Domain-Knowledge-Docs, inferred Domain via Embedding-Similarity (hardcoded 3 Domains: finance/tech/marketing)
- `EnhancedAgentManager.create_new_agent()`: Async Version, ruft `AgentOptimizer.determine_domain()` (Chroma-Suche), holt Domain-Docs, generiert Prompts
- Resultat: Ein WorkerAgent mit domain_docs und prompt-Templates — keine echte KI-generierte Konfiguration

### Stärken
- Idee: Low-confidence-Routing → neue Agenten-Instanz erstellen — ist conceptual sound
- `determine_domain()` via Embedding-Similarity war technisch korrekt (wenn auch abhängig von Chroma)

### Schwächen
- Generierung war im Wesentlichen Template-Filling, nicht echte Agent-Synthese
- Hardcodierte 3 Domains (finance/tech/marketing) — kein skalierbares Domain-Modell
- WorkerAgent-Klasse direkt instanziiert — starke Kopplung

### Heute
- **AgentCreationEngine**: `should_create_agent(score)` → `create_agent_from_task()` → AgentDescriptor
- Erstellt AgentDescriptor mit inferred source_type, execution_kind, capabilities, trust_level
- Domain-Inferenz über TaskIntent
- Registriert optional in AgentRegistry
- **Beurteilung:** Heutige Implementierung ist sauberer und architekturkonformer. AgentDescriptor ist unveränderlich und validiert. Die Logik ist entkoppelt von der Ausführungsschicht.

### Was fehlt
- `AgentCreationEngine` erstellt nur Descriptors, kein echtes "Konfigurationsgenerieren" via LLM
- Kein Feedback ob ein generierter Agent tatsächlich erfolgreich war
- Kein "Agent-Improvement" nach generiertem Agent (war in `EnhancedAgentManager` vorhanden)

---

## 2. AgentImprover / Agent-Optimierung

### Früher (agent_optimizer.py + enhanced_agent_manager.py)
**Ablauf:**
1. `evaluate_agent()` → performance = 0.4 × avg_quality + 0.4 × success_rate + 0.2 × user_satisfaction
2. Wenn `performance < min_performance_threshold (0.7)`:
   - Mehr Domain-Docs aus Chroma holen
   - Prompts neu generieren (template-basiert)
   - `last_optimized` aktualisieren
3. Optimization-Loop läuft alle 24h asynchron

### Stärken der Idee
- **Kontinuierliche Agent-Verbesserung als First-Class-Citizen** — das fehlt heute vollständig
- Multi-dimensional Performance: response_quality + success_rate + user_satisfaction
- Time-based Scheduling der Optimierung

### Schwächen der Implementation
- Prompt-"Optimierung" war Template-Filling (kein LLM-basierter Ansatz)
- Domain-Docs kamen aus Chroma-Vector-Store der selten aktualisiert wurde
- `asyncio.create_task()` direkt im `__init__` — schwer testbar und fehleranfällig
- Keine Trennung zwischen Evaluation-Trigger und Optimization-Ausführung

### Heute
- **Kein Äquivalent vorhanden.** FeedbackLoop aktualisiert PerformanceHistoryStore, aber es gibt keinen Mechanismus der darauf basierend Agenten-Konfigurationen ändert.

### Was wäre heute sinnvoll?
Ein leichter **AgentHealthMonitor** als Hintergrundprozess oder CLI-Tool:
- Liest PerformanceHistoryStore
- Flaggt Agenten mit `success_rate < 0.5` oder `recent_failures > N`
- Schreibt in AgentDescriptor.metadata (z.B. `"health": "degraded"`)
- CandidateFilter kann dann degradierte Agenten niedrig priorisieren

**Keine Prompt-Manipulation, kein Chroma, kein asyncio im __init__.**

---

## 3. Supervisor / Worker — Delegation

### Früher
- `CommunicationManager`: Asynchroner In-Memory-Message-Bus
- Kein echter Supervisor/Worker-Mechanismus — Delegation war manuell über `select_agent()` → `execute()`
- Kein hierarchisches Agent-System

### Heute
- **PlanExecutionOrchestrator** ist der funktionale Nachfolger
- Step-level Routing → Execution mit parallelen Step-Groups
- Aber: kein explizites Supervisor/Worker-Muster mit delegierter Verantwortlichkeit
- Orchestrator ist zentral, nicht verteilt

### Was wäre sinnvoll?
Ein **Delegation-Konzept** im Plan: Ein Plan-Step kann einen anderen Plan delegieren (Sub-Plan). Das würde Supervisor/Worker natürlich ausdrücken. Heute: sequentielle und parallele Steps, aber keine rekursive Plan-Delegation.

---

## 4. Selbstverbesserungs- / Selbstreflexionsansätze

### Früher
- `adaptive_learning_manager.py`: NAS (Neural Architecture Search) mit zufälligen Perturbationen — **war ein Stub ohne echte Evaluation**
- `meta_learner.py`: `train_step()` mit echten PyTorch-Gradienten — war real, aber ohne persistentes Dataset
- `enhanced_agent_manager.py`: Optimization-Loop — real, aber mit template-basiertem Output

### Heute
- `core/decision/learning/`: Online-Updater, RewardModel, NeuralTrainer, TrainingDataset
- **Das ist der stärkste Fortschritt**: ein vollständiger, aber leichtgewichtiger Learning-Loop existiert im Core
- RewardModel: Strukturiertes Reward-Signal aus (success, latency, cost, capability_match)
- TrainingDataset: Append-only, deterministisch batch-fähig
- NeuralTrainer + OnlineUpdater: Saubere Trennung zwischen Batch-Training und Online-Updates

### Bewertung
Heute ist die Learning-Infrastruktur **deutlich reifer und sauberer** als früher. Das Problem der alten Manager war nicht die Idee, sondern die Implementierung.

---

## 5. Agent Profile / Skill / Capability / Matching

### Früher
- Capabilities waren implizit im WorkerAgent-Domain (finance/tech/marketing)
- Keine strukturierte Capability-Liste
- Matching via Embedding-Similarity über unstrukturierten Text

### Heute
- `Capability` Enum mit `CapabilityRisk` — explizit typisiert
- `AgentDescriptor.capabilities: list[str]` — strukturiert
- `CandidateFilter` — filtert nach required_capabilities
- `FeatureEncoder` — capability_match_score als zentrales Feature
- `TaskIntent.required_capabilities` — explizit aus Task

**Das ist heute deutlich stärker** als früher. Capabilities sind First-Class-Citizens.

### Was fehlt
- Kein Capability-Discovery-Mechanismus: Woher kommen neue Capabilities?
- Kein Capability-Inheritance (Agent A hat alle Capabilities von Agent B plus mehr)
- Kein Skill-Level innerhalb einer Capability (Basic/Advanced)

---

## 6. Agent-Memory / State

### Früher
- `knowledge_manager.py`, `domain_knowledge_manager.py`: Document-basiertes Wissen, Langchain-Wrapping
- Kein strukturierter Conversation-State-Speicher
- Kein Session-Konzept (außer `services/session_manager/` — separater Service)

### Heute
- Kein explizites Agent-Memory-Konzept im Core
- TraceStore speichert Execution-History, aber das ist Audit, kein Memory
- `ApprovalStore` ist Task-spezifisch

### Was fehlt / wäre sinnvoll?
**Kein Handlungsbedarf aktuell.** Memory für Agenten ist ein großes Topic (RAG, vector stores, episodic memory) das heute nicht nötig ist. ABrain-Agenten sind zustandslos per Design — der Zustand liegt in Plänen und Traces.

---

## 7. Zusammenfassung: Was ist heute schon enthalten?

| Konzept | Früher vorhanden | Heute im Core | Bewertung |
|---|---|---|---|
| Agent-Factory | ✅ (template-basiert) | ✅ AgentCreationEngine (sauberer) | Heute besser |
| Agent-Improvement/Lifecycle | ✅ (async loop) | ❌ fehlt | Lücke |
| Supervisor/Worker | ❌ (primitiv) | ✅ Orchestration (plan-basiert) | Heute besser |
| NeuralAgent-Scoring | ✅ (MLP, schwer) | ✅ (MLP, leicht) | Heute besser |
| Capability-Matching | ❌ (implizit) | ✅ (explizit) | Heute deutlich besser |
| Agent-Memory/State | ✅ (Langchain Docs) | ❌ (Design: zustandslos) | Bewusste Entscheidung |
| Training-Loop | ✅ (PyTorch, in-memory) | ✅ (pure Python, persistent) | Heute besser |
| Adaptive Threshold | ✅ (NNManager) | ❌ fehlt | Kleine Lücke |
| Agent-Health-Monitoring | ✅ (EnhancedAgentManager) | ❌ fehlt | Mittelgroße Lücke |

---

## 8. Was darf NICHT als managers/-Parallelwelt zurückkommen?

- `EnhancedAgentManager` als separater Service mit eigenem asyncio-Loop
- `AgentOptimizer` als zweite Routing/Entscheidungsinstanz
- `CommunicationManager` als Message-Bus (würde Orchestration umgehen)
- WorkerAgent-Klasse (war direkte Ausführungseinheit ohne Governance)
- MLflow-Run bei jedem Agent-Create-Ereignis
