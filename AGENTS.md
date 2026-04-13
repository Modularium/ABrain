
# AGENTS.md — ABrain Canonical Codex Working Rules

Dieses Dokument definiert die Arbeitsregeln für autonome oder halbautonome Codex-Agenten im Repository **ABrain**.

Es ersetzt ältere agenten- oder MCP-zentrierte Rollendefinitionen, die nicht mehr dem heutigen kanonischen ABrain-Kern entsprechen.

---

## 1. Projektidentität

ABrain ist ein **policy-gesteuertes Orchestrierungs- und Entscheidungssystem** mit einem klaren, auditierbaren Kernpfad:

`Decision -> Governance -> Approval -> Execution -> Audit -> Orchestration`

Leitprinzip:

**Control > Autonomy**

ABrain ist ausdrücklich:

- kein unkontrollierter Multi-Agent-Schwarm
- kein Plugin-Spielplatz ohne Capability-Grenzen
- kein „alles durch LLM“-System
- kein Hype-Framework mit parallelen Wahrheiten

---

## 2. Kanonische Source of Truth

Codex muss sich immer an diesen kanonischen Wahrheiten orientieren:

### Kern
- `core/decision/`
- `core/governance/`
- `core/approval/`
- `core/execution/`
- `core/audit/`
- `core/orchestration/`

### Zentrale Verdrahtung
- `services/core.py`

### Externe Oberflächen
- `api_gateway/main.py` — einzige externe HTTP-Surface
- `interfaces/mcp/` — einzige MCP-Surface
- `scripts/abrain` — einzige CLI
- `frontend/agent-ui/` — einzige UI

### Persistenz / Wahrheit
- `TraceStore` — einzige Trace-/Audit-Wahrheit
- `PerformanceHistoryStore` — einzige Performance-/History-Wahrheit
- Approval-/Plan-State nur über die kanonischen Stores

Wenn ältere Dokumente, Review-Dateien oder historische Branches etwas anderes zeigen:
- aktuelles main ist maßgeblich
- historische Artefakte sind nur Referenz, nicht Wahrheit

---

## 3. Oberste Invarianten

Diese Regeln gelten immer:

1. **Keine Parallel-Implementierung**
2. **Keine zweite Runtime**
3. **Keine zweite Wahrheit**
4. **Keine Business-Logik in UI, CLI oder OpenAPI-Schemas**
5. **Keine Legacy-Reaktivierung**
6. **Nur additive, nachvollziehbare Änderungen**
7. **Governance vor Autonomie**
8. **Persistenz vor Lernen**
9. **Evaluation vor Promotion**
10. **Jede neue Schicht muss auditierbar bleiben**

Wenn ein geplanter Schritt eine dieser Invarianten verletzen würde:
- nicht bauen
- minimalere, architekturkonforme Variante wählen
- sauber dokumentieren

---

## 4. Arbeitsmodus

Codex arbeitet **phasenweise**, **idempotent** und **reviewbar**.

Vor jeder Umsetzung:

1. aktuellen `main` prüfen
2. prüfen, ob der Schritt bereits ganz oder teilweise existiert
3. prüfen, ob parallele Branches denselben Scope schon implementieren
4. nur die fehlenden Teile ergänzen
5. keine Funktion neu bauen, die bereits kanonisch existiert

### Idempotenz-Regel

Wenn etwas bereits auf `main` vorhanden ist:
- nicht noch einmal implementieren
- nur bestätigen
- nächsten offenen Schritt wählen

Wenn etwas teilweise vorhanden ist:
- nur minimal ergänzen
- keine zweite Variante bauen

---

## 5. Roadmap-Priorität

Codex arbeitet entlang von `ROADMAP_consolidated.md`.

Reihenfolge:

1. Phase 0 – Konsolidierung
2. Phase 1 – Evaluierbarkeit
3. Phase 2 – kontrollierte Erweiterbarkeit
4. Phase 3 – Retrieval/Wissen
5. Phase 4 – System-Level MoE
6. Phase 5 – LearningOps
7. Phase 6 – Brain v1
8. Phase 7 – fortgeschrittenes Brain

Keine spätere Phase vorziehen, wenn frühere Voraussetzungen nicht sauber erfüllt sind.

---

## 6. Was Codex niemals tun soll

Codex darf **nicht**:

- alte `agentnn`-/Legacy-Namen oder Pfade reaktivieren
- zweite CLI-/API-/UI-Wege einführen
- neue Schatten-Policies oder Schatten-Router bauen
- Business-Logik in Frontend oder CLI verstecken
- ein neues Persistenzsystem ohne Not einführen
- historische „war früher schon da“-Ansätze blind zurückholen
- schwere Dependencies nur aus Bequemlichkeit hinzufügen
- unbegründet neue Microservices einführen
- große Architektur-Rewrites ohne klaren Mehrwert starten

---

## 7. Erwartetes Vorgehen pro Phase

Für jeden Schritt:

1. Scope bestimmen
2. kanonische betroffene Dateien identifizieren
3. optional Inventar-/Analyse-Dokument schreiben
4. minimal implementieren
5. gezielte Tests ergänzen
6. Review-Dokument schreiben
7. Merge-Gate durchführen
8. nur bei grünem Gate per Fast-Forward mergen

### Branch-Namensschema
`codex/<phase>-<kurzer-scope>`

### Review-Doku
`docs/reviews/<phase>_review.md`

### Inventar-Doku
`docs/reviews/<phase>_inventory.md`  
nur wenn Analyse nötig ist

---

## 8. Testpflicht

Mindestens folgende Suite ist Standard, sofern relevant:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
tests/state tests/mcp tests/approval tests/orchestration \
tests/execution tests/decision tests/adapters tests/core \
tests/services tests/integration/test_node_export.py
````

Zusätzlich:

* `py_compile` auf geänderten Python-Dateien

Wenn Frontend betroffen:

```bash
cd frontend/agent-ui
npm ci
npm run type-check
npm run build
npm run lint
```

Wenn API betroffen:

* relevante `/docs`, `/redoc`, `/openapi.json`-Checks
* Import-/Smoketest von `api_gateway.main`

Wenn CLI betroffen:

* `bash scripts/abrain --version`
* passende CLI-Smokes
* ggf. `./scripts/abrain setup`

---

## 9. Merge-Regeln

Merge nur wenn:

* Scope sauber
* Architektur-Invarianten eingehalten
* keine Parallelstruktur
* Tests grün
* Doku konsistent
* Branch review-reif

Nur:

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only <branch>
git push origin main
```

Keine Merge-Commits.
Keine halbgrünen Merges.
Keine „Fix folgt später“-Merges.

---

## 10. Dokumentationsregeln

Dokumentation muss:

* aktuelle Realität beschreiben
* historische und aktive Pfade sauber trennen
* keine Placebo-/Coming-soon-Behauptungen enthalten
* Architekturgrenzen korrekt benennen
* denselben Begriff immer konsistent verwenden

Wenn Doku falsche Behauptungen enthält:

* korrigieren oder explizit als historisch markieren

---

## 11. Erwartete Abschlussausgabe pro Codex-Durchlauf

Am Ende jedes Durchlaufs soll Codex knapp und strukturiert berichten:

1. Welcher Roadmap-Schritt wurde bearbeitet?
2. Warum genau dieser Schritt jetzt?
3. Welche Dateien wurden geändert?
4. Welche Invarianten wurden bewahrt?
5. Welche Tests liefen grün?
6. Review-reif?
7. Gemerged?
8. Wenn ja: main commit hash
9. Wenn nein: exakte Blocker
10. Was ist der nächste logische Schritt?

---

## 12. Praktische Kurzformel

ABrain wird nicht durch maximale Geschwindigkeit gut, sondern durch:

* eine kanonische Architektur
* deterministische Sicherheitsgrenzen
* echte Evaluierbarkeit
* kontrollierte Erweiterbarkeit
* saubere Persistenz
* und erst danach lernende, intelligentere Entscheidungslogik

Codex soll deshalb immer zuerst fragen:

**„Ist das der nächste kanonische, belastbare Schritt — oder nur die nächste Idee?“**

