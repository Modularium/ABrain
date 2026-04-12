# Setup One-Liner Inventory

Datum: 2026-04-12
Branch: `codex/setup-one-liner-bootstrap`

## Gepruefte Dateien

- `scripts/setup.sh`
- `scripts/abrain`
- `scripts/agentnn`
- `scripts/abrain_mcp.py`
- `README.md`
- `CONTRIBUTING.md`
- `scripts/README.md`
- `docs/mcp/*`
- `docs/architecture/*`
- `pyproject.toml`
- `requirements-light.txt`
- `frontend/agent-ui/package.json`
- `api_gateway/main.py`
- `interfaces/mcp/server.py`

## Was ein vollstaendiges Setup heute real leisten muss

Ein kompletter Bootstrap fuer den aktuellen ABrain-Stand muss:

1. `.venv` erzeugen oder wiederverwenden
2. Python-Bootstrap-Tools aktualisieren
3. Python-Dependencies fuer den aktiven Runtime-Kern installieren
4. die editable Installation fuer `abrain-mcp` erzeugen oder erneuern
5. den API-Gateway-Import gegen den aktuellen Dependency-Stand pruefen
6. den MCP-v2-Server ueber `initialize` und `tools/list` smoke-testen
7. das Frontend unter `frontend/agent-ui` installieren, typpruefen und bauen
8. am Ende klar melden, dass CLI, MCP, API und UI bereit sind

## Aktueller technischer Stand vor dieser Abschlussrunde

Der vorherige Modernisierungsschritt hatte die groessten Legacy-Brueche bereits entfernt:

- `scripts/setup.sh` war eigenstaendig
- `scripts/abrain setup ...` delegierte direkt an `scripts/setup.sh`
- `requirements-light.txt` war bereits auf den kanonischen Kern reduziert
- `pyproject.toml` und `core/config.py` waren fuer frische editable- und API-Smokes repariert

## Noch offene One-Liner-Bruecken

### A. Benutzerfuehrung war noch nicht konsequent auf einen Befehl reduziert

- README, CONTRIBUTING und mehrere Architekturdokumente empfahlen weiter `./scripts/abrain setup all`
- technisch funktionierte `./scripts/abrain setup` bereits als Voll-Setup, aber die Doku kommunizierte das nicht als kanonischen Weg

### B. Erfolgsausgabe war eher generisch als zielorientiert

- der Bootstrap endete mit Startpfaden, aber nicht mit einer klaren Ready-State-Ausgabe fuer CLI, MCP, API und UI

### C. CLI-Bereitschaft war implizit, nicht explizit geprueft

- der Setup-Flow pruefte API, MCP und UI, aber nicht explizit die kanonische Bash-CLI selbst

### D. MCP-Entry-Point sollte bei der Verifikation ausdruecklich als v2 verifiziert werden

- `abrain-mcp` wurde bereits erzeugt, aber der Flow sollte fuer den One-Liner explizit bestaetigen, dass der Console-Entry auf `interfaces.mcp.server:main` zeigt

## Kanonische Einstiege heute

- bevorzugt: `./scripts/abrain setup`
- direkt, aber sekundär: `bash scripts/setup.sh`
- MCP v2: `.venv/bin/python -m interfaces.mcp.server`
- MCP Console-Entry nach Setup: `.venv/bin/abrain-mcp`
- API Gateway: `.venv/bin/python -m uvicorn api_gateway.main:app --reload`
- UI Dev: `cd frontend/agent-ui && npm run dev`
