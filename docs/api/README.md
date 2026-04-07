# API Einstieg

Die REST-Schnittstellen der ABrain-Services sind in OpenAPI beschrieben. Diese Seite ist ein kompakter Überblick, keine vollständige Vertragsgarantie für jede historische Route.

Für den gehärteten Integrationspfad sind der laufende OpenAPI-Stand der aktiven FastAPI-Apps sowie die Core-Schicht unter `services/core.py` und `core/*` maßgeblich.

Deaktivierte historische Pfade wie der fruehere Plugin-Agent-Service werden
nicht mehr als aktuelle OpenAPI-Spezifikation veroeffentlicht.

- Registry: `/agents`, `/register`
- Dispatcher: `/task`
- Session Manager: `/start_session`, `/update_context`, `/context/{id}`
- Vector Store: `/add_document`, `/vector_search`
- LLM Gateway: `/generate`, `/embed`

Einen Gesamtüberblick liefert [openapi-overview.md](openapi-overview.md).
