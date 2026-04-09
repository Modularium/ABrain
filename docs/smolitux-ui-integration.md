# Smolitux-UI Integration für ABrain

Hinweis: Die hier beschriebene Smolitux-Bridge ist `legacy (disabled)` und nicht Teil des canonical runtime stack.

Diese Dokumentation beschreibt die Integration der Smolitux-UI-Bibliothek mit dem ABrain-System.

## Überblick

Die Smolitux-UI-Integration bietet eine moderne, reaktionsfähige Benutzeroberfläche für das ABrain-System. Sie ermöglicht Benutzern, mit dem Multi-Agenten-System zu interagieren, Aufgaben zu erstellen, Agenten zu verwalten und Ergebnisse zu visualisieren.

## Architektur

Die Integration besteht aus folgenden Komponenten:

1. **Frontend**: Eine React-Anwendung mit Smolitux-UI-Komponenten
2. **Backend-API**: Eine REST-API für die Kommunikation zwischen Frontend und Backend
3. **WebSocket-Verbindung**: Für Echtzeit-Updates und Chat-Funktionalität

### Frontend-Architektur

```
frontend/
├── public/              # Statische Dateien
├── src/
│   ├── components/      # Wiederverwendbare Komponenten
│   ├── layouts/         # Layout-Komponenten
│   ├── pages/           # Seiten-Komponenten
│   ├── styles/          # CSS-Stile
│   ├── translations/    # Übersetzungsdateien
│   ├── types/           # TypeScript-Typdefinitionen
│   ├── utils/           # Hilfsfunktionen
│   ├── App.tsx          # Hauptanwendungskomponente
│   └── main.tsx         # Einstiegspunkt
├── index.html           # HTML-Vorlage
└── vite.config.ts       # Vite-Konfiguration
```

### Backend-Integration

Die Backend-Integration erfolgt über die folgenden Komponenten:

1. **API-Endpunkte**: REST-API-Endpunkte für Frontend-Kommunikation
2. **WebSocket-Endpunkte**: Für Echtzeit-Updates und Chat
3. **Smolitux-Konfiguration**: Konfigurationsoptionen für die UI-Integration

## Funktionen

### Chat-Interface

Das Chat-Interface ermöglicht Benutzern, mit dem ABrain-System zu interagieren:

- Eingabe von Fragen und Aufgaben
- Anzeige von Antworten und Ergebnissen
- Informationen über den verwendeten Agenten
- Ausführungszeit und andere Metriken

### Agenten-Verwaltung

Die Agenten-Verwaltung bietet einen Überblick über alle verfügbaren Agenten:

- Liste aller Agenten mit Domäne und Erfolgsrate
- Detailansicht mit Leistungsmetriken
- Informationen über die Wissensbasis

### Aufgaben-Übersicht

Die Aufgaben-Übersicht zeigt alle ausgeführten Aufgaben:

- Liste aller Aufgaben mit Status und Zeitstempel
- Detailansicht mit Ausführungsverlauf
- Ergebnisanzeige und Metriken

### Einstellungen

Die Einstellungen ermöglichen die Konfiguration des Systems:

- LLM-Einstellungen (Backend, API-Schlüssel, etc.)
- Systemeinstellungen (Sprache, Theme, etc.)
- Logging und Metriken

## API-Endpunkte

Die folgenden API-Endpunkte werden für die Smolitux-UI-Integration bereitgestellt:

### REST-API

- `POST /smolitux/tasks`: Erstellt und führt eine Aufgabe aus
- `GET /smolitux/tasks`: Gibt eine Liste aller Aufgaben zurück
- `GET /smolitux/tasks/{task_id}`: Gibt Details zu einer bestimmten Aufgabe zurück
- `GET /smolitux/agents`: Gibt eine Liste aller Agenten zurück

### WebSocket-API

- `WebSocket /smolitux/ws`: WebSocket-Verbindung für Echtzeit-Updates und Chat

## Konfiguration

Die Smolitux-UI-Integration kann über die folgenden Konfigurationsoptionen angepasst werden:

### Umgebungsvariablen

```
# Frontend-Konfiguration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Smolitux-Konfiguration
SMOLITUX_DEFAULT_LANGUAGE=de
SMOLITUX_DEFAULT_THEME=light
SMOLITUX_ENABLE_LOGGING=true
```

### Konfigurationsdatei

Die Datei `config/smolitux_config.py` enthält alle Konfigurationsoptionen für die Smolitux-UI-Integration:

```python
class SmolituxConfig(BaseModel):
    # API-Konfiguration
    api_prefix: str = "/smolitux"
    api_version: str = "v1"
    
    # UI-Konfiguration
    default_language: str = "de"
    available_languages: list = ["de", "en"]
    
    # Theme-Konfiguration
    default_theme: str = "light"
    available_themes: list = ["light", "dark"]
    
    # ...
```

## Deployment

Die Smolitux-UI-Integration kann mit Docker und Docker Compose bereitgestellt werden:

```bash
# Starten der Anwendung
docker-compose up -d

# Stoppen der Anwendung
docker-compose down
```

## Entwicklung

### Voraussetzungen

- Node.js 16+
- Python 3.9+
- Docker und Docker Compose (optional)

### Frontend-Entwicklung

```bash
# Installation der Abhängigkeiten
cd frontend
npm install

# Starten des Entwicklungsservers
npm run dev
```

### Backend-Entwicklung

```bash
# Installation der Abhängigkeiten
pip install -r requirements.txt

# Starten des Entwicklungsservers
uvicorn api.server:app --reload
```

## Fehlerbehebung

### Häufige Probleme

1. **WebSocket-Verbindungsfehler**:
   - Überprüfen Sie, ob der WebSocket-Server läuft
   - Überprüfen Sie die WebSocket-URL in der Frontend-Konfiguration

2. **API-Verbindungsfehler**:
   - Überprüfen Sie, ob der API-Server läuft
   - Überprüfen Sie die API-URL in der Frontend-Konfiguration

3. **Styling-Probleme**:
   - Stellen Sie sicher, dass die Smolitux-UI-Bibliothek korrekt installiert ist
   - Überprüfen Sie die CSS-Imports in der Anwendung

## Nächste Schritte

Die folgenden Erweiterungen sind für zukünftige Versionen geplant:

1. **Erweiterte Visualisierungen**:
   - Grafische Darstellung von Agenten-Leistung
   - Netzwerkvisualisierung für Agenten-Kommunikation

2. **Benutzerverwaltung**:
   - Benutzerauthentifizierung und -autorisierung
   - Benutzerspezifische Einstellungen

3. **Erweiterte Agenten-Verwaltung**:
   - Erstellung und Bearbeitung von Agenten über die UI
   - Hochladen von Dokumenten für die Wissensbasis

4. **Mobile Optimierung**:
   - Responsive Design für mobile Geräte
   - Progressive Web App (PWA) Funktionalität
