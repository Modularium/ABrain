# S8 / S9 / S10 Blocker Fix Review

## Ausgangslage

Im kombinierten Review der Phasen S8, S9 und S10 wurden vier reale Blocker
identifiziert:

1. `S8` berechnete `quality` im Agent-Katalog aus einer ad-hoc Shadow-History
   statt aus der kanonischen `PerformanceHistoryStore`-Quelle.
2. `S10` hielt Routing-/Explainability-Daten doppelt:
   als first-class Felder auf `ExplainabilityRecord` und zusätzlich redundant
   unter `metadata.routing_decision`.
3. `S9` stellte `execution_capabilities` in API und CLI bereit, aber nicht
   sichtbar im Frontend dar.
4. `tests/core/test_api_gateway_openapi.py` hing reproduzierbar im
   `TestClient`-Pfad und blockierte die geforderte Suite.

## Minimale Korrekturen

### 1. S8: kanonische History-Anbindung

`services/core.py:list_agent_catalog()` nutzt jetzt für `quality` die
kanonische Kombination aus:

- `AgentRegistry().list_descriptors()`
- `_get_learning_state()["perf_history"]`
- `PerformanceHistoryStore.get_for_descriptor()` bzw. `get(agent_id)`

Die frühere synthetische `AgentPerformanceHistory(...)`-Projektion aus rohen
Katalogfeldern wurde vollständig entfernt.

Wichtig:

- Es wurde **kein** zweites History-Modell eingeführt.
- `compute_agent_quality()` blieb unverändert als einzelne, deterministische
  Funktion bestehen.
- Wenn keine History vorliegt, liefert der bestehende Store ehrlich den leeren
  Default-Zustand, wodurch weiterhin neutrale/`insufficient_data`-Ergebnisse
  entstehen.

### 2. S10: eine Explainability-Wahrheit

Neue Explainability-Datensätze speichern die S10-Signale nur noch einmal
kanonisch:

- `routing_confidence`
- `score_gap`
- `confidence_band`
- `policy_effect`
- `scored_candidates`

`services/core._store_trace_explainability()` schreibt diese Felder weiter
first-class, speichert aber **kein** volles `metadata.routing_decision` mehr.
In `metadata` bleiben nur nicht-redundante Kontextinformationen erhalten:

- `task_type`
- `required_capabilities`
- `rejected_agents`
- `candidate_filter`
- `created_agent`
- `winning_policy_rule`
- `routing_model_source`
- `selected_candidate_model_source`
- `selected_candidate_feature_summary`

`TraceStore._build_replay_descriptor()` liest jetzt nur noch aus der
kanonischen Repräsentation:

- first-class Explainability-Felder
- nicht-redundante Explainability-Metadaten
- Trace-Metadaten

Für Bestandsdaten gibt es eine **Read-Normalisierung** in `TraceStore`:
alte `metadata.routing_decision`-Payloads werden beim Lesen in die kanonischen
Felder und Metadaten überführt. Damit bleibt Rückwärtskompatibilität erhalten,
ohne für neue Daten eine zweite Wahrheit fortzuführen.

### 3. S9: Frontend-Gate geschlossen

`frontend/agent-ui/src/pages/AgentsPage.tsx` rendert jetzt die vorhandene
kanonische Capability-Surface kompakt:

- `execution_protocol`
- `requires_network`
- `requires_local_process`
- `supports_cost_reporting`
- `supports_token_reporting`
- `runtime_constraints`

Die Darstellung ist rein read-only. Es wurde keine neue React-Logik,
Interpretationslogik oder zweite Capability-Welt eingeführt.

### 4. OpenAPI-Test-Hänger

Die Ursache war nicht die ABrain-API selbst, sondern der in dieser Umgebung
hängende `fastapi.testclient.TestClient`-Pfad. Der Hänger war sogar mit
minimalen FastAPI/Starlette-Apps reproduzierbar.

Der Test wurde deshalb produktiv sinnvoll auf direkten ASGI-Zugriff via
`httpx.ASGITransport` + `httpx.AsyncClient` umgestellt. Dadurch wird weiterhin
die echte ASGI-App geprüft:

- `/docs`
- `/redoc`
- `/openapi.json`
- dokumentierte Control-Plane-Routen

Swagger/OpenAPI wurde nicht zurückgebaut oder versteckt.

## Warum kein Feature verloren ging

- `S8`: `quality` bleibt in API, CLI und Health-UI sichtbar, aber jetzt auf
  der richtigen Datenquelle.
- `S9`: `execution_capabilities` bleiben in API und CLI unverändert und sind
  zusätzlich im Frontend sichtbar.
- `S10`: `trace show`, `explain` und `trace drilldown` behalten ihre
  Informationen; redundante Doppelhaltung wurde entfernt, nicht die Funktion.
- Alte Trace-Daten bleiben lesbar, weil `TraceStore` sie beim Lesen in die
  kanonische Struktur normalisiert.

## Intakte Invarianten

- **Single Runtime**: keine neue Execution-, Routing-, Policy- oder Replay-Welt
- **Single Source of Truth**:
  - `ExecutionResult` unverändert
  - `PerformanceHistoryStore` bleibt einzige History-Wahrheit
  - `TraceStore` bleibt einzige Trace-Wahrheit
  - `ExplainabilityRecord` bleibt einzige Explainability-Wahrheit
- **No Parallel Logic**:
  - keine zweite Trust-Berechnung
  - keine zweite Capability-Logik
  - keine zweite Replay-/Forensics-Engine
- **Additive only**:
  - keine Breaking Changes
  - keine stillen Semantikänderungen bestehender Felder
- **Governance / Approval / Orchestration untouched**:
  - kein Bypass und keine Duplikation dieser Layer

## Validierung

Erfolgreich geprüft:

- `.venv/bin/python -m pytest -o python_files='test_*.py' tests/state tests/mcp tests/approval tests/orchestration tests/execution tests/decision tests/adapters tests/core tests/services tests/integration/test_node_export.py`
  - Ergebnis: `352 passed, 1 skipped`
- `.venv/bin/python -m py_compile` für alle geänderten Python-Dateien
- `frontend/agent-ui`
  - `npm ci`
  - `npm run type-check`
  - `npm run build`
  - `npm run lint`

## Fazit

Der kombinierte Stand ist nach diesen Korrekturen architekturkonform:

- `S8` hängt an der kanonischen History
- `S9` ist jetzt auch im Frontend sichtbar
- `S10` führt nur noch eine Explainability-Wahrheit
- der frühere OpenAPI-Test-Hänger ist sauber beseitigt

Damit ist der Stand merge-reif, sofern kein neuer externer Konflikt auf
`main` entstanden ist.
