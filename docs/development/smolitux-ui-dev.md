# Entwicklerdokumentation: Smolitux-UI für ABrain

Diese Dokumentation richtet sich an Entwickler, die an der Smolitux-UI-Integration für das ABrain-System arbeiten möchten.

## Architektur

Die Smolitux-UI-Integration besteht aus folgenden Komponenten:

1. **Frontend**: Eine React-Anwendung mit TypeScript und Smolitux-UI-Komponenten
2. **Backend-API**: Eine FastAPI-basierte REST-API für die Kommunikation
3. **WebSocket-Verbindung**: Für Echtzeit-Updates und Chat-Funktionalität

### Frontend-Architektur

```
frontend/
├── public/              # Statische Dateien
├── src/
│   ├── components/      # Wiederverwendbare Komponenten
│   │   ├── AgentCard.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── Navbar.tsx
│   │   ├── SettingsForm.tsx
│   │   ├── Sidebar.tsx
│   │   └── TaskItem.tsx
│   ├── layouts/         # Layout-Komponenten
│   │   └── MainLayout.tsx
│   ├── pages/           # Seiten-Komponenten
│   │   ├── AgentsPage.tsx
│   │   ├── ChatPage.tsx
│   │   ├── HomePage.tsx
│   │   ├── SettingsPage.tsx
│   │   └── TasksPage.tsx
│   ├── styles/          # CSS-Stile
│   │   └── index.css
│   ├── translations/    # Übersetzungsdateien
│   │   ├── de.json
│   │   └── en.json
│   ├── types/           # TypeScript-Typdefinitionen
│   │   └── index.ts
│   ├── utils/           # Hilfsfunktionen
│   │   ├── api.ts
│   │   ├── i18n.ts
│   │   └── theme.ts
│   ├── App.tsx          # Hauptanwendungskomponente
│   └── main.tsx         # Einstiegspunkt
├── index.html           # HTML-Vorlage
├── package.json         # Abhängigkeiten und Skripte
├── tsconfig.json        # TypeScript-Konfiguration
└── vite.config.ts       # Vite-Konfiguration
```

### Backend-Integration

Die Backend-Integration erfolgt über die folgenden Komponenten:

1. **API-Endpunkte**: REST-API-Endpunkte in `api/endpoints.py`
2. **WebSocket-Endpunkte**: WebSocket-Endpunkte in `api/endpoints.py`
3. **Smolitux-Konfiguration**: Konfigurationsoptionen in `config/smolitux_config.py`

## Entwicklungsumgebung einrichten

### Voraussetzungen

- Node.js 16+
- Python 3.9+
- Git

### Frontend-Entwicklung

1. Repository klonen:
   ```bash
   git clone https://github.com/EcoSphereNetwork/Agent-NN.git
   cd Agent-NN
   ```

2. Frontend-Abhängigkeiten installieren:
   ```bash
   cd frontend
   npm install
   ```

3. Entwicklungsserver starten:
   ```bash
   npm run dev
   ```

4. Zugriff auf die Anwendung:
   - Frontend: http://localhost:3000

### Backend-Entwicklung

1. Python-Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

2. Entwicklungsserver starten:
   ```bash
   uvicorn api.server:app --reload
   ```

3. Zugriff auf die API:
   - API: http://localhost:8000
   - API-Dokumentation: http://localhost:8000/docs

## Komponenten

### Frontend-Komponenten

#### Seiten

- **HomePage**: Startseite mit Übersicht und Schnellzugriff
- **ChatPage**: Chat-Interface für Benutzerinteraktionen
- **AgentsPage**: Übersicht und Verwaltung der Agenten
- **TasksPage**: Übersicht und Details der Aufgaben
- **SettingsPage**: Konfiguration des Systems

#### Wiederverwendbare Komponenten

- **ChatMessage**: Darstellung von Chat-Nachrichten
- **AgentCard**: Darstellung von Agenten-Informationen
- **TaskItem**: Darstellung von Aufgaben-Informationen
- **SettingsForm**: Formular für Systemeinstellungen
- **Navbar**: Navigationsleiste
- **Sidebar**: Seitenleiste für Navigation

#### Utilities

- **api.ts**: API-Client für Backend-Kommunikation
- **i18n.ts**: Internationalisierung und Übersetzungen
- **theme.ts**: Theme-Verwaltung (hell/dunkel)

### Backend-Komponenten

#### API-Endpunkte

- `POST /smolitux/tasks`: Erstellt und führt eine Aufgabe aus
- `GET /smolitux/tasks`: Gibt eine Liste aller Aufgaben zurück
- `GET /smolitux/tasks/{task_id}`: Gibt Details zu einer bestimmten Aufgabe zurück
- `GET /smolitux/agents`: Gibt eine Liste aller Agenten zurück
- `WebSocket /smolitux/ws`: WebSocket-Verbindung für Echtzeit-Updates und Chat

#### Konfiguration

- `config/smolitux_config.py`: Konfigurationsoptionen für die Smolitux-UI-Integration

## Erweiterung und Anpassung

### Neue Komponenten hinzufügen

1. Erstellen Sie eine neue Komponente in `frontend/src/components/`:
   ```tsx
   import React from 'react';
   import { useTranslation } from '../utils/i18n';

   interface MyComponentProps {
     // Props definieren
   }

   const MyComponent: React.FC<MyComponentProps> = (props) => {
     const t = useTranslation();
     
     return (
       <div className="my-component">
         {/* Komponente implementieren */}
       </div>
     );
   };

   export default MyComponent;
   ```

2. Importieren und verwenden Sie die Komponente in einer Seite:
   ```tsx
   import MyComponent from '../components/MyComponent';

   const MyPage: React.FC = () => {
     return (
       <div className="my-page">
         <h1>My Page</h1>
         <MyComponent />
       </div>
     );
   };
   ```

### Neue API-Endpunkte hinzufügen

1. Fügen Sie einen neuen Endpunkt in `api/endpoints.py` hinzu:
   ```python
   @self.router.post("/smolitux/my-endpoint")
   async def my_endpoint(request: MyRequestModel):
       """My endpoint description."""
       try:
           # Implementieren Sie den Endpunkt
           result = await self.my_service.do_something(request)
           return result
       except Exception as e:
           self.log_error(e, {"request": request.dict()})
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail=f"Error: {str(e)}"
           )
   ```

2. Definieren Sie ein Datenmodell in `api/models.py`:
   ```python
   class MyRequestModel(BaseModel):
       """My request model."""
       field1: str
       field2: int
       optional_field: Optional[str] = None
   ```

3. Verwenden Sie den Endpunkt im Frontend:
   ```typescript
   async function callMyEndpoint(data: MyRequestData): Promise<any> {
     const response = await fetch(`${API_BASE_URL}/smolitux/my-endpoint`, {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json'
       },
       body: JSON.stringify(data)
     });
     
     if (!response.ok) {
       throw new Error(`HTTP error ${response.status}`);
     }
     
     return response.json();
   }
   ```

### Übersetzungen hinzufügen

1. Fügen Sie neue Übersetzungen in `frontend/src/translations/de.json` und `frontend/src/translations/en.json` hinzu:
   ```json
   {
     "myComponent": {
       "title": "Mein Titel",
       "description": "Meine Beschreibung"
     }
   }
   ```

2. Verwenden Sie die Übersetzungen in Ihren Komponenten:
   ```tsx
   const MyComponent: React.FC = () => {
     const t = useTranslation();
     
     return (
       <div>
         <h1>{t('myComponent.title')}</h1>
         <p>{t('myComponent.description')}</p>
       </div>
     );
   };
   ```

## Best Practices

### Code-Stil

- Verwenden Sie TypeScript für typsichere Komponenten
- Folgen Sie dem Functional Component Pattern mit Hooks
- Verwenden Sie aussagekräftige Namen für Komponenten und Funktionen
- Dokumentieren Sie komplexe Logik mit Kommentaren

### Komponenten-Design

- Erstellen Sie wiederverwendbare Komponenten
- Verwenden Sie Props für Konfiguration und Daten
- Trennen Sie Logik und Darstellung
- Verwenden Sie CSS-Klassen für Styling

### API-Integration

- Verwenden Sie den API-Client für alle Backend-Kommunikation
- Behandeln Sie Fehler und Ladezustände
- Implementieren Sie Caching für häufige Anfragen
- Verwenden Sie TypeScript-Typen für API-Antworten

### Internationalisierung

- Verwenden Sie den Übersetzungs-Hook für alle Texte
- Vermeiden Sie hartcodierte Strings
- Verwenden Sie Parameter für dynamische Texte
- Testen Sie die Anwendung in verschiedenen Sprachen

## Fehlerbehebung

### Häufige Probleme

1. **Komponenten werden nicht gerendert**:
   - Überprüfen Sie die Imports
   - Stellen Sie sicher, dass die Komponente exportiert wird
   - Überprüfen Sie die Props

2. **API-Anfragen schlagen fehl**:
   - Überprüfen Sie die API-URL
   - Stellen Sie sicher, dass der Server läuft
   - Überprüfen Sie die Anfragedaten
   - Prüfen Sie die Netzwerkanfragen im Browser

3. **Übersetzungen funktionieren nicht**:
   - Überprüfen Sie den Übersetzungsschlüssel
   - Stellen Sie sicher, dass die Übersetzung existiert
   - Überprüfen Sie die Spracheinstellung

### Debugging

- Verwenden Sie `console.log` für einfaches Debugging
- Nutzen Sie die React Developer Tools für Komponenten-Debugging
- Verwenden Sie die Netzwerk-Tools für API-Debugging
- Aktivieren Sie das Logging im Backend für Server-Debugging

## Testen

### Frontend-Tests

1. Unit-Tests mit Jest:
   ```bash
   cd frontend
   npm test
   ```

2. Komponenten-Tests mit React Testing Library:
   ```tsx
   import { render, screen } from '@testing-library/react';
   import MyComponent from './MyComponent';

   test('renders component', () => {
     render(<MyComponent />);
     expect(screen.getByText('My Component')).toBeInTheDocument();
   });
   ```

### Backend-Tests

1. API-Tests mit pytest:
   ```bash
   pytest tests/test_smolitux_api.py
   ```

2. Endpunkt-Tests:
   ```python
   async def test_smolitux_tasks_endpoint():
       response = await client.post(
           "/smolitux/tasks",
           json={"description": "Test task"}
       )
       assert response.status_code == 200
       assert "task_id" in response.json()
   ```

## Deployment

### Docker-Deployment

1. Frontend bauen:
   ```bash
   cd frontend
   npm run build
   ```

2. Docker-Image bauen:
   ```bash
   docker-compose build
   ```

3. Docker-Container starten:
   ```bash
   docker-compose up -d
   ```

### Manuelles Deployment

1. Frontend bauen:
   ```bash
   cd frontend
   npm run build
   ```

2. Frontend-Dateien auf Webserver kopieren:
   ```bash
   cp -r dist/* /var/www/html/
   ```

3. Backend starten:
   ```bash
   uvicorn api.server:app --host 0.0.0.0 --port 8000
   ```

## Ressourcen

- [React-Dokumentation](https://reactjs.org/docs/getting-started.html)
- [TypeScript-Dokumentation](https://www.typescriptlang.org/docs/)
- [FastAPI-Dokumentation](https://fastapi.tiangolo.com/)
- [Vite-Dokumentation](https://vitejs.dev/guide/)
- [Smolitux-UI-Dokumentation](https://github.com/EcoSphereNetwork/smolitux-ui)
