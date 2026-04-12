# Phase R2 — Priorisierte Reimplementierungs-Kandidaten

## Bewertungsmatrix

Alle Kandidaten wurden gegen folgende Ausschlusskriterien geprüft:
- Erzeugt zweite Runtime? → **A**
- Erzeugt zweite Wahrheitsquelle? → **A**
- Umgeht Policy/Approval/Audit? → **A**
- Baut managers/ als Parallelwelt faktisch wieder auf? → **A**
- Zwingt schwere Legacy-Dependencies? → **A**
- Erhöht Komplexität stark ohne klaren Wert? → **A**

Kategorien:
- **A** = Nicht zurückholen
- **B** = Nur Idee merken, derzeit nicht sinnvoll
- **C** = Als kleine architekturkonforme Neuimplementierung sinnvoll
- **D** = Als strategisch wichtiger nächster Ausbau sinnvoll

---

## Kandidat 1 — Token-Count + API-Cost in ExecutionResult

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | `ExecutionResult` um `token_count: int` und `api_cost: float` erweitern; FeedbackLoop verarbeitet diese |
| **Früherer Ort** | `evaluation_manager.py` (EvaluationMetrics), `nn_manager.py` (time_penalty) |
| **Früherer Nutzen** | Token-Effizienz und Kosten als Optimierungssignal |
| **Frühere Schwächen** | In-Memory, kein Persistence, in Monolith-Manager |
| **Heutiger Zielort** | `core/execution/adapters/base.py` (ExecutionResult) + `core/decision/feedback_loop.py` |
| **Geschätzter Aufwand** | Klein (2–4h) |
| **Erwarteter Mehrwert** | Hoch — ermöglicht Cost-Tracking und Token-Effizienz-Metriken |
| **Architektur-Risiko** | Minimal — additiv, kein Breaking Change |
| **Priorität** | **1** |
| **Kategorie** | **C** |

---

## Kandidat 2 — Agent-Health-Policy in Governance

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | PolicyRule: wenn `recent_failures >= N` oder `success_rate < X` → Effect: "deny" oder Prioritäts-Abwertung |
| **Früherer Ort** | Implizit in `enhanced_agent_manager.py` (min_performance_threshold), `nn_manager.py` (confidence_threshold) |
| **Früherer Nutzen** | Agenten unter Schwellenwert wurden nicht mehr ausgewählt |
| **Frühere Schwächen** | War in Manager-Logik vergraben, kein formales Policy-Konzept |
| **Heutiger Zielort** | `core/governance/policy_registry.py` als PolicyRule-Seed + `PolicyEvaluationContext` um PerformanceHistory erweitern |
| **Geschätzter Aufwand** | Klein (3–5h) |
| **Erwarteter Mehrwert** | Hoch — verhindert dauerhaft schlechte Agenten in kritischen Workflows |
| **Architektur-Risiko** | Niedrig — PolicyEvaluationContext braucht eine Erweiterung |
| **Priorität** | **2** |
| **Kategorie** | **C** |

---

## Kandidat 3 — Cost-Ceiling als PolicyRule

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | PolicyRule: wenn `agent.cost_profile > max_allowed_cost` → Effect: "require_approval" oder "deny" |
| **Früherer Ort** | Kein direktes Äquivalent — nur `evaluation_manager.py` mit Cost-Tracking |
| **Früherer Nutzen** | Kosten wurden getrackt, aber nicht durchgesetzt |
| **Frühere Schwächen** | Nur Observability, keine Enforcement |
| **Heutiger Zielort** | `core/governance/policy_registry.py` — neue PolicyRule |
| **Geschätzter Aufwand** | Klein (2–3h, wenn Kandidat 1 kommt mit api_cost) |
| **Erwarteter Mehrwert** | Hoch — Budget-Governance für teure Agenten |
| **Architektur-Risiko** | Minimal — additiv |
| **Priorität** | **3** |
| **Kategorie** | **C** |

---

## Kandidat 4 — User-Rating im FeedbackLoop

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | ApprovalDecision kann optionales `rating: float (0–1)` mitbringen; FeedbackLoop extrahiert und verarbeitet es |
| **Früherer Ort** | `evaluation_manager.py` (user_rating 1–5), `meta_learner._get_historical_performance()` |
| **Früherer Nutzen** | Direktes Nutzerfeedback als Learning-Signal |
| **Frühere Schwächen** | Selten befüllt, keine strukturierte Erfassung |
| **Heutiger Zielort** | `core/approval/models.py` (ApprovalDecision um rating erweitern) + `core/decision/feedback_loop.py` |
| **Geschätzter Aufwand** | Klein (2–3h) |
| **Erwarteter Mehrwert** | Mittel — HITL-Feedback als direktes Learning-Signal |
| **Architektur-Risiko** | Minimal |
| **Priorität** | **4** |
| **Kategorie** | **C** |

---

## Kandidat 5 — Lightweight Provider-Fallback im Orchestrator

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | Wenn `ExecutionResult.success == False` und error-type ist `provider_unavailable`: Orchestrator re-routet mit `exclude=[failed_agent_id]` |
| **Früherer Ort** | `fault_tolerance.py` (konzeptionell), `model_manager.py` (verschiedene Sources) |
| **Früherer Nutzen** | Fehlertoleranz bei Provider-Ausfällen |
| **Frühere Schwächen** | War auf PyTorch-Distributed fokussiert, kein HTTP-Provider-Fallback |
| **Heutiger Zielort** | `core/orchestration/orchestrator.py` — Retry-Logik mit Exclusion-Set bei Provider-Fehler |
| **Geschätzter Aufwand** | Mittel (4–8h) |
| **Erwarteter Mehrwert** | Hoch — Resilienz bei Provider-Ausfällen |
| **Architektur-Risiko** | Niedrig — erfordert saubere Error-Classification in ExecutionResult |
| **Priorität** | **5** |
| **Kategorie** | **C** |

---

## Kandidat 6 — Agent-Performance-Health-Monitor (CLI)

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | CLI-Befehl `abrain health-check` analysiert PerformanceHistoryStore und gibt Warnung für Agenten mit `success_rate < 0.5` oder `recent_failures > N` aus; kann auch AgentDescriptor.metadata["health"] setzen |
| **Früherer Ort** | `enhanced_agent_manager.py` (_run_optimization_loop), `evaluation_manager.py` |
| **Früherer Nutzen** | Automatische Erkennung von underperformenden Agenten |
| **Frühere Schwächen** | Asynchroner Loop in __init__, Prompt-"Optimierung" war Stub |
| **Heutiger Zielort** | CLI-Command + PerformanceHistoryStore (read-only Analyse) |
| **Geschätzter Aufwand** | Klein (3–4h) |
| **Erwarteter Mehrwert** | Mittel — Ops-Tool für Agent-Qualitätskontrolle |
| **Architektur-Risiko** | Minimal — read-only Analyse |
| **Priorität** | **6** |
| **Kategorie** | **C** |

---

## Kandidat 7 — Semantic Text-Similarity als optionales Routing-Feature

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | Leichtgewichtiger BM25/TF-IDF-Scorer der Task-Beschreibung gegen AgentDescriptor-Felder (display_name + capabilities) matcht; Score geht als `semantic_match_score` in FeatureEncoder |
| **Früherer Ort** | `hybrid_matcher.py` (Embedding-Cosine-Similarity), `agent_manager.py` (_infer_domain) |
| **Früherer Nutzen** | Semantisches Matching über unstrukturierte Task-Texte |
| **Frühere Schwächen** | Schwere torch/langchain-Dependencies, langsam beim Start |
| **Heutiger Zielort** | `core/decision/feature_encoder.py` als optionaler Scorer (kein torch) |
| **Geschätzter Aufwand** | Mittel (6–10h, BM25-Implementierung ohne externe Deps) |
| **Erwarteter Mehrwert** | Mittel — verbessert Matching bei freiem Task-Text |
| **Architektur-Risiko** | Niedrig — additives Feature, kein Breaking Change |
| **Priorität** | **7** |
| **Kategorie** | **D** |

---

## Kandidat 8 — Adaptiver Confidence-Threshold für AgentCreationEngine

| Feld | Wert |
|---|---|
| **Kurzbeschreibung** | `AgentCreationEngine.threshold` adaptiert sich basierend auf globalem `success_rate` des PerformanceHistoryStore: hohe Success-Rate → niedrigerer Threshold (weniger neue Agenten); niedrige Success-Rate → höherer Threshold |
| **Früherer Ort** | `nn_manager.py` (_update_parameters) |
| **Früherer Nutzen** | Selbst-kalibrierender Schwellenwert für Agent-Generierung |
| **Frühere Schwächen** | Kein Cooldown, no lower/upper bounds |
| **Heutiger Zielort** | `core/decision/agent_creation.py` |
| **Geschätzter Aufwand** | Klein (2–3h) |
| **Erwarteter Mehrwert** | Mittel |
| **Architektur-Risiko** | Minimal |
| **Priorität** | **8** |
| **Kategorie** | **C** |

---

## Ausgeschlossene Kandidaten (Kategorie A)

| Kandidat | Grund für Ausschluss |
|---|---|
| `MonitoringSystem` (Thread + psutil) | Infrastruktur-Aufgabe (Prometheus), Thread-Management im Core |
| `GPUManager` | Kein GPU-Workload im ABrain-Core |
| `FaultHandler` (PyTorch-Distributed) | Falsche Schicht, keine relevanten Fehler-Typen |
| `PerformanceManager` (Redis + Batch-Queue) | Redis-Dependency, Overengineering für aktuellen Scale |
| `DeploymentManager` (Docker API) | Infrastruktur, nicht Core-Aufgabe |
| `CommunicationManager` (Message-Bus) | Würde Orchestration umgehen |
| `MLflow in jedem Manager` | Anti-Pattern, kein zentraler Kontrollpunkt |
| `EnhancedAgentManager` als Service | Würde parallele Agent-Runtime aufbauen |
| `AdaptiveLearningManager` (NAS-Stub) | War Stub ohne echte Evaluation |
| `SecurityManager` (JWT + Prompt-Filter) | Ist Aufgabe der API-Gateway/Auth-Schicht |

---

## Kandidaten Kategorie B (Idee merken)

| Kandidat | Grund |
|---|---|
| A/B-Testing für Routing-Strategien | Wert vorhanden, aber heute kein konkreter Anwendungsfall ohne produktiven Traffic |
| Agent-Deprecation-Flow | Sinnvoll aber noch nicht dringend |
| Neural Architecture Search | Idee gut, Implementation aufwändig, heutiges MLP reicht |
| Coalition/Federation Manager | Interessante Verteilungsideen, heute überfrüh |

---

## Priorisierungs-Zusammenfassung

| Rang | Kandidat | Aufwand | Mehrwert | Kategorie |
|---|---|---|---|---|
| 1 | Token-Count + API-Cost in ExecutionResult | Klein | Hoch | C |
| 2 | Agent-Health-Policy in Governance | Klein | Hoch | C |
| 3 | Cost-Ceiling als PolicyRule | Klein | Hoch | C |
| 4 | User-Rating im FeedbackLoop | Klein | Mittel | C |
| 5 | Provider-Fallback im Orchestrator | Mittel | Hoch | C |
| 6 | Agent-Health-Monitor CLI | Klein | Mittel | C |
| 7 | Semantic Text-Similarity im FeatureEncoder | Mittel | Mittel | D |
| 8 | Adaptiver Confidence-Threshold | Klein | Mittel | C |
