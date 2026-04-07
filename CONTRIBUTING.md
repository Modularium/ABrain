# Contributing Guide

Vielen Dank für dein Interesse an ABrain. Dieses Projekt verwendet GitHub Flow.

## Setup

1. Forke das Repository und klone deine Kopie.
2. Installiere Abhängigkeiten mit `pip install -r requirements.txt`.
   Alternativ kannst du `./scripts/install.sh --ci` nutzen, um alle
   benötigten Tools automatisiert zu installieren.
3. Richte optionale Hooks ein:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Branches

Entwickle auf einem Feature-Branch, der von `main` abzweigt.

## Tests und Linting

Vor jedem Pull Request müssen folgende Checks laufen:

```bash
ruff check .
mypy mcp
pytest
```

## Pull Requests

- Beschreibe Änderungen klar und verweise auf Issues.
- Füge Dokumentation und Tests hinzu, wenn nötig.
- Stelle sicher, dass die CI-Pipeline ohne Fehler durchläuft.

Weitere Details findest du unter [docs/development/contributing.md](docs/development/contributing.md) sowie im gehärteten Überblick unter [docs/architecture/PROJECT_OVERVIEW.md](docs/architecture/PROJECT_OVERVIEW.md).
