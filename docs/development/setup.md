# Entwicklungssetup

Dieses Dokument beschreibt, wie Sie eine lokale Entwicklungsumgebung für den aktuellen ABrain-Stand einrichten.

## Voraussetzungen

- Python >= 3.10
- Git
- Docker (für die Services)

## Repository klonen

```bash
git clone https://github.com/Modularium/ABrain.git
cd Agent-NN
```

Der lokale Ordnername `Agent-NN` darf aus Kompatibilitätsgründen vorerst bestehen bleiben. Sichtbare Produktidentität und Remote liegen aber bei `ABrain`.

## Abhängigkeiten installieren

```bash
poetry install
```

## Services starten

Der kanonische Runtime-Stack liegt in `services/*`. Lokale Full-Stack- oder Legacy-MCP-Pfade sind nicht die Referenz für den neuen Kern.

Für den stabilisierten Foundations-Pfad sind die wichtigsten Prüfkommandos:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/decision tests/execution tests/adapters tests/core tests/services \
  tests/integration/test_node_export.py
```

## Tests ausführen

Nutze für breitere lokale Service-Experimente weiterhin die dokumentierten `docker compose`- und Skriptpfade, aber bewerte deren Ergebnisse gegen den kanonischen Core und nicht gegen historische Supervisor-/MCP-Altpfade.

## Linting

```bash
ruff check .
pytest tests/decision tests/execution tests/adapters tests/core tests/services
```
