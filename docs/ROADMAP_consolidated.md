# ABrain Roadmap (konsolidiert)

> Status: Konsolidierte Roadmap für den aktuellen ABrain-Kurs.  
> Sie ersetzt keine laufenden Architektur- und Review-Dokumente, sondern bündelt den belastbaren Entwicklungspfad aus den historischen Roadmaps, den Review-Ergebnissen und der neu definierten Produktstrategie.  
> Leitbild: **Control > Autonomy**. ABrain entwickelt sich zuerst als gehärtetes, policy-gesteuertes System und danach schrittweise zu einem hybriden Entscheidungsnetzwerk („Brain“), nicht zu einem generischen Hype-LLM.

---

## 1. Zweck dieser Datei

Diese Roadmap konsolidiert:

- die historische Aufgabenliste aus `ROADMAP.md`
- die älteren Planungsnotizen aus `Roadmap.md`
- die kurze Erweiterungsskizze aus `ROADMAP_NEXT.md`
- die abgeleiteten Erkenntnisse aus den Reviews und der aktuellen strategischen Analyse

Sie priorisiert nur die Teile weiter, die für den **aktuellen gehärteten ABrain-Zweig** technisch sinnvoll sind. Historische Punkte, die dem heutigen Architekturkurs widersprechen oder zu früh/skizzenhaft waren, werden hier nicht 1:1 übernommen.

---

## 2. Nordstern und Produktdefinition

### 2.1 Kurzdefinition

ABrain ist ein **policy-gesteuertes Orchestrierungs- und Entscheidungssystem** mit nachvollziehbarer Ausführungskette:

`Decision -> Governance -> Approval -> Execution -> Audit`

### 2.2 Strategischer Zielpfad

ABrain entwickelt sich in drei Stufen:

1. **Gehärtetes System**  
   Deterministische Governance, reproduzierbare Abläufe, belastbare Persistenz, konsolidierte APIs, klare Dokumentation.

2. **Hybrides Entscheidungssystem**  
   Externe und interne Modelle, Retrieval, spezialisierte Adapter und ein lernender Decision-Layer werden unter strikter Governance kombiniert.

3. **Eigenes ABrain-Model / Brain**  
   Ein kleines, effizientes, stark scope-spezialisiertes neuronales Entscheidungsnetzwerk übernimmt Routing-, Planungs-, Priorisierungs- und Auswahlentscheidungen. LLMs bleiben mögliche Subsysteme, aber nicht der Kern der Systemidentität.

### 2.3 Was ABrain ausdrücklich **nicht** ist

- kein „autonom um jeden Preis“-Agentensystem
- kein Plugin-Marktplatz ohne Capability- und Policy-Kontrolle
- kein unkontrollierter Multi-Agent-Schwarm
- kein kurzfristiges Full-Foundation-Model-Projekt
- kein Architektur-Spielplatz mit parallelen Implementierungen derselben Kernfunktion

---

## 3. Leitprinzipien

- **Governance vor Autonomie**
- **Deterministische Sicherheitsgrenzen**
- **Ein kanonischer Pfad pro Kernfunktion**
- **Persistenz vor Lernen**
- **Evaluation vor Promotion**
- **System-MoE vor Modell-MoE**
- **Spezialisierung vor Modellgröße**
- **Effizienz, Kosten und Energie als echte Metriken**
- **Human-in-the-loop für kritische Aktionen**
- **Architekturvereinfachung vor Expansion**

---

## 4. Was aus den alten Roadmaps bleibt – und was nicht

### Beibehalten

- stärkere Persistenz und saubere Zustandsverwaltung
- bessere Testabdeckung, CI und Dokumentation
- API-/CLI-Härtung
- konfigurierbare Modell-/Provider-Anbindung
- strukturierte Logging-, Monitoring- und Audit-Pfade
- kontrollierte Erweiterbarkeit über Plugins/Adapter
- spätere Lern- und Trainingspfade auf Basis echter Laufzeitdaten

### Nicht als Primärziel übernehmen

- unmittelbarer Umbau in eine breit aufgespannte Microservice-Landschaft
- frühe Full-Scale-Meta-Learning- oder AutoML-Versprechen
- unkritische Übernahme historischer „alles ist schon implementiert“-Behauptungen
- großskaliges eigenes Foundation-Model-Training als Nahziel
- parallele Supervisor-/Router-/Manager-Pfade ohne klaren kanonischen Kern

---

## 5. Roadmap in Phasen

## Phase 0 – Konsolidierung abschließen (Blocker-Phase)

### Ziel
Den gehärteten Kern in einen belastbaren Zustand bringen. Ohne diese Phase sind spätere Lern-, Plugin- oder Brain-Schritte nicht verantwortbar.

### Deliverables

- Kanonische Kernpfade dokumentieren und verifizieren
- Parallele Implementierungen identifizieren und abbauen
- Persistenzlücken schließen
- Approval-, Plan-, Performance- und Training-State verlässlich speichern
- Security-Defaults vereinheitlichen
- Dokumentation auf aktuellen Stand bringen
- harte CI-Baseline herstellen

### Aufgaben

- [ ] Kanonische Kernarchitektur dokumentieren: Welche Module sind Source of Truth?
- [ ] Alle parallelen Routing-/Decision-/Approval-/Execution-Pfade inventarisieren
- [ ] Pending Approvals persistent machen
- [ ] PlanState persistent machen
- [ ] Performance-/Feedback-/Training-Daten versioniert persistieren
- [ ] Sicherheitsrelevante Defaults vereinheitlichen
- [ ] Konfigurationspfade vereinheitlichen (`.env`, YAML, runtime paths)
- [ ] Logging, Trace-IDs und Audit-Korrelation vereinheitlichen
- [ ] Historische Roadmap-/README-Aussagen gegen realen Code abgleichen
- [ ] „Coming soon“-, Pseudocode- oder Placebo-Dokumentation entfernen oder markieren
- [ ] CI-Minimum definieren: lint, typecheck, unit, integrations, smoke

### Exit-Kriterien

- keine unbekannten parallelen Kernpfade mehr
- kein kritischer Laufzeitstate nur im RAM
- alle sicherheitsrelevanten Kernpfade testbar und dokumentiert
- klare Trennung zwischen historischer und aktueller Doku

---

## Phase 1 – Evaluierbarkeit als Produktfeature

### Ziel
Änderungen am System reproduzierbar und regressionssicher machen.

### Deliverables

- Replay-Harness für Traces und Plans
- Policy-Compliance-Suite
- deterministische Regressionstests für Governance und Approval
- Baseline-Metriken für Routing, Kosten, Latenz und Fehlverhalten

### Aufgaben

- [ ] Replay-Harness auf Basis gespeicherter Traces bauen
- [ ] Vergleich „expected vs actual“ für Routing-Entscheide implementieren
- [ ] Policy-Testkatalog für deny / approval_required / allow erstellen
- [ ] Approval-Transition-Tests aufbauen
- [ ] Adapter-Output-Snapshots für Regressionstests definieren
- [ ] Routing-Baseline-Metriken definieren:
  - Erfolgsrate
  - Fehlrouting-Rate
  - P95-Latenz
  - Kosten pro Task
  - Anteil Fallbacks
- [ ] Safety-Metriken definieren:
  - Policy-Compliance-Rate
  - unerlaubte Side-Effects
  - falsche Tool-Aufrufe
  - Approval-Bypass-Versuche
- [ ] CI-Gates für Replay und Compliance aktivieren

### Exit-Kriterien

- jede relevante Kernänderung kann gegen gespeicherte Fälle geprüft werden
- Policy-Regressionen werden vor Merge sichtbar
- es gibt einen belastbaren Vorher-/Nachher-Vergleich für spätere ML-Schritte

---

## Phase 2 – Kontrollierte Erweiterbarkeit (Plugins, Adapter, Tools)

### Ziel
ABrain erweiterbar machen, ohne Governance und Auditierbarkeit zu verlieren.

### Deliverables

- kontrolliertes Plugin-/Adapter-Modell
- Capability-Scopes
- Policy-Bindings pro Tool/Adapter
- Output-Schemas und Validatoren
- Budgetierung für Kosten, Latenz und Rate Limits

### Aufgaben

- [ ] Plugin-/Adapter-Manifest spezifizieren
- [ ] Capabilities formal beschreiben
- [ ] jedem Tool/Adapter Policy-Regeln zuordnen
- [ ] Eingabe- und Ausgabe-Schemas erzwingen
- [ ] Output-Validatoren für kritische Aktionen bauen
- [ ] Sandboxing-/Isolation-Regeln definieren
- [ ] Kosten- und Latenzbudgets pro Adapter einführen
- [ ] Audit-Events für jeden Tool-Call standardisieren
- [ ] Risk-Tiering pro Plugin/Adapter einführen
- [ ] Security-Tests gegen unsichere Plugins/Prompt Injection aufbauen

### Exit-Kriterien

- neue Integrationen erweitern das System, ohne neue Schattenpfade zu erzeugen
- jeder Adapter ist capability-, policy- und audit-aware
- kein Tool darf implizit außerhalb seines Scopes handeln

---

## Phase 3 – Retrieval- und Wissensschicht

### Ziel
ABrain um eine sichere Wissens- und Kontextschicht erweitern, ohne untrusted content direkt handlungswirksam zu machen.

### Deliverables

- Retrieval-Layer
- ingestierbare Wissensquellen
- Untrusted-Content-Sanitization
- Quellenbezug für Planungs- und Erklärpfade

### Aufgaben

- [ ] Wissensquellen klassifizieren: trusted / internal / external / untrusted
- [ ] Ingestion-Pipeline mit Metadaten und Provenienz bauen
- [ ] Retrieval-API definieren
- [ ] RAG nur für Erklärung, Planung und Assistenz freigeben, nicht direkt für kritische Actions
- [ ] Quellennachweise in Explainability/Audit integrieren
- [ ] Prompt-Injection-Abwehr an Retrieval-Grenzen implementieren
- [ ] PII-/Lizenz-/Retention-Regeln für Wissensquellen definieren
- [ ] Benchmarks für Retrieval-Qualität und Antwortstabilität aufsetzen

### Exit-Kriterien

- Retrieval verbessert Qualität und Aktualität messbar
- externe Inhalte können Governance nicht stillschweigend verschieben
- Datenherkunft ist auditierbar

---

## Phase 4 – System-Level MoE und hybrides Modellrouting

### Ziel
ABrain als hybrides Multi-Model-System ausbauen: verschiedene Modelle und Ausführungspfade werden systemisch geroutet, nicht über ein einzelnes „Alles-Modell“.

### Deliverables

- Multi-Modell-Routing
- Provider-/Model-Registry
- Budget-aware Dispatching
- Fallback-Strategien
- On-device-/lokale Modelle für Teilaufgaben

### Aufgaben

- [ ] Modell-/Provider-Registry mit Metadaten aufbauen
- [ ] Modelle nach Zweck klassifizieren:
  - Planung
  - Klassifikation
  - Ranking
  - Retrieval-Hilfe
  - kurze lokale Assistenz
  - Spezialmodelle
- [ ] Routing nach Kosten, Latenz, Risiko und Qualitätsbedarf implementieren
- [ ] Fallback-Kaskaden definieren
- [ ] lokale/kleine Modelle für einfache Klassifikation, Ranking und Guardrails prüfen
- [ ] Quantisierungs- und Distillationspfad für lokale Modelle aufbauen
- [ ] KPI-Vergleiche zwischen externen und internen Pfaden etablieren

### Exit-Kriterien

- ABrain wählt Ausführungspfade nachvollziehbar und budgetbewusst
- einfache Aufgaben benötigen nicht automatisch teure General-LLMs
- hybrides Routing bringt messbaren Mehrwert

---

## Phase 5 – LearningOps für kontrolliertes Lernen

### Ziel
Aus Laufzeitdaten lernen, ohne Sicherheitsgrenzen oder Produktionsstabilität zu gefährden.

### Deliverables

- Dataset Builder aus Traces, Approvals, Outcomes
- Offline-Training-Pipeline
- Eval- und Safety-Regressionen vor Modellpromotion
- Modellversionierung und Rollback

### Aufgaben

- [ ] Trainingsdaten-Schema für Decision-/Routing-Lernen definieren
- [ ] Datensätze aus Traces, Approvals und Outcomes generieren
- [ ] Datenqualitätsregeln aufbauen
- [ ] Offline-Trainingsjobs definieren
- [ ] Modellartefakte versionieren
- [ ] Eval-Suite für neue Modellversionen aufbauen
- [ ] Canary-/Shadow-Rollout für neue Decision-Modelle einführen
- [ ] Rollback-Mechanismus definieren
- [ ] Online-Lernen auf „best effort“ begrenzen, bis Offline-Pipeline belastbar ist

### Exit-Kriterien

- kein unkontrolliertes Live-Lernen im Kernpfad
- jede neue Modellversion ist testbar, vergleichbar und reversibel
- Feedback aus Genehmigungen und realen Outcomes wird systematisch nutzbar

---

## Phase 6 – ABrain Brain v1: kleines neuronales Entscheidungsnetzwerk

### Ziel
Den heutigen heuristisch-neuronalen Routing-Scorer zu einem echten, aber kontrollierten Entscheidungsnetzwerk weiterentwickeln.

### Definition von „ABrain Brain v1“

Nicht: ein großes generisches LLM.  
Sondern: ein **kleines, effizientes, scope-spezialisiertes Entscheidungsmodell**, das unter Governance Vorschläge macht für:

- Agent-/Adapter-Auswahl
- Werkzeugwahl
- Planpriorisierung
- Eskalation / Approval-Bedarf
- Budget- und Risikoabwägung
- ggf. Abbruch statt Ausführung

### Mögliche Architekturpfade

- MLP/Tabular + Embeddings für erste produktive Version
- kleines Transformer-basiertes Entscheidungsmodell für Kontextfenster über Traces/Plans
- GNN-Komponenten für Agent-/Capability-/Plan-Graphen
- hierarchische Policy-Netze für mehrstufige Entscheidungen
- constrained optimization / multi-objective scoring statt reiner Accuracy-Optimierung

### Aufgaben

- [ ] Zielvariablen des Decision-Netzes formalisieren
- [ ] Zustandsrepräsentation definieren:
  - Task-Merkmale
  - Kontext
  - Budget
  - Policy-Signale
  - Verlauf
  - Performance-Historie
- [ ] Trainingsziele definieren:
  - Top-k Routing Accuracy
  - Policy-Compliance-preserving ranking
  - Cost-aware selection
  - Escalation prediction
- [ ] Shadow-Mode für Brain-v1 einführen
- [ ] Brain-v1 gegen heuristische Baseline evaluieren
- [ ] Brain-v1 nur als Vorschlagsmodell ausrollen, nicht als Policy-Ersatz

### Exit-Kriterien

- das Decision-Netzwerk ist reproduzierbar besser als die Baseline in klar definierten Metriken
- es verletzt keine Safety- oder Governance-Invarianten
- es reduziert Fehlrouting, unnötige Kosten oder unnötige Genehmigungen messbar

---

## Phase 7 – Fortgeschrittenes Brain: hierarchisch, hybrid, simuliert trainierbar

### Ziel
ABrain schrittweise von einem reinen Routing-Modell zu einem breiteren Entscheidungsnetzwerk weiterentwickeln.

### Fokus

- hierarchische Entscheidungen
- simulationsgestütztes Training
- optional offline RL / constrained RL
- World-Model-artige Repräsentationen für Pläne, nicht für offene General Intelligence

### Aufgaben

- [ ] Simulationsumgebung für wiederkehrende Task-Klassen bauen
- [ ] Gegenfaktische Evaluationen ermöglichen
- [ ] hierarchisches Decision-Making testen
- [ ] constrained RL nur in Sandbox-Umgebungen evaluieren
- [ ] graphbasierte Zustandsrepräsentationen prüfen
- [ ] Multi-Objective-Optimierung (Erfolg, Kosten, Risiko, Energie) einführen

### Exit-Kriterien

- Nutzen gegenüber Brain v1 ist empirisch belegt
- zusätzliche Komplexität ist betrieblich vertretbar
- keine Verlagerung kritischer Sicherheitslogik in schwer erklärbare Blackboxes

---

## 6. Querschnitts-Workstreams

## 6.1 Sicherheit

- [ ] Least Privilege für Modelle, Adapter und Tools
- [ ] strikte Trennung zwischen untrusted input und action layer
- [ ] Output-Validierung für strukturierte Actions
- [ ] Approval-Pflicht für risikoreiche Operationen
- [ ] Rate Limits, Auth, AuthZ, Secret Hygiene
- [ ] Security-Testfälle gegen Prompt Injection, Tool Misuse, Excessive Agency
- [ ] standardisierte Audit-Exports

## 6.2 Dokumentation

- [ ] klare Trennung: historisch / aktuell / experimentell
- [ ] Architekturdiagramme für Kernpfad, Plugin-Pfad, LearningOps
- [ ] Dokumentation pro kanonischem Pfad
- [ ] Experimente explizit als solche kennzeichnen
- [ ] falsche oder veraltete Implementierungsbehauptungen entfernen

## 6.3 Observability

- [ ] korrelierbare Trace-IDs durch den gesamten Kernpfad
- [ ] strukturierte Logs
- [ ] Erfolgs-, Kosten-, Latenz-, Sicherheitsmetriken
- [ ] Dashboards für Routing, Approvals, Incidents, Modellvergleiche

## 6.4 Daten und Governance

- [ ] Datenschema für Training und Auswertung
- [ ] Provenienz und Lizenzstatus je Datenquelle
- [ ] PII-Strategie
- [ ] Retention- und Löschkonzept
- [ ] reproduzierbare Datensplits

## 6.5 Effizienz und Green AI

- [ ] Energieverbrauch pro Modellpfad messen
- [ ] Kosten pro Task und pro Modellpfad reporten
- [ ] Quantisierung/Distillation für lokale Spezialmodelle evaluieren
- [ ] unnötig große Modelle durch Routing und Retrieval vermeiden

---

## 7. Technische Priorisierung (Impact / Reihenfolge)

### Höchste Priorität

1. Phase 0 – Konsolidierung abschließen
2. Phase 1 – Evaluierbarkeit / Replay / Compliance
3. Phase 2 – kontrolliertes Plugin-/Adapter-Modell
4. Phase 3 – Retrieval- und Wissensschicht

### Danach

5. Phase 4 – System-Level MoE / hybrides Modellrouting
6. Phase 5 – LearningOps
7. Phase 6 – Brain v1

### Langfristig und nur bei klarer Datenlage

8. Phase 7 – fortgeschrittenes Entscheidungsnetzwerk
9. größere interne Modellforschung
10. komplexere RL- oder neurosymbolische Erweiterungen

---

## 8. KPI-Rahmen

### Systemmetriken

- Task-Erfolgsrate
- Fehlrouting-Rate
- P50/P95-Latenz
- Kosten pro Task
- Energie pro Task
- Incident-Rate

### Governance-Metriken

- Policy-Compliance-Rate
- unerlaubte Side-Effects
- Anteil korrekt eskalierter Fälle
- Anteil unnötiger Genehmigungen
- Approval-Latenz

### Lern-/Modellmetriken

- Top-1 / Top-k Routing Accuracy
- Calibration / Confidence-Fehler
- OOD-Stabilität
- Drift-Indikatoren
- Shadow-vs-Production-Vergleich

### Produktmetriken

- Anteil lokal lösbarer Tasks
- Reduktion externer Modellkosten
- Wiederverwendbarkeit von Entscheidungen
- nachvollziehbare Explainability-Rate

---

## 9. Definition of Done pro größerem Schritt

Ein Schritt gilt erst dann als abgeschlossen, wenn:

- Architekturpfad klar dokumentiert ist
- Tests vorhanden sind
- Security-Betrachtung dokumentiert ist
- Observability vorhanden ist
- Rollback oder Fallback definiert ist
- keine unmarkierten Parallelpfade entstanden sind
- README / Doku / Changelog angepasst wurden

---

## 10. Explizite Nicht-Ziele für die nächsten Phasen

- sofortiges Training eines großen eigenen Foundation Models
- Verlagerung der Governance in ein uninterpretierbares Modell
- parallele Rewrite-Projekte ohne produktiven Mehrwert
- Plugin-Ökosystem ohne Sandboxing und Capability-Grenzen
- Online-RL in produktionsnahen kritischen Pfaden ohne starke Offline-Evaluation

---

## 11. Empfohlene Reihenfolge der nächsten konkreten Umsetzungen

### Nächste 4–8 Wochen

- [ ] Konsolidierungsinventur abschließen
- [ ] Persistenzlücken schließen
- [ ] Replay-Harness MVP bauen
- [ ] Policy-Compliance-Testkatalog aufsetzen
- [ ] Dokumentation historisch vs. aktuell bereinigen

### Danach

- [ ] Plugin-/Adapter-Spezifikation finalisieren
- [ ] sichere Retrieval-Schicht einführen
- [ ] Modell-/Provider-Registry vereinheitlichen
- [ ] System-MoE-Routing mit Budgets testen

### Erst danach

- [ ] Offline-Dataset-Builder aus Traces/Approvals/Outcomes bauen
- [ ] LearningOps-Pipeline aufsetzen
- [ ] Brain-v1 im Shadow-Mode trainieren und vergleichen

---

## 12. Schlussformel

Die Roadmap ist absichtlich konservativ. ABrain gewinnt mittelfristig nicht dadurch, dass es möglichst schnell „mehr KI“ auf die bestehende Architektur legt, sondern dadurch, dass es

- verlässlich entscheidet,
- sicher eskaliert,
- sauber dokumentiert,
- reproduzierbar lernt,
- und erst danach schrittweise ein eigenes kleines Entscheidungsnetzwerk aufbaut.

Damit bleibt ABrain technisch ernstzunehmend und erweitert seinen Umfang auf eine Weise, die betrieblich, sicherheitstechnisch und ökonomisch tragfähig ist.
