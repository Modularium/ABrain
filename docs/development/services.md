# Services Übersicht

> Status: Architekturüberblick. Für den sicherheitsrelevanten Referenzpfad sind zusätzlich `services/core.py`, `core/execution/dispatcher.py`, `core/tools/*` und `docs/architecture/PROJECT_OVERVIEW.md` maßgeblich.

Die Modular Control Plane besteht aus mehreren eigenständigen Services. Jeder Service stellt eine kleine FastAPI-Anwendung bereit.

| Service            | Port | Zweck                         |
|--------------------|------|-------------------------------|
| Dispatcher         | 8000 | Orchestriert Aufgaben         |
| Agent Registry     | 8001 | Verwalten registrierter Agenten |
| Session Manager    | 8002 | Speichert Gesprächskontexte   |
| Vector Store       | 8003 | Dokumentensuche               |
| LLM Gateway        | 8004 | Zugriff auf Sprachmodelle     |
| User Manager       | 8005 | Verwaltet Nutzerkonten und Token |
| Worker Dev         | 8101 | Beispiel-Worker für Code      |
| Worker OpenHands   | 8102 | Docker-Operationen            |
| Worker LOH         | 8103 | Pflegewissen                  |

## Startoptionen

Die Services können einzeln mit `python -m <module>` oder gemeinsam via Docker Compose gestartet werden. Beispiel:

```bash
docker-compose up dispatcher registry session-manager vector-store llm-gateway
```

Für Entwicklung kann jeder Service auch separat gestartet werden, um Logs leichter zu verfolgen.
