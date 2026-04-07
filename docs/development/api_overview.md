# API- und CLI-Übersicht

Diese Datei fasst die aktuell vorhandenen Schnittstellen von ABrain zusammen.
Sie dient als Orientierung für das neue Developer SDK.

## REST-API (`api/`)
- **`server.py`** startet eine FastAPI-Anwendung mit Versionierung unter `/api/v2`.
- **`endpoints.py`** definiert Routen für Aufgabenverwaltung (`/tasks`), Agentsteuerung (`/agents`), Modelldaten (`/models`), Knowledge-Base (`/knowledge-bases`) und ein Login (`/token`).
- Antworten und Payloads sind in `api/models.py` als Pydantic-Modelle beschrieben.

## API‑Gateway (`api_gateway/`)
- Vermittelt externe Aufrufe an die MCP‑Services (LLM‑Gateway, Dispatcher, Session-Manager).
- Enthält Ratenbegrenzung, JWT‑Verifikation und einfache Proxy‑Routen wie `/llm/generate` oder `/chat`.

## Kommandozeilenwerkzeuge (`cli/`)
- Verschiedene Click‑basierte Skripte für Agent‑Steuerung und LLM‑Backends.
- `unified_cli.py` bietet eine Sammlung von Unterbefehlen (`chat`, `llm`, `batch`, `monitor`).
- Die CLI nutzt primär lokale Agenten-Klassen und ruft kaum HTTP‑APIs auf.

## Manager‑Klassen (`managers/`)
- `AgentManager` kapselt Agent-Lifecycle und Auswahl über einen `HybridMatcher`.
- Weitere Manager regeln Modelle, Deployment und Überwachung.

Diese Struktur zeigt, dass schon REST-Endpunkte und lokale CLIs existieren.
Für das geplante SDK sollen vor allem `/task`, `/agents`, die Session-API und der
Vector‑Store abstrahiert werden, damit externe Anwendungen sie leicht ansprechen
können.
