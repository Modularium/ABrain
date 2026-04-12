# Phase R2 — Vergleich: Agent Lifecycle / Orchestration / Coordination

## A. Früher (managers/-Welt)

### AgentManager
- WorkerAgent-Registry (Dict, in-memory)
- Domain-Inferenz via Embedding-Cosine-Similarity (finance/tech/marketing hardcoded)
- `create_new_agent()` — erstellt WorkerAgent mit Domain-Knowledge
- `select_agent()` — HybridMatcher-Delegation
- Embedding- und Feature-Cache pro Agent
- `save_state()` / `load_state()` (Matcher)
- Direktkopplung an WorkerAgent-Implementierung

### EnhancedAgentManager
- Asynchroner Lifecycle mit `asyncio.create_task()` für Optimization-Loop
- Agents als Config-Dicts mit: domain, capabilities, prompts, created_at, last_optimized, status
- `create_new_agent()` — ruft AgentOptimizer für Domain-Bestimmung + Prompt-Generierung
- `optimize_agent()` — regelmäßige Performance-Prüfung, Prompt-Update bei Underperformance
- MLflow-Run bei jedem Agent-Create und Optimize
- `get_capable_agents(capability)` — Capability-Filter
- `get_domain_agents(domain)` — Domain-Filter

### CommunicationManager
- Asynchroner In-Memory-Message-Bus zwischen Agenten
- Keine Persistenz

### SystemManager
- `asyncio.Semaphore` für max_concurrent_tasks
- Backup/Restore (tar.gz Archive)

---

## B. Heute (kanonischer Kern)

### AgentDescriptor (core/decision/)
- Strukturiertes, validiertes Modell: agent_id, display_name, source_type, execution_kind, capabilities, trust_level, cost_profile, latency_profile, availability, metadata
- Unveränderlich (Pydantic BaseModel), keine Laufzeit-Mutation
- Kein In-Memory-Lifecycle-State

### AgentRegistry (core/decision/)
- Einfache Registry: register(), get(), list_descriptors()
- Sauber isoliert, keine Lifecycle-Logik

### AgentCreationEngine (core/decision/)
- `should_create_agent(score)` — threshold-basierte Entscheidung
- `create_agent_from_task()` — generiert AgentDescriptor aus TaskContext
- Domain-Inferenz über TaskIntent
- Automatische Registrierung möglich

### Orchestration (core/orchestration/)
- **PlanExecutionOrchestrator**: Schritt-für-Schritt Plan-Ausführung
- Routing → Policy-Check → Approval → Execution → FeedbackLoop — vollständige Pipeline
- Parallel-Step-Groups möglich
- Resume-Fähigkeit (persistenter State)
- `approved_step_ids` als explizite Kontrolle

---

## C. Bewertung

| Aspekt | Früher | Heute |
|---|---|---|
| Agent-Registry | ✅ Dict (einfach) | ✅ AgentRegistry (sauber) |
| Strukturiertes Agent-Modell | ❌ Config-Dict | ✅ AgentDescriptor (Pydantic) |
| Capability-basiertes Filtering | ✅ `get_capable_agents()` | ✅ CandidateFilter |
| Domain-basiertes Filtering | ✅ `get_domain_agents()` | ✅ TaskIntent.domain |
| Agent-Lifecycle (Optimierung) | ✅ EnhancedAgentManager | ❌ fehlt |
| Periodische Agent-Optimierung | ✅ Optimization-Loop | ❌ fehlt |
| Prompt-Update bei Underperformance | ✅ AgentOptimizer | ❌ fehlt |
| Multi-Agent-Coordination | ✅ CommunicationManager (primitiv) | ✅ Orchestration (Plan-basiert) |
| Plan-basierte Ausführung | ❌ keine | ✅ PlanExecutionOrchestrator |
| Approval-Integration | ❌ keine | ✅ vollständig |
| Policy-Enforcement | ❌ keine | ✅ vollständig |
| Trace pro Agent-Aktion | ❌ nur MLflow | ✅ SQLite Trace |
| Concurrent-Task-Limit | ✅ Semaphore | ❌ (in Orchestrator konfigurierbar) |
| Dynamic Agent Generation | ✅ create_new_agent() | ✅ AgentCreationEngine |

### Was war früher besser?
- **Agent-Optimierungs-Loop**: Der Gedanke, Agenten periodisch auf Basis von Performance-Metriken zu optimieren (Prompt-Update, Domain-Refresh) — fehlt heute vollständig. Nicht als Parallelarchitektur, aber als erweiterter FeedbackLoop-Mechanismus wäre das wertvoll.
- **User-Satisfaction als Optimierungsziel**: `agent_optimizer.py` nutzte response_quality, success_rate UND user_satisfaction für Entscheidungen — heute nur success_rate + latency.

### Was ist heute klar besser?
- AgentDescriptor vs. Config-Dict: Typsicherheit, Validation, Serialisierung
- Plan-basierte Multi-Agent-Orchestration mit Resume-Capability
- Approval-Integration in den Orchestrations-Flow
- Saubere Trennung: AgentCreationEngine erzeugt Descriptors, keine Lifecycle-Kopplung

### Welche Fähigkeiten fehlen heute?
- **Kein Mechanismus für periodische Agent-Performance-Prüfung** (ist ein Agent noch gut genug?)
- **Kein Agent-Deprecation-Flow** (wann wird ein Agent aus der Registry entfernt?)
- **Kein User-Satisfaction-Signal** im FeedbackLoop

### Empfehlung
- **Periodic Performance Check**: Kategorie C — ein einfacher Background-Job oder CLI-Befehl der PerformanceHistoryStore auswertet und Agenten mit low success_rate flaggt. Kleine Erweiterung.
- **User-Satisfaction-Signal**: Kategorie C — Approval-UI kann optionales Rating mitliefern, FeedbackLoop kann es verarbeiten.
- **Agent-Deprecation**: Kategorie B — Idee gut, aber noch nicht dringend.
