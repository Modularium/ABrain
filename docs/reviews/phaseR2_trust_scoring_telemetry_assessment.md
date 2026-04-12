# Phase R2 — Trust / Scoring / Telemetry Assessment

## 1. Was war früher vorhanden?

### Trust-Score-Ansätze (MetaLearner._get_historical_performance)
```python
# Gewichtetes Score-Aggregat aus 4 Dimensionen:
# - response_time: 1/(1+t)         — niedrige Latenz → höherer Score
# - confidence_score: direkt        — Modell-Konfidenz
# - user_feedback: / 5.0            — Nutzerbewertung normalisiert
# - task_success: 0/1               — Erfolg
# → mean(scores) über letzten 100 Tasks
```

**Was war gut:**
- Multi-dimensional Trust: nicht nur success/failure, sondern Latenz + Konfidenz + User-Feedback
- Rolling Window (100 Tasks) — ältere Daten verlieren Gewicht
- Normalisierung auf [0,1]

**Was war schlecht:**
- Gleichgewichtung aller Dimensionen (keine differenzierte Gewichtung)
- `confidence_score` war unklar definiert — LLM-Konfidenz? Agent-Konfidenz?
- User-Feedback war optional und selten vorhanden → oft None-Werte

### Success-Score in NNManager
```python
success_score = float(execution_result.get("success", False))
if execution_time > 30:
    time_penalty = min(execution_time / 60.0, 0.5)
    success_score = max(0.5, success_score - time_penalty)
```
**Was war gut:** Latenz-Penalty auf Erfolgscore — macht Sinn
**Was war schlecht:** Harte Schwellenwerte (30s), keine Konfigurierbarkeit

### EvaluationManager — Metriken
- `response_time`, `token_count`, `api_cost`, `success_rate`, `user_rating`
- Zeitfenster-Filterung, Percentile (p95)
- A/B-Testing mit scipy t-Tests
- Cost-Tracking pro Service (USD)

### MonitoringSystem — Telemetrie
- MetricBuffer: O(1) Running Aggregate (sum, count, min, max)
- AlertSeverity: INFO/WARNING/ERROR/CRITICAL
- Threshold-Konfiguration: `{AlertSeverity.WARNING: 80.0, AlertSeverity.CRITICAL: 95.0}`
- Metric-Types: SYSTEM, PERFORMANCE, MODEL, BUSINESS, CUSTOM
- `check_interval = 1.0s` psutil-Loop in separatem Thread
- MLflow-Logging jeder Metrik (zu viel!)

### Routing-Entscheidungslogging (NNManager)
```python
self.experiment_tracker.log_agent_selection(
    task_description=task_description,
    chosen_agent=best_agent,
    available_agents=available_agents,
    agent_scores=agent_scores,
    execution_result={"timestamp": ...}
)
```
**War MLflow für jede Routing-Entscheidung — sehr granular, aber inkonsistent.**

---

## 2. Was davon ist heute noch wertvoll?

### A. Multi-dimensional Success-Score
**Wert heute:** Hoch. Heute hat FeedbackLoop: success (bool), latency (ms), cost (float). Das fehlt: user_feedback-Signal und token_count.

**Wo einbauen:** FeedbackUpdate um optionales `user_rating: float | None` erweitern. Approval-UI kann 1–5 Rating mitliefern wenn ein Step approved/rejected wird.

### B. Token-Tracking
**Wert heute:** Mittel. Token-Effizienz ist wichtig für Cost-Optimization. ExecutionResult hat kein `token_count`.

**Wo einbauen:** `ExecutionResult.metadata["token_count"]` ist heute möglich, wird aber nicht strukturiert befüllt. Formales Feld in ExecutionResult wäre sauber.

### C. Threshold-basierte Alerts
**Wert heute:** Mittel. Heute gibt es keine Alerts wenn Agenten dauerhaft schlechte Performance haben.

**Wo einbauen:** Governance-Layer kann PolicyRule mit Thresholds auf PerformanceHistoryStore evaluieren. Beispiel: `if recent_failures > 5 → deny with reason "agent_degraded"`. Das wäre eine saubere Integration.

### D. Routing-Entscheidungslogging
**Wert heute:** Hoch — aber heute bereits besser durch TraceStore/SpanRecord.

Heute wird jede Routing-Entscheidung in einem Trace-Span erfasst. Das ist besser als MLflow-Logging, weil SQL-querybar und strukturiert. **Kein Handlungsbedarf.**

### E. A/B-Testing für Routing
**Wert heute:** Mittel. Sinnvoll um zwei Routing-Konfigurationen objektiv zu vergleichen.

**Wo einbauen:** Leichter Mechanismus in PerformanceHistoryStore: zwei "Gruppen" von Agenten (A/B) mit getrennten Metriken. Kein scipy erforderlich — simple mean comparison reicht.

---

## 3. Was lässt sich klein und sauber in Audit / Governance / Approval / Trace integrieren?

### Governance-Integration: Agent-Health-Policy
```python
# In PolicyRegistry:
PolicyRule(
    rule_id="agent_health_check",
    condition={"recent_failures_gt": 5},
    effect="deny",
    reason="Agent shows degraded health pattern"
)
```
Kleine Erweiterung der PolicyEvaluationContext um PerformanceHistory-Daten.

### Audit/Trace-Integration: Token-Count-Span
In jedem Execution-Span: `span.attributes["token_count"] = result.metadata.get("token_count", 0)`. Kein strukturelles Change nötig — nur Befüllung.

### Approval-Integration: User-Rating
Wenn ApprovalDecision.comment einen strukturierten Score enthält (z.B. `"rating:4/5"`), kann FeedbackLoop diesen extrahieren. Minimales Interface-Contract.

---

## 4. Was sollte NICHT als altes Metrikmonster zurückkommen?

### MonitoringSystem als separater Thread
- Psutil-basiertes Echtzeit-Monitoring ist Infrastruktur-Aufgabe (Prometheus, Grafana, etc.)
- In den Core-Layer zu bringen würde Thread-Management und Platform-Dependencies einbringen
- **Kategorie A: Nicht zurückholen**

### MLflow für jede Metrik
- MLflow öffnet SQLite-Connection bei jedem `start_run()` — in einem Request-Loop inakzeptabel
- Monitoring-Daten gehören in Prometheus, nicht in MLflow
- **Kategorie A: Nicht zurückholen**

### EvaluationManager als zentraler Aggregator
- War ein God-Object: Agent-Metriken + System-Metriken + A/B-Tests + Cost-Tracking in einer Klasse
- Heute sind diese Concerns aufgeteilt: PerformanceHistoryStore (Agenten), TraceStore (Ausführungen), ServiceMetrics wäre Infrastruktur
- **Kategorie A: Nicht als Monolith zurückholen**

### Redundante MLflow + Custom Registry
- ModelRegistry + MLflow Model Registry parallel war Redundanz und Konfusion
- Heute: JSON-Weights-Persistence reicht für das kleine MLP
- **Kategorie A: Nicht zurückholen**

---

## 5. Welche konkrete Neuimplementierung wäre sinnvoll?

### Kandidat 1: FeedbackLoop.update_performance() um token_count + user_rating erweitern
```python
class FeedbackUpdate(BaseModel):
    agent_id: str
    performance: AgentPerformanceHistory
    score_delta: int
    reward: float | None = None
    token_count: int | None = None       # NEU
    user_rating: float | None = None     # NEU (0.0–1.0)
    ...
```
**Aufwand:** Klein. **Mehrwert:** Hoch. **Risiko:** Minimal.

### Kandidat 2: PolicyRule für Agent-Health-Threshold
```python
# PolicyRegistry seed:
{"rule_id": "degraded_agent_block", "condition": {"recent_failures_gte": 5}, "effect": "deny"}
```
**Aufwand:** Klein. **Mehrwert:** Hoch (verhindert Dauerversagen). **Risiko:** Minimal.

### Kandidat 3: Cost-Ceiling PolicyRule
```python
{"rule_id": "cost_ceiling", "condition": {"estimated_cost_per_token_gte": 0.01}, "effect": "require_approval"}
```
**Aufwand:** Klein (wenn PolicyEvaluationContext um Agent-Cost erweitert). **Mehrwert:** Mittel. **Risiko:** Minimal.

### Kandidat 4: Minimales A/B-Flag im FeedbackLoop
Ein `routing_experiment_group: str | None`-Feld in FeedbackUpdate das A/B-Auswertung ermöglicht ohne scipy.
**Aufwand:** Klein. **Mehrwert:** Mittel. **Risiko:** Minimal.

---

## 6. Zusammenfassung

| Komponente | Wert heute | Empfehlung |
|---|---|---|
| Multi-dim Trust Score | Hoch | C: FeedbackLoop erweitern |
| Token-Tracking | Hoch | C: ExecutionResult.token_count |
| User-Rating | Mittel | C: optional via Approval |
| Threshold-Alerts | Mittel | C: PolicyRule |
| Cost-Tracking | Hoch | C: FeedbackUpdate + PolicyRule |
| Routing-Decision-Log | — | Bereits in TraceStore: ok |
| A/B-Testing | Mittel | B: Idee merken |
| MonitoringSystem (Thread) | Niedrig | A: Infrastruktur |
| MLflow overuse | Negativ | A: Nicht zurückholen |
| EvaluationManager Monolith | Negativ | A: Nicht zurückholen |
