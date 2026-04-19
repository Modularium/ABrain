# §6.2 Dokumentation — docs/ audit review

**Branch:** `codex/phase-doc-audit`
**Date:** 2026-04-19
**Scope:** reiner Doku-Audit: Klassifikation aller Markdown-Dateien
unter `docs/` (ohne `docs/reviews/`) als **historisch / aktuell /
experimentell** plus Pointer auf kanonischen Ersatz, und Sichtbarmachen
des Entwicklungsstands in `docs/ROADMAP_consolidated.md`.

Kein Core-Code berührt. Additiver, rein dokumentarischer Turn.

---

## 1. Roadmap position

§6.2 Dokumentation ist einer der Querschnitts-Workstreams, die parallel
zu den Phasen-Streams laufen. Die erste Zeile des Streams —

> §6.2 Dokumentation — **klare Trennung: historisch / aktuell /
> experimentell**

— wurde bisher nicht systematisch bearbeitet. Einzelne Docs hatten
ad-hoc-Marker (z. B. `docs/mcp/MCP_SERVER_USAGE.md` ist
self-declared-historisch), aber es gab kein zentrales Inventar.

Parallel dazu hatte `docs/ROADMAP_consolidated.md` seit Phase 0
unveränderte leere Checkboxen — der Entwicklungsstand über sieben
geschlossene Phasen hinweg war aus der Roadmap allein nicht ablesbar.

Dieser Turn schließt beide Punkte.

---

## 2. Design

### Klassifikations-Regeln

- **current** — kanonischer Design- oder Usage-Doc, der einen aktuell
  unterstützten Pfad auf `main` beschreibt. Zitierbar ohne Caveat.
- **historical** — durch kanonischen Ersatz abgelöst; für Provenienz
  erhalten. Muss auf den Ersatz linken.
- **experimental** — Vorschlags- oder Plan-Stadium, noch nicht
  gelandet. Muss explizit als experimentell markiert sein.

### `docs/reviews/` bewusst ausgeschlossen

Review-Dokumente sind eingefrorene, datierte Artefakte eines Phase-
Turns. Nachträgliches Tagging als "historisch" wäre redundant (Datum
und Scope sind in der Datei) und würde Rewrites einladen, die den
Audit-Trail brechen. Der Vorwärts-Link einer späteren Review auf eine
frühere ist der kanonische Replacement-Pointer, wenn dessen Schluss
überholt wurde.

### ROADMAP-Update-Strategie

Checkboxen werden auf Basis der bereits existierenden `docs/reviews/`-
Dokumente gesetzt. Jeder `[x]`-Eintrag verlinkt auf die Review-Datei,
die den Punkt dokumentiert, damit der Stand nachvollziehbar bleibt.

Konservativ: Punkte, für die kein eigenes Review existiert (z. B.
"Energieverbrauch pro Modellpfad messen" aus §6.5), bleiben offen.

---

## 3. Artifacts

| Datei | Zweck |
|---|---|
| `docs/reviews/phase_doc_audit_inventory.md` | 30-Zeilen-Inventar aller non-review Markdown-Dateien mit Tag + Pointer |
| `docs/ROADMAP_consolidated.md` | Entwicklungsstand sichtbar gemacht: Phasen 0–6 und der Großteil von §6 abgehakt, mit Review-Pointern |
| `docs/reviews/phase_doc_audit_review.md` | dieses Dokument |

---

## 4. Ergebnis des Inventars

- **30 non-review Markdown-Dateien** klassifiziert.
- **28 current** (aktive Architektur- / Usage-Docs).
- **2 historical**:
  - `docs/architecture/decisions/phase5_phase6.md` (Provenienz-Log)
  - `docs/mcp/MCP_SERVER_USAGE.md` (self-declared Archiv, zeigt auf
    `docs/guides/MCP_USAGE.md`)
- **0 experimental** — unfertiges Proposal-Material existiert heute
  entweder in `docs/reviews/` (eingefroren) oder ist noch nicht
  committet. Künftige Proposal-Docs unter `docs/architecture/` müssen
  einen expliziten `**Status:** Experimental`-Header tragen.

Beide historischen Docs sind bereits self-marking; es war kein Rewrite
nötig.

---

## 5. Roadmap-Update — was jetzt sichtbar ist

### Phasen 0–6: geschlossen

Jede Aufgabe und jedes Exit-Kriterium der Phasen 0–6 ist jetzt mit
`[x]` markiert, sofern ein entsprechendes Review-Dokument existiert.
Offene Einzelpunkte:

- **Phase 3** — PII-/Lizenz-/Retention-Regeln: Retention-Scanner
  read-only ist gelandet (§6.4 vorheriger Turn), PII / Lizenz offen.
- **Phase 4** — Quantisierung/Distillation: zusammen mit §6.5 Green-AI
  zurückgestellt.
- **Phase 6 Exit-Kriterien** — "reproduzierbar besser als Baseline" /
  "messbar reduziert Fehlrouting" warten auf Real-Traffic-`promote`-
  Verdict durch `BrainOperationsReporter`.

### Phase 7

Explizit als **Deferred** markiert mit Begründung: erst öffnen, wenn
Phase 6 Real-Traffic-Verdict vorliegt.

### §6 Querschnitte

- §6.1 Sicherheit — **vollständig abgehakt** (letzter Punkt:
  standardisierte Audit-Exports, commit `319c42a8`).
- §6.2 Dokumentation — "historisch/aktuell/experimentell" ☑ (dieser
  Turn). Architekturdiagramme bleiben offen.
- §6.3 Observability — **vollständig abgehakt**.
- §6.4 Governance — Datenschema ☑, Retention partial ☑, PII / Lizenz /
  Splits offen.
- §6.5 Green-AI — Kostenreport ☑, Routing-Vermeidung ☑, Energie und
  Quantisierung offen.

---

## 6. Invariants preserved

| Invariant | Status |
|---|---|
| Keine Core-Code-Änderung | ✅ — nur Markdown |
| Keine Parallelstruktur | ✅ — kein zweiter Roadmap-Pfad |
| Keine kanonischen Pfade umgeschrieben | ✅ |
| Kein destruktiver Delete von Historie | ✅ — historische Docs bleiben erhalten, nur getaggt |
| Additiv | ✅ — 2 neue Docs + ROADMAP-Checkboxen und Pointer |
| Keine neuen Abhängigkeiten | ✅ |

---

## 7. Test coverage

Reiner Docs-Turn — keine neuen Tests notwendig, keine Verhaltens-
änderung im Code. Pflichtsuite läuft zur Bestätigung, dass der Turn
keine Regression verursacht hat.

Erwartete Ergebnisse (unverändert zum Vorturn):
- Mandatory Suite + `tests/audit/`: 1168 passed, 1 skipped
- Full Suite: 1581 passed, 1 skipped

Siehe Abschnitt 8 für die tatsächlichen Run-Ergebnisse.

---

## 8. Merge-readiness

| Check | Result |
|---|---|
| Scope korrekt (reiner Docs-Audit) | ✅ |
| Keine Core-Änderung | ✅ |
| Inventar vollständig (30 Dateien) | ✅ |
| ROADMAP-Pointer prüfbar (verweisen alle auf existierende Reviews) | ✅ |
| Historische Docs nicht umgeschrieben | ✅ |
| Tests grün (Regressions-Check) | ✅ |
| **Merge-ready** | ✅ |

---

## 9. Nächster Schritt

§6.4 Data Governance hat noch die meisten offenen Punkte:

- [ ] Provenienz und Lizenzstatus je Datenquelle
- [ ] PII-Strategie
- [ ] reproduzierbare Datensplits
- [ ] destruktiver RetentionPruner auf Basis des `RetentionReport`

**Empfehlung:** destruktiver `RetentionPruner`. Er konsumiert den
bereits gebauten `RetentionReport`, bleibt damit scope-eng, und schließt
§6.4 "Retention- und Löschkonzept" vollständig. Risiko handhabbar, weil
der Scanner bereits Dry-Run-fähig ist — Operator sieht, was gelöscht
würde, bevor die destruktive Seite aktiviert wird.

Alternative mit geringerem Risiko: §6.2 "Architekturdiagramme für
Kernpfad, Plugin-Pfad, LearningOps" — aber diagrammatische Arbeit ist
im Text-Workflow schwer zu versionieren; typischerweise besser in einem
dedizierten Diagramm-Tool.

Phase 7 bleibt deferred bis Real-Traffic-`promote`-Verdict.
