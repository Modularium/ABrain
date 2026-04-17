# Phase R1 — Retrieval Layer Inventory

**Date:** 2026-04-17
**Phase:** Phase 3 — Retrieval- und Wissensschicht, Step R1

---

## 1. Bestand: Legacy-RAG-Infrastruktur

Das Verzeichnis `rag/` enthält vier Python-Dateien, die aus der Pre-Canonical-Ära
stammen:

| Datei | Beschreibung | Status |
|---|---|---|
| `rag/url_rag_system.py` | Web-basiertes RAG mit LangChain, OpenAI Embeddings, WebScraperAgent | Legacy — Imports fehlen |
| `rag/content_cache.py` | Cache für gescrapten Web-Content | Legacy — Imports fehlen |
| `rag/parallel_processor.py` | Async-Batch-Processing für Embeddings | Legacy — Imports fehlen |
| `rag/js_renderer.py` | JavaScript-Rendering für Web-Scraping | Legacy — Imports fehlen |

**Befund:**
- `rag/url_rag_system.py` importiert `agents.web_scraper_agent`, `agents.web_crawler_agent`,
  `datastores.vector_store`, `utils.logging_util`, `config.llm_config` — keines dieser Module
  existiert im aktuellen kanonischen Core.
- Die gesamte `rag/`-Codebasis hängt von `langchain`, `pandas`, `OpenAIEmbeddings` ab,
  die nicht in den kanonischen Abhängigkeiten verankert sind.
- **Keine einzige Datei in `services/core.py`, `api_gateway/`, `core/` oder `interfaces/`
  importiert aus `rag/`.**
- Die Legacy-RAG-Dateien werden **nicht** aktiviert oder reaktiviert.
  Sie werden dokumentiert und als nicht-kanonisch markiert.

---

## 2. Bestand: Core-Infrastruktur für Phase 3

Folgende kanonische Module sind bereits vorhanden und als Grundlage nutzbar:

| Modul | Relevanz für Phase 3 |
|---|---|
| `core/execution/adapters/manifest.py` | Pattern für typisierte Governance-Modelle |
| `core/governance/policy_models.py` | Pattern für Pydantic-Modelle mit `extra="forbid"` |
| `core/governance/enforcement.py` | Pattern für Governance-Violation-Klassen |
| `core/state/trace_store.py` | Ziel für Retrieval-Audit-Events (später) |
| `services/core.py` | Einziger Service-Verdrahtungspunkt (Retrieval-Layer später einzuhängen) |

---

## 3. Scope von R1

R1 definiert und implementiert ausschließlich:

1. **Wissensquellen-Klassifikation** — formale `SourceTrust`-Taxonomie
2. **Retrieval-Scope-Beschränkung** — Retrieval nur für Explanation/Planning/Assistance,
   explizit NICHT für kritische Actions
3. **Kanonische Datenmodelle** — `KnowledgeSource`, `RetrievalQuery`, `RetrievalResult`
   als einzige Wahrheit für den Retrieval-Namespace
4. **Governance-Boundary** — `RetrievalBoundary` mit Query-Validierung und
   Trust-Level-Enforcement

R1 implementiert NICHT:
- Backend-Implementierungen (Vector Store, Embeddings)
- Ingestion-Pipeline
- Integration in den Orchestrator
- Prompt-Injection-Sanitization (R3)
- Benchmarks (R5)

---

## 4. Neue kanonische Pfade

```
core/retrieval/
  __init__.py          — öffentliche API des Retrieval-Namespaces
  models.py            — SourceTrust, RetrievalScope, KnowledgeSource, RetrievalQuery, RetrievalResult
  boundaries.py        — RetrievalBoundary, RetrievalPolicyViolation

tests/retrieval/
  __init__.py
  test_retrieval_models.py
  test_retrieval_boundaries.py
```

---

## 5. Governance-Regeln (R1)

### SourceTrust-Hierarchie

```
TRUSTED    — eigene, verifizierte Inhalte (Systemdokumentation, Code-Basis)
INTERNAL   — interne, weniger streng kontrollierte Quellen (Wikis, Tickets)
EXTERNAL   — Drittquellen mit kontrolliertem Zugang (lizenzierte Datensätze, bekannte APIs)
UNTRUSTED  — öffentliches Web, User-Inputs, unverifizierte Quellen
```

### Scope-Hierarchie (Restriktivität aufsteigend)

```
EXPLANATION — Erklärung von Entscheidungen (alle Quellen erlaubt, mit Herkunftsvermerk)
ASSISTANCE  — allgemeine Kontexthilfe (alle Quellen erlaubt, mit Herkunftsvermerk)
PLANNING    — Planung und Sequenzierung (nur TRUSTED/INTERNAL; EXTERNAL mit Warnung; UNTRUSTED verboten)
```

**Nie erlaubt:** Retrieval-Ergebnisse als direkte Grundlage für kritische Aktionen
(kein scope `critical_action` — fehlt absichtlich).

### Trust-Scope-Matrix

| Scope | TRUSTED | INTERNAL | EXTERNAL | UNTRUSTED |
|---|---|---|---|---|
| EXPLANATION | ✅ | ✅ | ✅ (mit Vermerk) | ✅ (mit Warnung) |
| ASSISTANCE | ✅ | ✅ | ✅ (mit Vermerk) | ✅ (mit Warnung) |
| PLANNING | ✅ | ✅ | ⚠️ Warnung | ❌ Verboten |
| (critical_action) | ❌ nicht definiert | ❌ | ❌ | ❌ |
