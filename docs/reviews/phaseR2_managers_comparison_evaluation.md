# Phase R2 — Vergleich: Trust / Scoring / Evaluation / Telemetry

## A. Früher (managers/-Welt)

### EvaluationManager
- **Pro-Agent-Metriken**: `response_time`, `token_count`, `api_cost`, `success_rate`, `user_rating (1–5)`
- **Statistik**: Percentile (p95), Mean, Min/Max über Zeitfenster
- **A/B-Tests**: Vollständiges Framework mit scipy t-Tests, Signifikanzniveaus (0.01/0.05/0.1), min_samples, max_duration
- **Cost-Tracking**: Per-Service-Kostenverfolgung (USD), tägliche Durchschnitte
- **Export/Import**: JSON-Serialisierung der gesamten Metriken-Basis

### MonitoringSystem
- **Echtzeit-Monitoring**: Thread-basiert, MetricBuffer mit O(1)-Aggregaten
- **Threshold-Alerts**: AlertSeverity (INFO/WARNING/ERROR/CRITICAL), Alert-Callbacks
- **System-Metriken**: psutil-basiert: CPU%, Memory%, GPU% (pynvml)
- **MLflow-Integration**: Jede Metrik → MLflow-Run
- **Konfigurierbar**: MetricConfig mit Typ, Einheit, Thresholds, Aggregation, Retention

### MetaLearner._get_historical_performance()
- Gewichtetes Score-Aggregat aus:
  - `response_time` → 1/(1+t) normalisiert
  - `confidence_score`
  - `user_feedback` (1–5 normalisiert auf 0–1)
  - `task_success` (bool)
- Letzte 100 Tasks als Rolling Window

### ABTest (ab_testing.py)
- Vollständiges scipy-basiertes A/B-Framework
- `ttest_ind`, `chi2_contingency` — korrekte statistische Tests
- Traffic-Split konfigurierbar, multiple Varianten
- Min-Samples und Max-Duration Guards
- Statistisch: Winner-Bestimmung, p-value, Effect-Size

---

## B. Heute (kanonischer Kern)

### PerformanceHistoryStore (core/decision/)
- `success_rate` (rolling avg), `avg_latency`, `avg_cost`, `recent_failures`, `execution_count`, `load_factor`
- `record_result()` — saubere Rolling-Update-Logik
- JSON-persistierbar
- Wird direkt in FeatureEncoder und FeedbackLoop genutzt

### FeedbackLoop (core/decision/)
- `update_performance()` — sammelt Execution-Outcomes
- Approval-Status-Filter (rejected/cancelled/expired → kein Learning)
- Optionaler Online-Updater für Neural Policy
- `score_delta` im FeedbackUpdate

### AuditLog + TraceStore (core/audit/)
- SQLite-Persistenz für Traces, Spans, ExplainabilityRecords
- Strukturierte SpanRecord mit Timing, Status, Events
- ExplainabilityRecord für Human-readable Decision-Erklärungen
- Verwendung durch Orchestration und Execution

### Governance-Layer (core/governance/)
- PolicyDecision mit Effect, Matched Rules
- Kein direktes Scoring, aber Policy-basiertes Blocking

---

## C. Bewertung

| Aspekt | Früher | Heute |
|---|---|---|
| Per-Agent-Metriken (Kosten, Latenz, Success) | ✅ EvaluationManager | ✅ PerformanceHistoryStore |
| A/B-Testing | ✅ vollständig (scipy) | ❌ fehlt |
| User-Rating-Erfassung | ✅ 1–5 Skala | ❌ fehlt |
| Cost-Tracking (USD, pro Service) | ✅ detailliert | ❌ fehlt |
| Real-time System-Metriken (CPU/Mem/GPU) | ✅ MonitoringSystem | ❌ fehlt |
| Threshold-Alerts | ✅ konfigurierbar | ❌ fehlt |
| Trace/Span-Persistenz | ❌ keine | ✅ SQLite |
| Policy-Enforcement-Logging | ❌ keine | ✅ vollständig |
| Statistical Significance Testing | ✅ scipy-basiert | ❌ fehlt |
| Export/Import von Metriken | ✅ JSON | ✅ JSON (PerformanceHistory) |

### Was war früher besser?
- **A/B-Testing mit scipy-Statistik** — kein Äquivalent heute. War technisch korrekt implementiert.
- **Cost-Tracking** (api_cost in USD, per Service) — fehlt heute vollständig.
- **User-Rating** (1–5) als direktes Feedback-Signal — fehlt heute.
- **Echtzeit-Monitoring** (CPU/Memory/GPU mit Alerts) — fehlt in der Core-Schicht (wäre eher Infrastruktur).
- **EvaluationMetrics.token_count** — Token-Effizienz wurde getrackt, heute nicht.

### Was ist heute klar besser?
- **TraceStore/SQLite**: Dauerhafte, strukturierte Trace-Persistenz — die managers/ hatten nur In-Memory + MLflow.
- **Policy-Enforcement** mit Logging — gab es früher nicht.
- **Approval-Status-Filter im FeedbackLoop** (rejected → kein Learning) — elegante Architektur.

### Welche Fähigkeiten fehlen heute?
1. **Cost-Tracking pro Execution** (API-Kosten in USD) → kleine Erweiterung von PerformanceHistoryStore/FeedbackLoop
2. **Token-Effizienz-Tracking** (token_count) → kann in ExecutionResult ergänzt werden
3. **A/B-Testing-Mechanismus** für Routing-Strategien → könnte als leichtes Framework in governance/ oder orchestration/ sitzen
4. **User-Feedback-Erfassung** (1–5) → Approval-UI könnte Rating mitbringen

### Empfehlung
- **Cost-Tracking**: Kategorie C — kleine Ergänzung im FeedbackLoop/PerformanceHistoryStore
- **Token-Tracking**: Kategorie C — ExecutionResult um `token_count` erweitern
- **A/B-Testing**: Kategorie B — Idee merken, derzeit zu viel Overhead
- **Echtzeit-System-Monitoring**: Kategorie A — nicht zurückholen, ist Infrastruktur-Aufgabe (Prometheus/Grafana)
