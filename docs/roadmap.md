# ABrain Roadmap

Diese Datei fasst die wichtigsten Schritte der Entwicklungsplanung zusammen.
Ausführliche To‑Do-Listen befinden sich in `ROADMAP.md`. Historische
Notizen sind unter `Roadmap.md` archiviert.

## Phase 1 – MCP-Grundlagen
- Aufteilung des Monolithen in Microservices
- Einführung des `ModelContext` und erster End‑to‑End-Test

## Phase 2 – Lernmechanismen
- Routing-Agent und Feedback-Schleife aktivieren
- Provider-System mit dynamischer Modellwahl

## Phase 3 – SDK & Frontend
- Python‑SDK und CLI bereitstellen
- Erste React-basierte Chat‑UI anbinden

## Phase 4 – Stabilisierung
- Vollständige Testabdeckung und Deployment‑Skripte
- Betriebsmetriken und Audit‑Logs einführen

## Phase 5 – Erweiterte Lernmechanismen
- Feinjustierung vorhandener Modelle via Reinforcement Learning und Few-Shot-Training.
- Aufbau einer Föderationsschicht, um mehrere ABrain-Instanzen zu koordinieren.
- Unterstützung für komplexe Multi-Agent-Aufgaben mit geteiltem Kontext.

## Phase 6 – Skalierung & Federation
- Lastverteilung und horizontale Skalierung der Worker-Dienste.
- Federation mit externen Agent-Plattformen über standardisierte APIs.
- Ausbau der Überwachungs- und Governance-Werkzeuge.

## Teamweitergabe & Onboarding
- Neue Entwickler starten am besten mit `docs/deployment.md` und `docs/maintenance.md`.
- Kernkomponenten befinden sich im canonical runtime stack unter `services/`; `mcp/` bleibt nur `legacy (disabled)`. Die React-Oberflaeche liegt unter `frontend/agent-ui`.
- Für Tests dient `tests/test_all.py` als Einstiegspunkt.

## Strategische Ziele
- Minimierung technischer Schulden durch klare Modultrennung.
- Weitere Automatisierung des Trainingsprozesses und Self-Healing der Dienste.
- Dokumentierte Entscheidungsprozesse in `docs/architecture/` fortführen.
