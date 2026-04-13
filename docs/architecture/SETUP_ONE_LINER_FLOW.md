# Setup One-Liner Flow

## Ziel

Der kanonische lokale Einstieg fuer einen frischen ABrain-Checkout ist genau ein Befehl:

```bash
./scripts/abrain setup
```

Alternativ kann derselbe Flow direkt ueber das Skript gestartet werden:

```bash
bash scripts/setup.sh
```

Beide Wege fuehren in denselben linearen Bootstrap. Es gibt keine zweite Setup-Architektur, keine Parallel-CLI und keine separate Runtime.

## Was der One-Liner tut

### 1. Systemgrundlage pruefen

- `python3`
- `npm`
- `requirements-light.txt`
- `pyproject.toml`
- `frontend/agent-ui/package.json`

### 2. Python-Umgebung vorbereiten

- `.venv` anlegen oder wiederverwenden
- `pip`, `setuptools`, `wheel` aktualisieren, wenn eine frische Venv erstellt wurde
- `.env` aus `.env.example` erzeugen, falls noch keine lokale `.env` existiert

### 3. Python-Dependencies installieren

- Installation aus `requirements-light.txt`
- Ziel: aktiver Runtime-Kern fuer CLI, API Gateway, MCP v2 und Test-Suite

### 4. CLI und editable Installation vorbereiten

- `poetry-core` sicherstellen
- `pip install -e . --no-deps --no-build-isolation`
- `abrain-mcp` regenerieren
- Bash-CLI-Smoke ueber `./scripts/abrain --version`

### 5. API Gateway verifizieren

- `api_gateway.main` importieren
- zentrale Kontrollrouten pruefen
- kanonischen Startpfad ausgeben

### 6. MCP v2 verifizieren

- `initialize`
- `tools/list`
- Console-Entry-Metadaten fuer `abrain-mcp`

### 7. Frontend vorbereiten

- `npm ci`
- `npm run type-check`
- `npm run build`

### 8. Ready-State ausgeben

Der Abschluss meldet klar:

- `[OK] CLI bereit`
- `[OK] MCP bereit`
- `[OK] API bereit`
- `[OK] UI gebaut`

und nennt die kanonischen Startpfade.

## Optionale Teilpfade

Die One-Liner-Form ist kanonisch. Teil-Schritte bleiben nur fuer gezielte Wiederholungen oder Diagnose:

- `./scripts/abrain setup deps`
- `./scripts/abrain setup cli`
- `./scripts/abrain setup api`
- `./scripts/abrain setup mcp`
- `./scripts/abrain setup ui`

## Nicht-Ziele

- keine Wiederbelebung von `scripts/lib` oder `scripts/helpers`
- keine historische ABrain-Setup-Logik
- keine zweite Runtime
- keine verdeckte Docker-Orchestrierung
- keine alternative CLI neben `scripts/abrain`
