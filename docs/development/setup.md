# Entwicklungssetup

Dieses Dokument beschreibt, wie Sie eine lokale Entwicklungsumgebung für den aktuellen ABrain-Stand einrichten.

## Voraussetzungen

- Python >= 3.10
- Git
- Docker (für die Services)

## Repository klonen

```bash
git clone https://github.com/EcoSphereNetwork/Agent-NN.git
cd Agent-NN
```

## Abhängigkeiten installieren

```bash
poetry install
```

## Services starten

Die wichtigsten MCP-Services können über Docker Compose gestartet werden:

```bash
docker-compose up dispatcher registry session-manager
```

Nun ist der Dispatcher unter `http://localhost:8000` erreichbar.

## Tests ausführen

```bash
./tests/ci_check.sh
```

## Linting

```bash
ruff check .
mypy mcp
```
