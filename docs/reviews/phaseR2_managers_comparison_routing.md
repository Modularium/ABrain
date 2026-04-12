# Phase R2 — Vergleich: Routing / Matching / Task Selection

## A. Früher (managers/-Welt)

### Features / Fähigkeiten
- **HybridMatcher**: Kombination aus drei Scores: Embedding-Kosinus-Ähnlichkeit (30%), MetaLearner-NN-Score (40%), historische Performance (30%)
- **MetaLearner**: PyTorch MLP (Input: 768-dim Task-Embedding concateniert mit 64-dim Agent-Features → 256 Hidden → 1 Score). Trainierbar via SGD+BCELoss
- **NNManager**: Embedding-basierte Selektion mit `requirement_match` (keyword-basiert, `match_task_to_domain()`) + adaptive `confidence_threshold` (selbst-adjustierend: 0.6–0.9 je nach success_rate)
- **MatchResult**: Reichhaltige Scoring-Ausgabe mit `similarity_score`, `nn_score`, `combined_score`, `confidence`, `match_details`

### Technisch Problematisches
- Schwere External-Dependencies: `torch`, `langchain_huggingface`, `langchain_openai` — startup-Zeit enorm
- `HybridMatcher` und `AgentManager` und `MetaLearner` bildeten eine enge Kopplung ohne klare Schnittstelle
- Kein deterministischer Fallback wenn Embeddings/Torch nicht verfügbar
- Embeddings wurden zur Laufzeit berechnet, kein vorab-berechneter Feature-Vektor
- `match_task_to_domain()` war string-keyword-basiert, nicht skalierbar

### Architektonische Schwächen
- Keine Policy-Schicht vor oder nach dem Routing
- Kein Approval-Schritt zwischen Auswahl und Ausführung
- Kein Trace für Routing-Entscheidungen
- Manager-Klasse hielt gleichzeitig Routing-Logik, Agent-Registry und Cache

---

## B. Heute (kanonischer Kern)

### Vorhandenes in core/decision/
- **RoutingEngine**: Saubere Kompositionsklasse (Planner + CandidateFilter + NeuralPolicyModel + PerformanceHistoryStore)
- **NeuralPolicyModel + MLPScoringModel**: Kleines deterministisches MLP (6 Hidden Units) — kein Torch, pure Python. Trainierbar über `train_step()`, persistierbar als JSON-Weights
- **FeatureEncoder**: Strukturierter, deterministischer Feature-Vektor aus AgentDescriptor + TaskIntent + PerformanceHistory
- **CandidateFilter**: Capability-basiertes Filtering vor Scoring
- **PerformanceHistoryStore**: Rolling-Average für success_rate, avg_latency, avg_cost, recent_failures — persistierbar als JSON
- **TaskIntent**: Strukturiertes Intent-Modell mit task_type, domain, risk, required_capabilities, execution_hints, description
- **RankedCandidate/RoutingDecision**: Strukturierte Ausgabe mit agent_id, score, capability_match_score, feature_summary

### Robustheit
- Keine externen ML-Dependencies im Routing-Pfad (kein torch, kein langchain)
- Vollständig deterministisch und testbar
- Policy-Check (Governance) und Approval-Request nach dem Routing
- Routing-Entscheidungen gehen durch Audit/Trace-Layer
- AgentDescriptor mit Trust-Level, Cost-Profile, Latency-Profile direkt im Routing-Input

### Was fehlt / ist reduziert
- Kein Task-Embedding im Scoring (NeuralPolicyModel nutzt handcodierte Feature-Weights, keine Sentence-Embeddings)
- Keine semantische Ähnlichkeit zwischen Task-Beschreibung und Agent-Beschreibung
- Kein self-adjusting confidence threshold
- Kein Confidence-Score in der Routing-Ausgabe
- Kein A/B-Test-Framework für Routing-Strategien

---

## C. Bewertung

| Aspekt | Früher | Heute |
|---|---|---|
| Semantisches Matching | ✅ Embedding-basiert (aber schwer) | ❌ Keyword + Feature-basiert |
| Gewichtete Multi-Score-Kombination | ✅ 3 Scores kombiniert | ✅ MLP mit feature-weights |
| Externe Dependencies | ❌ torch, langchain, HuggingFace | ✅ pure Python |
| Deterministisch | ❌ abhängig von Modell-Zustand | ✅ vollständig deterministisch |
| Policy/Approval Integration | ❌ keine | ✅ vollständig |
| Trace/Audit | ❌ keine | ✅ vollständig |
| Performance History | ✅ vorhanden (komplex) | ✅ vorhanden (einfach, sauber) |
| Trainingsfähigkeit | ✅ online trainierbar (PyTorch) | ✅ online trainierbar (pure Python) |
| Confidence-Score | ✅ vorhanden | ❌ fehlt |
| Semantic Task-Embedding | ✅ vorhanden | ❌ fehlt |

### Was war früher besser?
- **Semantic Embedding-Similarity** zwischen Task-Text und Agent-Description war eine echte Stärke. Die MatchResult.confidence erlaubte Low-Confidence-Entscheidungen explizit zu markieren.
- **Self-adjusting confidence threshold** (NNManager) war ein elegantes adaptives Element.

### Was ist heute klar besser?
- Deterministisch, policy-enforced, audit-traced — das war in der managers/-Welt komplett absent.
- Keine schweren ML-Dependencies im kritischen Routing-Pfad.
- FeatureEncoder gibt strukturierte, benannte Features — debuggbar.

### Welche Fähigkeit fehlt heute?
Ein **semantischer Similarity-Score** zwischen dem freien Task-Text und der Agent-Description (Display Name + Capabilities) ist heute nicht vorhanden. Dieser wäre als erweitertes Feature (kein Replacement) sinnvoll und ließe sich klein implementieren ohne torch.

### Empfehlung
**Kategorie C**: Als kleine architekturkonforme Neuimplementierung sinnvoll — ein leichtgewichtiger Text-Similarity-Scorer (z.B. BM25 oder TF-IDF, keine torch-Abhängigkeit) als optionales zusätzliches Feature in `FeatureEncoder` oder als separater `SemanticMatcher`-Adapter.
