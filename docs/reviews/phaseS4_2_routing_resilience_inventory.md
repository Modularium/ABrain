# Phase S4.2 — Soft Fallback & Routing Preferences: Inventory

**Branch:** `codex/phaseS4-2-soft-fallback-and-routing-preference`
**Date:** 2026-04-13
**Scope:** Vorab-Intelligenz im Routing — Confidence, Health, Cost. Keine neue Runtime.

---

## 1. Hard Fallback (S4) vs Vorab-Routing (S4.2)

| Merkmal | S4 Hard-Fallback | S4.2 Vorab-Intelligenz |
|---|---|---|
| Auslöser | Execution schlägt fehl (Infra-Fehler) | Vor der Execution: schlechte Kandidatenlage |
| Zeitpunkt | Nach `execution_engine.execute()` | In `route_intent()` / vor Governance |
| Ergebnis | Anderer Agent wird ausgeführt | Besserer Agent wird von Anfang an gewählt |
| Governance | Immer neu erzwungen für Fallback-Agent | Normal — kein Sonderfall |
| Feedback | Primärfehler + Fallback-Ergebnis getrennt | Normal — ein Ergebnis |
| Bounded | Explizit: max. ein Versuch | Konzeptionell: Auswahl = einmal |

**Trennlinie:** S4.2 greift bei der *Entscheidung*, S4 greift bei der *Ausführung*.

---

## 2. Heutige Architektur: Canonical Routing Path

```
RoutingEngine.route_step(step, task, descriptors, *, exclude_agent_ids=None)
  │
  ├─ [S4] exclude_agent_ids pre-filter
  │
  ├─ TaskIntent aufbauen
  │
  └─ route_intent(intent, descriptors)
       ├─ CandidateFilter.filter_candidates()   [harte Policy: OFFLINE, capabilities, trust]
       ├─ NeuralPolicyModel.score_candidates()  [MLP-Scoring: capability, history, cost, latency]
       └─ RoutingDecision(selected_agent_id, ranked_candidates, diagnostics)
```

**Heute fehlende Signale:**
- Keine explizite `routing_confidence` im `RoutingDecision`
- Kein `score_gap` zwischen #1 und #2
- DEGRADED-Verfügbarkeit wird nicht separat penalisiert (nur indirekt via MLP-Feature `availability`)
- Kein Cost-Tie-Breaking: bei gleichem Score gewinnt der erste im Feld
- Feature-Encoder: `availability` nutzt `_enum_ratio` statt `_inverse_enum_ratio` — DEGRADED wird deshalb MLP-intern als "höherer Wert" kodiert, was dem positiven Gewicht keine sinnvolle Penalisierung gibt

---

## 3. Wo S4.2 architekturkonform eingreift

**Einziger Einhängepunkt: `route_intent()` in `RoutingEngine`**

```
[S4.2 Additions]
NeuralPolicyModel.score_candidates()
  → scored_candidates

+ _apply_degraded_penalty(scored, descriptors_by_id, multiplier)
  → re-sort DEGRADED-Agenten nach unten

+ _apply_cost_tiebreak(scored, descriptors_by_id, band)
  → innerhalb Score-Band: günstiger gewinnt

+ _compute_routing_metrics(scored)
  → routing_confidence, score_gap, confidence_band

→ RoutingDecision(... routing_confidence=..., score_gap=..., confidence_band=...)
```

**In `orchestrator._execute_step()`:** Minimale Ergänzung:
- `routing_confidence`, `score_gap`, `confidence_band` in routing_span-Attributen
- `add_span_event("routing_low_confidence")` wenn `confidence_band == "low"`

---

## 4. Bestehende Signale, die S4.2 nutzt

| Signal | Quelle | Heute schon im Routing? |
|---|---|---|
| `success_rate` | `PerformanceHistoryStore` | ✓ via MLP-Feature |
| `recent_failures` | `PerformanceHistoryStore` | ✓ via MLP-Feature (bounded_inverse) |
| `avg_latency` | `PerformanceHistoryStore` | ✓ via MLP-Feature |
| `avg_cost` | `PerformanceHistoryStore` | ✓ via MLP-Feature |
| `load_factor` | `PerformanceHistoryStore` | ✓ via MLP-Feature |
| `availability` | `AgentDescriptor` | ✓ via MLP-Feature (aber Encoding-Bug: DEGRADED > ONLINE) |
| `cost_profile` | `AgentDescriptor` | ✓ via MLP-Feature (inverse_enum_ratio) |
| `trust_level` | `AgentDescriptor` | ✓ via MLP-Feature |

**S4.2 Neuzugänge (explizit, nicht im MLP):**
| Signal | Neu in | Verwendung |
|---|---|---|
| `degraded_availability_penalty` | `RoutingPreferences` | Score-Multiplikator für DEGRADED nach MLP-Scoring |
| `cost_tie_band` | `RoutingPreferences` | Tie-Breaking innerhalb Band |
| `routing_confidence` | `RoutingDecision` | Audit/Trace + Span-Event bei "low" |
| `score_gap` | `RoutingDecision` | Audit/Trace |
| `confidence_band` | `RoutingDecision` | Audit/Trace + Span-Event |

---

## 5. Invarianten, die nicht verletzt werden dürfen

1. **Kein Governance-Bypass.** S4.2 ändert die Routing-Entscheidung vor Governance. Governance läuft immer noch für den final ausgewählten Agenten.

2. **Kein zweiter Orchestrator.** `route_intent()` ist ein Methodenaufruf im bestehenden Pfad — keine neue Runtime.

3. **Keine neue Retry-Logik.** S4.2 wählt einmal den besten Kandidaten. Kein While-Loop, keine Kaskade.

4. **Bounded.** Tie-Breaking ist deterministisch und endet nach einem Durchlauf.

5. **S4 Hard-Fallback bleibt unberührt.** `_apply_degraded_penalty` und `_apply_cost_tiebreak` laufen in `route_intent()`, nicht in `_attempt_fallback_step()`. Die S4-Exclusion-Logik (`exclude_agent_ids`) ist orthogonal dazu.

6. **Feedback-Semantik unverändert.** S4.2 ändert nur die Auswahl vor der Execution — die Feedback-Pfade (S3/S4) bleiben exakt identisch.

7. **Rückwärtskompatibel.** `RoutingPreferences` hat Defaults, bei denen die neuen Felder (`degraded_availability_penalty=0.85`, `cost_tie_band=0.05`) nur bei tatsächlich degradierten Agenten oder sehr engen Score-Bändern wirken.

---

## 6. Was S4.2 NICHT tut

- Kein Budgeting- oder Billing-Subsystem
- Kein Background-Health-Monitor
- Keine Registry-Mutation zur Laufzeit
- Keine neue Entscheidungs-Engine
- Keine automatische Approval-Eskalation bei low confidence (das wäre S2-Governance-Sache)
- Kein generisches Multi-Retry
- Keine parallele Mehrfachausführung

---

## 7. Files Changed in S4.2

| File | Change |
|---|---|
| `core/decision/routing_engine.py` | `RoutingPreferences` model, neue Felder auf `RoutingDecision`, `RoutingEngine.__init__` erweitert, drei Hilfsfunktionen, `route_intent()` Erweiterung |
| `core/decision/__init__.py` | `RoutingPreferences` exportieren |
| `core/orchestration/orchestrator.py` | `routing_span` Attribute + `routing_low_confidence` Span-Event |
| `tests/decision/test_routing_s42_preferences.py` | Neue Tests |
