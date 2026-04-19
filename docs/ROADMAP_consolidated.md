# ABrain Roadmap (konsolidiert)

> Status: Konsolidierte Roadmap für den aktuellen ABrain-Kurs.  
> Sie ersetzt keine laufenden Architektur- und Review-Dokumente, sondern bündelt den belastbaren Entwicklungspfad aus den historischen Roadmaps, den Review-Ergebnissen und der neu definierten Produktstrategie.  
> Leitbild: **Control > Autonomy**. ABrain entwickelt sich zuerst als gehärtetes, policy-gesteuertes System und danach schrittweise zu einem hybriden Entscheidungsnetzwerk („Brain“), nicht zu einem generischen Hype-LLM.
>
> **Entwicklungsstatus (Stand 2026-04-19):** Phasen 0–6 auf `main` abgeschlossen. Querschnittsarbeit in §6 läuft weiter. Phase 7 bleibt deferred bis ein Real-Traffic-`promote`-Verdict des `BrainOperationsReporter` vorliegt. Checkboxen unten spiegeln den kanonischen Stand gemäß `docs/reviews/`-Historie; Pointer in Klammern verweisen auf den zugehörigen Review.

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

- [x] Kanonische Kernarchitektur dokumentieren: Welche Module sind Source of Truth? (`docs/architecture/CANONICAL_REPO_STRUCTURE.md`, Phase O)
- [x] Alle parallelen Routing-/Decision-/Approval-/Execution-Pfade inventarisieren (`phaseO_full_repo_inventory.md`, `phaseR2_managers_*`)
- [x] Pending Approvals persistent machen (`phaseN_persistent_state_review.md`)
- [x] PlanState persistent machen (`phaseN_persistent_state_review.md`)
- [x] Performance-/Feedback-/Training-Daten versioniert persistieren (`phase5_L4_review.md` — ModelRegistry)
- [x] Sicherheitsrelevante Defaults vereinheitlichen (`phaseS21_security_tests_review.md`)
- [x] Konfigurationspfade vereinheitlichen (`.env`, YAML, runtime paths) (`setup_modernization_review.md`, `setup_one_liner_review.md`)
- [x] Logging, Trace-IDs und Audit-Korrelation vereinheitlichen (`phaseK_audit_explainability_review.md`, `phaseS10_trace_forensics_review.md`)
- [x] Historische Roadmap-/README-Aussagen gegen realen Code abgleichen (`post_cleanup_readme_setup_onboarding_audit.md`)
- [x] „Coming soon"-, Pseudocode- oder Placebo-Dokumentation entfernen oder markieren (`phaseO_canonicalization_cleanup_review.md`, §6.2 this turn)
- [x] CI-Minimum definieren: lint, typecheck, unit, integrations, smoke (`phaseS13_ci_gates_review.md`)

### Exit-Kriterien

- [x] keine unbekannten parallelen Kernpfade mehr
- [x] kein kritischer Laufzeitstate nur im RAM
- [x] alle sicherheitsrelevanten Kernpfade testbar und dokumentiert
- [x] klare Trennung zwischen historischer und aktueller Doku (§6.2 this turn: `phase_doc_audit_inventory.md`)

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

- [x] Replay-Harness auf Basis gespeicherter Traces bauen (`phaseS11_replay_compliance_review.md`)
- [x] Vergleich „expected vs actual" für Routing-Entscheide implementieren (`phaseS11_replay_compliance_review.md`)
- [x] Policy-Testkatalog für deny / approval_required / allow erstellen (`phaseS12_policy_catalog_review.md`)
- [x] Approval-Transition-Tests aufbauen (`phaseI_hitl_approval_review.md`)
- [x] Adapter-Output-Snapshots für Regressionstests definieren (`phaseS11_replay_compliance_review.md`)
- [x] Routing-Baseline-Metriken definieren (`phaseS14_safety_metrics_routing_kpis_review.md`):
  - Erfolgsrate
  - Fehlrouting-Rate
  - P95-Latenz
  - Kosten pro Task
  - Anteil Fallbacks
- [x] Safety-Metriken definieren (`phaseS14_safety_metrics_routing_kpis_review.md`):
  - Policy-Compliance-Rate
  - unerlaubte Side-Effects
  - falsche Tool-Aufrufe
  - Approval-Bypass-Versuche
- [x] CI-Gates für Replay und Compliance aktivieren (`phaseS13_ci_gates_review.md`)

### Exit-Kriterien

- [x] jede relevante Kernänderung kann gegen gespeicherte Fälle geprüft werden
- [x] Policy-Regressionen werden vor Merge sichtbar
- [x] es gibt einen belastbaren Vorher-/Nachher-Vergleich für spätere ML-Schritte

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

- [x] Plugin-/Adapter-Manifest spezifizieren (`phaseS15_adapter_manifests_review.md`)
- [x] Capabilities formal beschreiben (`phaseS15_adapter_manifests_review.md`, `phaseS12_policy_catalog_review.md`)
- [x] jedem Tool/Adapter Policy-Regeln zuordnen (`phaseS12_policy_catalog_review.md`)
- [x] Eingabe- und Ausgabe-Schemas erzwingen (`phaseS15_adapter_manifests_review.md`)
- [x] Output-Validatoren für kritische Aktionen bauen (`phaseS19_execution_audit_events_review.md`)
- [x] Sandboxing-/Isolation-Regeln definieren (`phaseS20_adapter_budgets_isolation_review.md`)
- [x] Kosten- und Latenzbudgets pro Adapter einführen (`phaseS20_adapter_budgets_isolation_review.md`)
- [x] Audit-Events für jeden Tool-Call standardisieren (`phaseS19_execution_audit_events_review.md`)
- [x] Risk-Tiering pro Plugin/Adapter einführen (`phaseS12_policy_catalog_review.md`)
- [x] Security-Tests gegen unsichere Plugins/Prompt Injection aufbauen (`phaseS21_security_tests_review.md`)

### Exit-Kriterien

- [x] neue Integrationen erweitern das System, ohne neue Schattenpfade zu erzeugen
- [x] jeder Adapter ist capability-, policy- und audit-aware
- [x] kein Tool darf implizit außerhalb seines Scopes handeln

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

- [x] Wissensquellen klassifizieren: trusted / internal / external / untrusted (`phaseR1_retrieval_classification_review.md`)
- [x] Ingestion-Pipeline mit Metadaten und Provenienz bauen (`phase3_R2_review.md`)
- [x] Retrieval-API definieren (`phase3_R3_review.md`)
- [x] RAG nur für Erklärung, Planung und Assistenz freigeben, nicht direkt für kritische Actions (`phase3_R4_review.md`)
- [x] Quellennachweise in Explainability/Audit integrieren (`phase3_R4_review.md`)
- [x] Prompt-Injection-Abwehr an Retrieval-Grenzen implementieren (`phase3_R5_review.md`)
- [ ] PII-/Lizenz-/Retention-Regeln für Wissensquellen definieren — *teilweise: Retention-Scanner read-only ☑ (`phase_gov_retention_scanner_review.md`); PII/Lizenz offen*
- [x] Benchmarks für Retrieval-Qualität und Antwortstabilität aufsetzen (`phase3_R6_review.md`)

### Exit-Kriterien

- [x] Retrieval verbessert Qualität und Aktualität messbar
- [x] externe Inhalte können Governance nicht stillschweigend verschieben
- [x] Datenherkunft ist auditierbar

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

- [x] Modell-/Provider-Registry mit Metadaten aufbauen (`phaseS9_provider_abstraction_review.md`, `phase4_M1_review.md`)
- [x] Modelle nach Zweck klassifizieren (`phase4_M2_review.md`):
  - Planung
  - Klassifikation
  - Ranking
  - Retrieval-Hilfe
  - kurze lokale Assistenz
  - Spezialmodelle
- [x] Routing nach Kosten, Latenz, Risiko und Qualitätsbedarf implementieren (`phase4_M3_review.md`)
- [x] Fallback-Kaskaden definieren (`phaseS4_provider_fallback_review.md`, `phaseS4_2_soft_fallback_review.md`)
- [x] lokale/kleine Modelle für einfache Klassifikation, Ranking und Guardrails prüfen (`phase4_M4_review.md`)
- [ ] Quantisierungs- und Distillationspfad für lokale Modelle aufbauen — *deferred zusammen mit §6.5 Green-AI-Items*
- [x] KPI-Vergleiche zwischen externen und internen Pfaden etablieren (`phase4_M4_review.md`)

### Exit-Kriterien

- [x] ABrain wählt Ausführungspfade nachvollziehbar und budgetbewusst
- [x] einfache Aufgaben benötigen nicht automatisch teure General-LLMs
- [x] hybrides Routing bringt messbaren Mehrwert

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

- [x] Trainingsdaten-Schema für Decision-/Routing-Lernen definieren (`phase5_L1_review.md`)
- [x] Datensätze aus Traces, Approvals und Outcomes generieren (`phase5_L1_review.md`, `phase5_L2_review.md`)
- [x] Datenqualitätsregeln aufbauen (`phase5_L2_review.md`)
- [x] Offline-Trainingsjobs definieren (`phase5_L3_review.md`)
- [x] Modellartefakte versionieren (`phase5_L4_review.md` — ModelRegistry)
- [x] Eval-Suite für neue Modellversionen aufbauen (`phase5_L3_review.md`)
- [x] Canary-/Shadow-Rollout für neue Decision-Modelle einführen (`phase5_L5_review.md` — ShadowEvaluator)
- [x] Rollback-Mechanismus definieren (`phase5_L4_review.md`)
- [x] Online-Lernen auf „best effort" begrenzen, bis Offline-Pipeline belastbar ist (`phaseD_learning_system_review.md`)

### Exit-Kriterien

- [x] kein unkontrolliertes Live-Lernen im Kernpfad
- [x] jede neue Modellversion ist testbar, vergleichbar und reversibel
- [x] Feedback aus Genehmigungen und realen Outcomes wird systematisch nutzbar

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

- [x] Zielvariablen des Decision-Netzes formalisieren (`phase6_B1_review.md`)
- [x] Zustandsrepräsentation definieren (`phase6_B1_review.md`, `phase6_B4_review.md`):
  - Task-Merkmale
  - Kontext
  - Budget
  - Policy-Signale
  - Verlauf
  - Performance-Historie
- [x] Trainingsziele definieren (`phase6_B2_review.md`):
  - Top-k Routing Accuracy
  - Policy-Compliance-preserving ranking
  - Cost-aware selection
  - Escalation prediction
- [x] Shadow-Mode für Brain-v1 einführen (`phase6_B5_review.md`, `phase6_B6_review.md`)
- [x] Brain-v1 gegen heuristische Baseline evaluieren (`phase6_B6_review.md`, `phase6_obs_report_review.md`)
- [x] Brain-v1 nur als Vorschlagsmodell ausrollen, nicht als Policy-Ersatz (`phase6_B5_review.md`)

### Exit-Kriterien

- [ ] das Decision-Netzwerk ist reproduzierbar besser als die Baseline in klar definierten Metriken — *pending: Real-Traffic `promote`-Verdict durch `BrainOperationsReporter`*
- [x] es verletzt keine Safety- oder Governance-Invarianten
- [ ] es reduziert Fehlrouting, unnötige Kosten oder unnötige Genehmigungen messbar — *pending: Real-Traffic-Daten*

---

## Phase 7 – Fortgeschrittenes Brain: hierarchisch, hybrid, simuliert trainierbar

> **Status (2026-04-19):** Deferred. Erst eröffnet, wenn der Real-Traffic-`promote`-Verdict aus `BrainOperationsReporter` (Phase 6 Exit) vorliegt.

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

- [x] Least Privilege für Modelle, Adapter und Tools (`phaseS15_adapter_manifests_review.md`, `phaseS20_adapter_budgets_isolation_review.md`)
- [x] strikte Trennung zwischen untrusted input und action layer (`phase3_R5_review.md`)
- [x] Output-Validierung für strukturierte Actions (`phaseS19_execution_audit_events_review.md`)
- [x] Approval-Pflicht für risikoreiche Operationen (`phaseI_hitl_approval_review.md`)
- [x] Rate Limits, Auth, AuthZ, Secret Hygiene (`phaseS20_adapter_budgets_isolation_review.md`, `phaseS21_security_tests_review.md`)
- [x] Security-Testfälle gegen Prompt Injection, Tool Misuse, Excessive Agency (`phaseS21_security_tests_review.md`, `red_team_review_abrain_adminbot.md`)
- [x] standardisierte Audit-Exports (`docs/reviews/phase_gov_audit_export_review.md`, commit `319c42a8`)

## 6.2 Dokumentation

- [x] klare Trennung: historisch / aktuell / experimentell — *§6.2 this turn: `phase_doc_audit_inventory.md`*
- [ ] Architekturdiagramme für Kernpfad, Plugin-Pfad, LearningOps
- [x] Dokumentation pro kanonischem Pfad (`docs/architecture/*`, `docs/guides/*`)
- [x] Experimente explizit als solche kennzeichnen — *§6.2 this turn: historische Docs getaggt, experimentelle Docs müssen künftig `**Status:** Experimental` tragen*
- [x] falsche oder veraltete Implementierungsbehauptungen entfernen (`post_cleanup_readme_setup_onboarding_audit.md`, `phaseO_canonicalization_cleanup_review.md`)

## 6.3 Observability

- [x] korrelierbare Trace-IDs durch den gesamten Kernpfad (`phaseK_audit_explainability_review.md`, `phaseS10_trace_forensics_review.md`)
- [x] strukturierte Logs (`phaseS1_observability_feedback_review.md`)
- [x] Erfolgs-, Kosten-, Latenz-, Sicherheitsmetriken (`phaseS14_safety_metrics_routing_kpis_review.md`, `phase_gov_agent_performance_report_review.md`, commit `bd157ef5`)
- [x] Dashboards für Routing, Approvals, Incidents, Modellvergleiche (`phaseM_control_plane_review.md`, `phase6_obs_report_review.md`)

## 6.4 Daten und Governance

- [x] Datenschema für Training und Auswertung (`phase5_L1_review.md`, `phase6_B1_review.md`)
- [ ] Provenienz und Lizenzstatus je Datenquelle
- [ ] PII-Strategie
- [x] Retention- und Löschkonzept — *read-only Scanner ☑ (`phase_gov_retention_scanner_review.md`, commit `31f315fb`); destruktiver Pruner steht aus*
- [ ] reproduzierbare Datensplits

## 6.5 Effizienz und Green AI

- [ ] Energieverbrauch pro Modellpfad messen
- [x] Kosten pro Task und pro Modellpfad reporten (`phase_gov_agent_performance_report_review.md`, commit `bd157ef5`)
- [ ] Quantisierung/Distillation für lokale Spezialmodelle evaluieren
- [x] unnötig große Modelle durch Routing und Retrieval vermeiden (`phase4_M3_review.md`, `phase4_M4_review.md`)

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

- [x] Konsolidierungsinventur abschließen
- [x] Persistenzlücken schließen
- [x] Replay-Harness MVP bauen
- [x] Policy-Compliance-Testkatalog aufsetzen
- [x] Dokumentation historisch vs. aktuell bereinigen — *§6.2 this turn*

### Danach

- [x] Plugin-/Adapter-Spezifikation finalisieren
- [x] sichere Retrieval-Schicht einführen
- [x] Modell-/Provider-Registry vereinheitlichen
- [x] System-MoE-Routing mit Budgets testen

### Erst danach

- [x] Offline-Dataset-Builder aus Traces/Approvals/Outcomes bauen
- [x] LearningOps-Pipeline aufsetzen
- [x] Brain-v1 im Shadow-Mode trainieren und vergleichen

---

## 12. Schlussformel

Die Roadmap ist absichtlich konservativ. ABrain gewinnt mittelfristig nicht dadurch, dass es möglichst schnell „mehr KI“ auf die bestehende Architektur legt, sondern dadurch, dass es

- verlässlich entscheidet,
- sicher eskaliert,
- sauber dokumentiert,
- reproduzierbar lernt,
- und erst danach schrittweise ein eigenes kleines Entscheidungsnetzwerk aufbaut.

Damit bleibt ABrain technisch ernstzunehmend und erweitert seinen Umfang auf eine Weise, die betrieblich, sicherheitstechnisch und ökonomisch tragfähig ist.
