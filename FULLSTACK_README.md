# ABrain Full Stack Setup

Dieses Dokument beschreibt, wie Sie das ABrain-Frontend mit dem Backend verbinden und das gesamte System lokal ausführen.

> Status: Operativer Full-Stack-Helfer. Für den gehärteten Core- und AdminBot-Referenzpfad bleiben `README.md` und `docs/setup/DEVELOPMENT_SETUP.md` maßgeblich.

## System-Übersicht

Das ABrain-System besteht aus:

- **Frontend**: React/TypeScript Anwendung mit modernem UI (Port 3000)
- **Backend**: FastAPI Server als Bridge zwischen Frontend und ABrain-Core (Port 8000)
- **ABrain Core**: Das Hauptsystem mit Agenten, Task-Management und KI-Funktionalitäten

## Voraussetzungen

### Backend
- Python 3.8+
- Virtual Environment (`.venv` im Projektroot)
- Alle Requirements aus `requirements.txt`

### Frontend
- Node.js 18+
- npm oder yarn
- Moderne Webbrowser

## Schnellstart

### 1. Automatischer Start (Empfohlen)

```bash
# System testen
bash test_system.sh

# Vollständiges System starten
bash start_fullstack.sh
```

Das Startskript führt automatisch folgende Schritte aus:
- Überprüft und installiert fehlende Abhängigkeiten
- Startet den Backend-Server auf Port 8000
- Startet den Frontend-Entwicklungsserver auf Port 3000
- Überwacht beide Services und ermöglicht gleichzeitiges Stoppen

### 2. Manueller Start

#### Backend starten:
```bash
# In das Projektverzeichnis wechseln
cd /home/dev/Agent-NN

# Virtual Environment aktivieren
source .venv/bin/activate

# Backend-Server starten
python server/main.py
```

#### Frontend starten:
```bash
# In das Frontend-Verzeichnis wechseln
cd /home/dev/Agent-NN/frontend/agent-ui

# Abhängigkeiten installieren (nur beim ersten Mal)
npm install

# Development Server starten
npm run dev
```

## Zugangsdaten

Für die Demo-Anwendung verwenden Sie:
- **Email**: demo@abrain.local
- **Passwort**: demo

## Verfügbare Endpunkte

### API Endpunkte (Backend - Port 8000)
- `GET /health` - System-Gesundheitscheck
- `POST /auth/login` - Benutzer-Anmeldung
- `GET /user/me` - Aktueller Benutzer
- `GET /agents` - Liste der verfügbaren Agenten
- `POST /agents` - Neuen Agenten erstellen
- `GET /tasks` - Liste der Aufgaben
- `POST /tasks` - Neue Aufgabe erstellen
- `GET /metrics/system` - System-Metriken
- `GET /docs` - API-Dokumentation (Swagger)

### Frontend (Port 3000)
- Dashboard mit System-Übersicht
- Agenten-Management
- Task-Management
- Chat-Interface
- System-Monitoring
- Einstellungen

## Architektur-Details

### Backend-Bridge (server/main.py)
Der Backend-Server fungiert als Bridge zwischen dem React-Frontend und dem ABrain-Core-System:

- **Authentifizierung**: Einfache token-basierte Authentifizierung
- **API-Transformation**: Konvertiert Frontend-Anfragen in ABrain-Core-Aufrufe
- **Mock-Modus**: Läuft auch ohne vollständig konfiguriertes ABrain-System
- **Error-Handling**: Robuste Fehlerbehandlung und Logging

### Frontend-Konfiguration
- **Vite**: Schneller Build-Tool und Dev-Server
- **React Query**: Für API-State-Management
- **Zustand**: Für globales State-Management
- **Tailwind CSS**: Für Styling
- **TypeScript**: Für Type-Safety

### API-Proxy
Das Frontend ist bereits konfiguriert, um API-Aufrufe an das Backend zu proxyen:
- Development: `http://localhost:8000`
- Proxy-Konfiguration in `vite.config.ts`

## Entwicklung

### Frontend Development
```bash
cd frontend/agent-ui

# Dependencies installieren
npm install

# Development server starten
npm run dev

# Build für Produktion
npm run build

# Linting
npm run lint
```

### Backend Development
```bash
# Virtual environment aktivieren
source .venv/bin/activate

# Development server mit Auto-reload
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

## Fehlerbehebung

### Port-Konflikte
Falls die Ports 3000 oder 8000 bereits belegt sind:
```bash
# Prozesse auf Port finden und beenden
netstat -tulnp | grep :8000
kill -9 <PID>
```

### Frontend Build-Probleme
```bash
# Node modules löschen und neu installieren
cd frontend/agent-ui
rm -rf node_modules package-lock.json
npm install
```

### Backend-Probleme
```bash
# Virtual environment neu erstellen
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Logs anzeigen
```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log
```

## Systemtest

Das System kann vollständig getestet werden:
```bash
bash test_system.sh
```

Dieser Test überprüft:
- Backend-Server Funktionalität
- Frontend-Build Process
- API-Endpunkt Konnektivität
- Authentifizierung
- Alle wichtigen Funktionen

## Nächste Schritte

1. **System testen**: `bash test_system.sh`
2. **System starten**: `bash start_fullstack.sh`
3. **Browser öffnen**: http://localhost:3000
4. **Anmelden** mit den Demo-Zugangsdaten
5. **System erkunden**: Dashboard, Agenten, Tasks, Chat

## Produktions-Deployment

Für die Produktion:
1. Frontend bauen: `npm run build`
2. Backend mit Production-Settings: Umgebungsvariablen setzen
3. Reverse Proxy (nginx) konfigurieren
4. SSL-Zertifikate einrichten
5. Database-Backend für persistente Daten

## Unterstützung

Bei Problemen:
1. Logs überprüfen (`backend.log`, `frontend.log`)
2. Systemtest ausführen (`bash test_system.sh`)
3. Network-Konnektivität zwischen Frontend und Backend prüfen
4. Browser-Entwicklertools für Frontend-Probleme verwenden
