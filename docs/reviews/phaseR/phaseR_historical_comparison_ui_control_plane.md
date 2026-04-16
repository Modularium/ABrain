# Phase R — Domain 7: UI / Control Plane / UX
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**

`monitoring/agen-nn_dashboard.tsx` — Vollständiges React-Dashboard (Mock-Daten):
- **System Overview:** CPU/GPU/Memory/Disk Usage (numerisch + visuell), Active Agents, Task Queue Size, Total Tasks Completed, Avg Response Time.
- **Models Tab:** Tabelle mit LLM-Models (Name, Type, Source, Version, Status, Requests, Latency).
- **Active Tasks Tab:** Task-Liste mit ID, Type, Agent, Status (running/completed/queued), Duration.
- **System Components Tab:** Komponenten-Status-Übersicht (Supervisor Agent, MLflow, Vector Store, Cache Manager) mit Version und lastUpdated.
- **Logs Tab:** Log-Einträge mit Level (INFO/WARNING/ERROR), Timestamp, Message.
- **Agents Tab:** Agent-Tabelle mit Name, Domain, Status, Tasks, SuccessRate, AvgResponse, LastActive.
- **Knowledge Bases Tab:** KB-Tabelle mit Name, Documents, LastUpdated, Size, Status.
- **A/B Testing Tab:** Test-Liste mit ID, Name, Status, Variants, Winner, Improvement.
- **Security Events Tab:** Security-Events mit Type, Timestamp, Details.
- Auto-Refresh alle 30 Sekunden.
- Dark/Light-Theme-Toggle.
- Lucide-React Icons.

`monitoring/agent_dashboard.py` — Python-Terminal-Dashboard (System-Metriken).
`monitoring/system_monitor.py` — System-Metriken-Kollektor.

`archive/ui_legacy/legacy_frontend/` — Sehr frühes Frontend (kaum dokumentiert).
`archive/ui_legacy/monitoring_dashboard/` — Ältere Monitoring-Dashboard-Version.

**Wie war die Architektur?**
- Mock-Daten: Das Dashboard zeigte simulierte Daten mit `setTimeout` statt echter API-Calls.
- Kein Zustand-Management (kein Zustand-Store).
- Kein Routing.
- Einzelne große Komponente.
- Kein Build-System (kein Vite/webpack).

**Welche Probleme gab es?**
- Alle Daten waren Mock: Das Dashboard war nie mit einer echten API verbunden.
- Monolithische Komponente: Eine einzige TSX-Datei mit allem.
- Kein State-Management.
- Kein Routing zwischen Seiten.
- Python-Dashboard war terminal-only (nicht produktiv nutzbar).

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`frontend/agent-ui/` — React + TypeScript + Zustand + Vite + Tailwind:

**Pages (18 Seiten):**
- `Dashboard.tsx` — System-Übersicht.
- `AgentsPage.tsx` — Agent-Katalog.
- `TasksPage.tsx` — Task-Ausführung und -Historie.
- `RoutingPage.tsx` — Routing-Entscheidungen.
- `TracesPage.tsx` — Audit-Traces und Explainability.
- `ApprovalsPage.tsx` — HITL-Approval-Queue.
- `ChatPage.tsx` — Chat-Interface.
- `FeedbackPage.tsx` — Feedback-Eingabe.
- `MetricsPage.tsx` — Prometheus-Metriken.
- `MonitoringPage.tsx` — Monitoring-Übersicht.
- `PlansPage.tsx` — Plan-Ausführungs-Übersicht.
- `RoutingPage.tsx` — Routing-Visualisierung.
- `AdminPage.tsx` — Admin-Funktionen (via AdminBot).
- `SettingsPage.tsx` — Einstellungen.
- `DebugPage.tsx` — Debug-Tools.

**UI-Komponenten:**
- Header, Sidebar, Badge, Button, Card, Input, LoadingSpinner, Modal, ProgressBar, Toast.

**State Management:** Zustand.
**Build:** Vite. Type-check: tsc --noEmit. Build erfolgreich (7.35s), PWA (11 entries precached).

**Wie ist es strukturiert?**
- Vollständig modular: Jede Seite ist eine eigene Komponente.
- Zustand-Store für globalen State.
- React Router für Navigation.
- Tailwind CSS für Styling.
- Echte API-Calls (nicht Mock-Daten).
- TypeScript + strenge Typen.

---

### Bewertung

**Was war früher schlechter?**
- Dashboard war nie produktiv (nur Mock-Daten).
- Monolithische Struktur.
- Kein Build-System, kein TypeScript.
- Python-Terminal-Dashboard hatte keinen Browser-Zugang.

**Was ist heute besser?**
- Echte API-Integration.
- Vollständig modular.
- TypeScript + Zustand + Vite = produktionsbereit.
- 18 dedizierte Seiten.
- PWA-fähig.

**Wo gab es frühere Stärken?**
- Das alte Dashboard hatte **substanziell mehr angezeigten Scope**: Knowledge Bases, A/B Tests, Security Events, System Components (mit Version und lastUpdated), CPU/GPU/Memory/Disk-Metriken, LLM-Models mit Requests und Latency. Auch wenn es Mock-Daten waren, zeigten sie *was das System können sollte*.
- **A/B-Testing-Tab**: In der alten Monitoring UI gab es einen direkten Tab für A/B-Tests (auch wenn Mock). Heute fehlt ein solches UX-Konzept.
- **Knowledge Base Tab**: Übersicht über Wissensdatenbanken mit Dokumentenzahl, Größe, Status. Heute gibt es keine KB-Verwaltung in der UI.
- **System Components mit Versionen**: Status-Übersicht aller Subsysteme mit Versionsnummer und Last-Updated-Zeit.
- **Security Events Tab**: Übersicht über sicherheitsrelevante Ereignisse direkt in der UI.
- **Logs Tab**: Direkte Log-Ansicht mit Level-Filtering. Heute gibt es keine Log-Ansicht in der UI (nur Traces).

---

### Gap-Analyse

**Was fehlt heute in der UI?**
- Keine **System-Health-Übersicht** mit CPU/GPU/Memory/Disk.
- Keine **Knowledge-Base-Verwaltung**.
- Kein **A/B-Testing-Tab** / Policy-Comparison.
- Kein **Security-Events-Log**.
- Keine **direkte Log-Ansicht** (aktuell: Traces, aber keine raw Logs).
- Keine **System-Komponenten-Status-Übersicht** mit Versionen.
- Kein **LLM-Model-Registry-Tab** (welche Modelle sind aktiv, welche Latenz).

**Welche Ideen sind verloren gegangen?**
- Systemweite Health-Visualisierung (CPU, GPU, Memory, Disk) — heute kein Äquivalent in der UI.
- Knowledge-Base-UI.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| Mock-Daten-Dashboard | A — bewusst verworfen |
| System Health Metrics (CPU/GPU/Disk) in UI | D — **kritisch fehlend** für Operations |
| Knowledge Base UI | C — fehlt, sinnvoll wenn KB-Feature existiert |
| A/B Testing Tab | B — interessant, aber kein A/B-Testing-Feature heute |
| Security Events Log in UI | C — fehlt, wäre nützlich |
| Log-Ansicht in UI | C — fehlt, Traces sind kein Ersatz |
| System Components Status-Übersicht | C — fehlt, wäre für Ops nützlich |
| LLM Model Registry Tab | B — interessant, wenn LLM-Abstraction zurückkehrt |
