# Contributing Guide

Vielen Dank für dein Interesse an ABrain. Dieses Projekt verwendet GitHub Flow.

## Setup

1. Forke das Repository und klone deine Kopie.
2. Erstelle eine virtuelle Umgebung und installiere die Python-Abhängigkeiten:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements-light.txt
   ```
3. Wenn du den Console-Entry `abrain-mcp` lokal erzeugen willst, installiere das
   Paket zusätzlich editable:
   ```bash
   python -m pip install -e .
   ```
4. Für das Frontend:
   ```bash
   cd frontend/agent-ui
   npm ci
   ```
5. Richte optionale Hooks ein:
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
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/state tests/mcp tests/approval tests/orchestration \
  tests/execution tests/decision tests/adapters tests/core \
  tests/services tests/integration/test_node_export.py
cd frontend/agent-ui && npm run type-check && npm run build && npm run lint
```

## Pull Requests

- Beschreibe Änderungen klar und verweise auf Issues.
- Füge Dokumentation und Tests hinzu, wenn nötig.
- Stelle sicher, dass die CI-Pipeline ohne Fehler durchläuft.

Weitere Details findest du unter
[docs/architecture/CANONICAL_REPO_STRUCTURE.md](docs/architecture/CANONICAL_REPO_STRUCTURE.md),
[docs/architecture/CANONICAL_RUNTIME_STACK.md](docs/architecture/CANONICAL_RUNTIME_STACK.md)
und [docs/guides/MCP_USAGE.md](docs/guides/MCP_USAGE.md).
