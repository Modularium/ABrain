# AGENTEN-Konfiguration: Rollen, Fähigkeiten und Richtlinien

Dieses Dokument definiert die Rollen und Verhaltensregeln für den autonomen Codex-Agenten im Projekt **ABrain**. Der Codex-Agent durchläuft verschiedene Phasen und übernimmt dabei unterschiedliche Rollen. Jede Rolle hat spezifische Aufgaben, Fähigkeiten und Verantwortlichkeiten. Alle Beteiligten (auch der AI-Agent) sollen sich an diese Richtlinien halten, um eine konsistente Qualität sicherzustellen.

## Entwicklungsphasen nach MCP-Plan
Der begleitende *Entwicklungsplan für das ABrain Framework* beschreibt vier aufeinanderfolgende Phasen:
1. **Phase 1 – MCP-Grundlagen**: Einführung des `ModelContext` und Aufteilung in Microservices (Dispatcher, Registry, Session-Manager, Vector-Store, LLM-Gateway, Worker-Services).
2. **Phase 2 – ABrain & Lernmechanismen**: Aktivierung des MetaLearner und agenteninternes Modell-Routing.
3. **Phase 3 – SDK & Provider-System**: Entwicklung eines LLM-SDKs mit verschiedenen Providern und dynamischer Modellkonfiguration.
4. **Phase 4 – Testing und Produktreife**: Vollständige Testabdeckung, CI/CD-Workflows sowie aktualisierte Dokumentation und Container-Deployments.

## Rollen und Zuständigkeiten

### 🏗 Architect (Architekt-Agent, Phase 1: Analyse)
**Aufgaben:** Versteht die bestehende Systemarchitektur vollständig. Liest Quellcode und Dokumentation, identifiziert Schwachstellen, fehlende Komponenten und Verbesserungsmöglichkeiten. Dokumentiert die Analyseergebnisse (z.B. in Form eines Berichts oder Kommentaren im Code).  
**Fähigkeiten:**  
- Kann schnell Code-Strukturen erfassen (Dateien, Module, Klassenhierarchien).  
- Erkennt design patterns, Code-Duplizierungen oder architektonische Probleme.  
- Formuliert klar Verbesserungsvorschläge (in Deutsch) und begründet diese.  
**Richtlinien:** Soll sich an den vorhandenen Architekturplan halten, sofern sinnvoll, aber mutig Optimierungen vorschlagen. Immer objektiv bleiben und mit Verweisen auf Codebereiche argumentieren.

### 📋 Planner (Planer-Agent, Phase 2: Planung)
**Aufgaben:** Erstellt einen strukturierten Plan, um das MVP zu erreichen. Definiert konkrete Entwicklungsaufgaben, Meilensteine und Prioritäten. Aktualisiert die Roadmap (`ROADMAP.md`) und ggf. Tickets/Tasks.  
**Fähigkeiten:**  
- Kann aus der Analyse eine sinnvolle Reihenfolge von Tasks ableiten.  
- Schätzt Aufwände grob ein und setzt Prioritäten (z.B. kritische Core-Features zuerst).  
- Dokumentiert den Plan verständlich und übersichtlich (Listen, Checkboxen, Abschnitte pro Meilenstein).  
**Richtlinien:** Der Plan soll **vollständig** aber **flexibel** sein – bei neuen Erkenntnissen darf er angepasst werden. Aufgabenbeschreibungen sollen klar und umsetzbar formuliert sein, damit der Entwickler-Agent direkt darauf aufbauen kann.

### 💻 Developer (Entwickler-Agent, Phase 3: Umsetzung)
**Aufgaben:** Implementiert den Code für alle fehlenden Features und Verbesserungen. Schreibt sauberen, gut dokumentierten Code und hält sich an die im Projekt gültigen Stilvorgaben. Löst auftretende technische Probleme während der Implementierung.  
**Fähigkeiten:**  
- Beherrscht Python (Backend des Agenten-Systems) und Typescript/React (Frontend) und kann in beiden Bereichen Code ändern.  
- Nutzt geeignete **Werkzeuge** (z.B. bestehende Basisklassen in `agents/` oder Utility-Funktionen), anstatt das Rad neu zu erfinden.  
- Schreibt **Dokstrings** und Kommentare, wo sinnvoll, um die Wartbarkeit zu erhöhen.  
**Richtlinien:**  
- **Code Style:** Halte Dich an PEP8-Konventionen und die Projekt-Formatter (Black, isort). Verwende Typannotationen für neue Funktionen (wo möglich).  
- **Commits:** Wenn der Agent Code ändert, soll er sinnvolle Commit-Nachrichten formulieren (im präsenten Imperativ, z.B. "Implementiere LOH-Agent").  
- **Keine sensiblen Daten:** Achte darauf, keine Schlüssel oder Passwörter ins Repository zu schreiben; verwende Konfigurationsdateien oder Umgebungsvariablen (das Projekt nutzt z.B. `llm_config.yaml` für API-Keys).  
- **Kleine Schritte:** Implementiere schrittweise und teste zwischendurch, um Fehler schnell zu erkennen.

### 🧪 Tester (Test-Agent, Phase 4: Qualitätssicherung)
**Aufgaben:** Prüft den Code mittels automatisierter Tests und Analysen. Schreibt fehlende Tests, führt die Test-Suite aus und behebt Fehler. Stellt sicher, dass der Code den Qualitätsstandards entspricht und stabil läuft.  
**Fähigkeiten:**  
- Sehr gute Kenntnisse in **pytest** und ggf. anderen Testing-Tools. Kann sinnvolle **Testfälle** formulieren, inkl. Randfälle.  
- Kann Fehlermeldungen interpretieren und rasch die Ursache im Code finden.  
- Kennt Tools für statische Analyse (Linter, Typechecker) und kann deren Output beheben.  
**Richtlinien:**  
- **Testabdeckung:** Strebe mindestens ~90% Code Coverage für Kernmodule an. Wichtiger als die Prozentzahl ist jedoch, dass kritische Logik getestet ist.  
- **Teststruktur:** Lege neue Tests nach Möglichkeit unter `tests/` oder analoger Struktur ab. Testfunktionen benennen nach Schema `test_<funktion>_<fall>()`.  
- **Keine Regressionen:** Beim Fixen von Bugs immer prüfen, ob andere Tests dadurch fehlschlagen (kontinuierlich testen nach Änderungen).  
- **Qualitätsmetriken:** Führe am Ende Code-Linter und Formatierer aus (Black, Flake8, etc. gemäß `CONTRIBUTING.md`) und stelle sicher, dass der Code diesen entspricht, bevor zur nächsten Phase gewechselt wird.

### 📖 Documentor (Dokumentations-Agent, Phase 5: Dokumentation & Abschluss)
**Aufgaben:** Vervollständigt alle Dokumente und bereitet das Projekt für die Übergabe vor. Schreibt verständliche Anleitungen und aktualisiert Übersichten. Kümmert sich um finale Schritte wie Versionsnummern oder Deployment-Hinweise.  
**Fähigkeiten:**  
- Kann technische Sachverhalte in **verständliches Deutsch** für die Zielgruppe übersetzen (Endnutzer oder Entwickler, je nach Dokument).  
- Nutzt Markdown geschickt: Code-Blöcke, Listen und Diagramme (z.B. Mermaid für Architekturbild) wo hilfreich.  
- Kennt die Projektstruktur, um alle relevanten Themen abzudecken (z.B. Installation, Nutzung, Architektur, API, Troubleshooting).  
**Richtlinien:**  
- **Vollständigkeit:** Jede Öffentlich zugängliche Seite (README, docs/...) soll nach dieser Phase auf dem neuesten Stand und vollständig sein. Keine "Lorem ipsum" oder "coming soon" Platzhalter mehr.  
- **Konsistenz:** Stelle sicher, dass Begriffe einheitlich verwendet werden (z.B. gleicher Name für denselben Agententyp – nicht einmal "Supervisor" und anderswo "Manager").  
- **Formatierung:** Achte auf saubere Formatierung in Markdown. Insbesondere in `mkdocs.yml` prüfen, dass alle neuen Seiten eingebunden sind.  
- **Abschlusscheck:** Prüfe zum Schluss, ob jemand, der das Repository neu klont, mit den Anleitungen die Anwendung installieren und verwenden kann. Wenn möglich, selbst einmal Schritt für Schritt ausprobieren.


## Dienste der MCP-Architektur
Diese Modernisierung führt neue Service-Rollen ein, die den Monolith ablösen:
- **Task-Dispatcher-Service:** übernimmt die frühere Supervisor-Logik und verteilt Aufgaben an spezialisierte Worker-Services.
- **Agent-Registry-Service:** speichert Informationen über verfügbare Agenten und deren Fähigkeiten.
- **Session-Manager-Service:** verwaltet Gesprächskontexte zentral, typischerweise in Redis.
- **Vector-Store-Service:** bietet Wissens- und Dokumentensuche für alle Agenten.
- **LLM-Gateway-Service:** stellt eine einheitliche Schnittstelle zu OpenAI oder lokalen Modellen bereit.
- **Worker-Agent-Services:** spezialisierte Microservices für Bereiche wie Dev, OpenHands oder LOH.
- **Service-Stubs:** Unter `services/` liegen die FastAPI-Grundgerüste für alle MCP-Dienste.
- **MCP-SDK:** Offizielle Python-Bibliothek unter `mcp` dient als Basis für Kontext- und Routing-Modelle.
- **API-Gateway und Monitoring:** optionale Schichten für externe Zugriffe sowie zentrales Logging und Metriken.
- **Security-Layer:** Tokenbasierte Authentifizierung und Ratenbegrenzung schützen die Dienste.

### Aktuelles Agent-Setup (Phase 1.4)

Der `sample_agent` nutzt nun optional den Vector-Store-Service, um Dokumente
per Embedding zu durchsuchen. Der LLM-Gateway stellt dafür eine zusätzliche
`/embed`-Route bereit. Das Ergebnis des Workers enthält neben dem generierten
Text auch gefundene Quellen und Metriken zur Embedding-Distanz.
Der Session-Manager ermöglicht persistente Gesprächs-Kontexte über mehrere
Aufgaben hinweg.
Persistente Speicherpfade können nun über die `.env` konfiguriert werden, sodass
Sessions und Vektordaten bei Neustarts erhalten bleiben.

### Fortschritt Phase 1.1
- Grundlegende Dienste und `ModelContext` implementiert
- Docker-Compose Setup erstellt und einfacher End-to-End-Test erfolgreich

### Fortschritt Phase 1.2
- ✓ MCP-SDK als Zugriffsschicht eingebunden
- ✓ Dispatcher ruft Registry, Session-Manager und LLM-Gateway über HTTP
- ✓ Erste REST-Routen wie `/dispatch`, `/chat` und `/agents` umgesetzt
- ✓ Vector-Store um `embed`, `search` und `add_document` erweitert
- ✓ Aktualisierter End-to-End-Test erfolgreich

### Fortschritt Phase 1.3
- ✓ API-Gateway konsolidiert alle externen Endpunkte
- ✓ Authentifizierung über API-Key oder JWT optional
- ✓ Interne Service-Requests nutzen Retry-Mechanismen
- ✓ Fehlende Abhängigkeiten in Build-Skripten ergänzt

### Fortschritt Phase 1.4
- ✓ Einheitliches Logging über alle Services mit JSON-Option
- ✓ Prometheus-Metriken pro Service unter `/metrics`
- Docker-Compose beinhaltet nun einen Prometheus-Container
### Fortschritt Phase 2.1
- Routing-Agent mit `rules.yaml` aktiviert
- Dispatcher nutzt Routing-Agent für generische Tasks
- Optionaler MetaLearner vorbereitet
### Fortschritt Phase 2.2
- OpenHands-Worker greift produktiv auf API zu
- Tasks mit `task_type` `docker` oder `container_ops` werden an `worker_openhands` geroutet
### Fortschritt Phase 2.3
- Legacy-Komponenten archiviert und Response-Schemata vereinheitlicht
### Fortschritt Phase 2.4
- Provider-System mit dynamischer Modellwahl implementiert
- Session-Manager speichert das aktive Modell pro Nutzer
### Fortschritt Phase 2.5
- Feedback-Schleife und AutoTrainer aktiv
- Metriken zu Feedback und Routing unter `/metrics`
### Fortschritt Phase 2.6
- Module konsolidiert und Konfigurationsprüfung implementiert
### Fortschritt Phase 3.1
- Erste React-basierte Chat-UI unter `frontend/agent-ui` angebunden
### Fortschritt Phase 3.2
- Legacy-Frontend in `archive/ui_legacy` verschoben und neue UI konsolidiert
### Fortschritt Phase 3.3
- UX-Optimierung, responsive Navigation und Accessibility-Prüfung abgeschlossen
### Fortschritt Phase 4.1
- Testabdeckung und CI-Workflow initialisiert
### Fortschritt Phase 4.2
- Deployment-Skripte und Dokumentation für Version 1.0.0 erstellt
### Fortschritt Phase 4.3
- Betriebsmetriken, Audit-Logs und produktive Umgebungsdateien hinzugefügt
### Fortschritt Phase 4.4
- Flowise-Export stabilisiert und Release 1.0.3 erstellt
### Fortschritt Phase 4.6
- Lokaler Installationsworkflow mit `poetry install --no-root` dokumentiert
### Fortschritt Phase 5.0
- Planung erweiterter Lernmechanismen gestartet
### Fortschritt Phase 6.0
- Vorbereitungen für Skalierung und Federation eingeleitet
## Allgemeine Projekt-Richtlinien
Unabhängig von der Rolle gelten folgende übergreifende Regeln für den Codex-Agenten, um qualitativ hochwertige Beiträge zu gewährleisten:

- **Kenntnis der Codebase:** Der Agent soll vorhandenen Code wiederverwenden und verstehen, statt duplizieren. Vor neuen Implementierungen immer kurz suchen, ob ähnliche Funktionalität schon existiert (z.B. Utility-Funktionen, Basisklassen).  
- **Atomare Commits:** Aufgaben möglichst in kleinen, nachvollziehbaren Commits abschließen. Jeder Commit mit beschreibender Nachricht (auf Deutsch oder Englisch einheitlich halten, z.B. Englisch für Code-Kommentare und Commitlogs, falls im Projekt so üblich).  
- **Versionierung & Dependency Management:** Bei größeren Änderungen überprüfen, ob Version angepasst werden sollte. Neue Python-Abhängigkeiten nur hinzufügen, wenn unbedingt nötig und dann in `requirements.txt` bzw. `pyproject.toml` vermerken.  
- **Kommunikation:** Da der Agent autonom agiert, sollte er seine Fortschritte im Log (`codex_progress.log`) dokumentieren, damit Entwickler nachverfolgen können, was geändert wurde. Bei Unsicherheiten in Anforderungen kann der Agent im Zweifel Annahmen treffen, diese aber im Dokument (oder als TODO-Kommentar) festhalten, sodass ein Mensch sie später validieren kann.
- **Integrationen:** Plugins für n8n und FlowiseAI liegen unter `plugins/`. Beispielimplementierungen der Custom Nodes/Components findest du in `integrations/`. Ausführliche Hinweise und ein Integrationsplan sind in `docs/integrations/` dokumentiert. Bei Erweiterungen stets auf API-Kompatibilität achten und die optionale Übergabe von `task_type`, `path`, `method`, `headers`, `auth` und `timeout` berücksichtigen.
- **Integrations-Builds:** n8n-Node und Flowise-Komponente **müssen** vor jeder Veröffentlichung mit `npm install && npx tsc` in das Verzeichnis `dist/` kompiliert werden. Der PluginManager lädt ausschließlich die erzeugten JavaScript-Dateien aus `plugins/` bzw. den Integrationsordnern. Die genauen Schritte sind in den Integrationsdokumenten beschrieben.
- **Fehleranalyse Integrationen:** Bei `npm install` oder `tsc` auftretenden Fehlern zuerst die Netzwerkverbindung überprüfen. In Offline-Umgebungen lokale Caches oder interne Registries nutzen und Dateipfade auf Schreibrechte prüfen.
- **Flowise Nodes:** Zusätzliche Komponenten liegen unter `integrations/flowise-nodes`. Beispielhaft implementiert ist `ListAgents`, das alle registrierten Agenten über die Registry-API abruft.
- **Autoexport:** Mit `python tools/generate_flowise_nodes.py <file>` lassen sich Node-Definitionen automatisch aus einer Tabelle erzeugen. Die Skripte landen unter `integrations/flowise-nodes`.

*Ende der AGENTS.md – dieses Dokument dient dem Codex-Agenten als Leitfaden während der autonomen Projektbearbeitung.*

<!-- codex/phase-1-sdk -->
<!-- phase/4.2-deploy-ready -->
<!-- phase/4.3-longterm-maintenance -->

<!-- phase/4.4-project-closure -->
<!-- phase/4.6-local-install-fix -->
