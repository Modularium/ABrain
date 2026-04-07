# Benutzerhandbuch: Smolitux-UI für Agent-NN

> Hinweis: Historische UI-Dokumentation. Für den aktuellen Frontend-Referenzpfad ist `frontend/agent-ui` maßgeblich; diese Seite bleibt als Alt-Dokumentation erhalten.

Dieses Benutzerhandbuch erklärt die Verwendung der Smolitux-UI für das Agent-NN-System.

## Einführung

Die Smolitux-UI ist eine moderne Benutzeroberfläche für das Agent-NN-System, die es Ihnen ermöglicht, mit dem Multi-Agenten-System zu interagieren, Aufgaben zu erstellen, Agenten zu verwalten und Ergebnisse zu visualisieren.

## Installation

### Voraussetzungen

- Docker und Docker Compose
- Oder: Node.js 16+ und Python 3.9+

### Installation mit Docker

1. Repository klonen:
   ```bash
   git clone https://github.com/EcoSphereNetwork/Agent-NN.git
   cd Agent-NN
   ```

2. Umgebungsvariablen konfigurieren:
   ```bash
   cp .env.example .env
   # Bearbeiten Sie .env mit Ihren API-Schlüsseln und Konfigurationen
   ```

3. Mit Docker Compose starten:
   ```bash
   docker-compose up -d
   ```

4. Zugriff auf die Anwendung:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API-Dokumentation: http://localhost:8000/docs

### Manuelle Installation

1. Repository klonen:
   ```bash
   git clone https://github.com/EcoSphereNetwork/Agent-NN.git
   cd Agent-NN
   ```

2. Backend-Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

3. Frontend-Abhängigkeiten installieren:
   ```bash
   cd frontend
   npm install
   ```

4. Backend starten:
   ```bash
   cd ..
   uvicorn api.server:app --reload
   ```

5. Frontend starten:
   ```bash
   cd frontend
   npm run dev
   ```

6. Zugriff auf die Anwendung:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API-Dokumentation: http://localhost:8000/docs

## Verwendung

### Startseite

Die Startseite bietet einen Überblick über das System und seine Funktionen:

- **Funktionen**: Beschreibung der Hauptfunktionen des Systems
- **Erste Schritte**: Anleitung zur Verwendung des Systems
- **Schnellzugriff**: Schneller Zugriff auf Chat und Agenten

### Chat

Der Chat ermöglicht die Interaktion mit dem System:

1. Geben Sie Ihre Frage oder Aufgabe in das Eingabefeld ein
2. Klicken Sie auf "Senden" oder drücken Sie Enter
3. Das System wählt automatisch den besten Agenten für Ihre Anfrage
4. Die Antwort wird im Chat angezeigt, zusammen mit Informationen über den verwendeten Agenten

Beispiele für Anfragen:
- "Analysiere die Finanzdaten des letzten Quartals"
- "Erstelle eine Zusammenfassung des Marketingberichts"
- "Finde Informationen über neue Cloud-Technologien"

### Agenten

Die Agenten-Seite zeigt alle verfügbaren Agenten:

- **Liste**: Übersicht aller Agenten mit Domäne und Erfolgsrate
- **Details**: Detailansicht mit Leistungsmetriken und Wissensbasis
- **Suche**: Suche nach Agenten nach Name oder Domäne

Funktionen:
- Klicken Sie auf einen Agenten, um Details anzuzeigen
- Sehen Sie sich die Leistungsmetriken an (Erfolgsrate, Ausführungszeit, etc.)
- Erfahren Sie mehr über die Wissensbasis des Agenten

### Aufgaben

Die Aufgaben-Seite zeigt alle ausgeführten Aufgaben:

- **Liste**: Übersicht aller Aufgaben mit Status und Zeitstempel
- **Details**: Detailansicht mit Ausführungsverlauf und Ergebnis
- **Filter**: Filterung nach Status, Agent oder Zeitraum

Funktionen:
- Klicken Sie auf eine Aufgabe, um Details anzuzeigen
- Sehen Sie sich den Ausführungsverlauf an (Ereignisse, Zeitstempel, etc.)
- Betrachten Sie das Ergebnis der Aufgabe

### Einstellungen

Die Einstellungen-Seite ermöglicht die Konfiguration des Systems:

- **LLM-Einstellungen**: Konfiguration des Language Models (Backend, API-Schlüssel, etc.)
- **Systemeinstellungen**: Konfiguration des Systems (Sprache, Theme, etc.)
- **Logging**: Konfiguration des Loggings und der Metriken

Funktionen:
- Ändern Sie die Sprache der Benutzeroberfläche
- Wechseln Sie zwischen hellem und dunklem Theme
- Konfigurieren Sie das Language Model
- Aktivieren oder deaktivieren Sie Logging und Metriken

## Tipps und Tricks

### Effektive Anfragen

- Seien Sie spezifisch in Ihren Anfragen
- Geben Sie relevante Kontextinformationen an
- Verwenden Sie domänenspezifische Begriffe für bessere Ergebnisse

### Leistungsoptimierung

- Verwenden Sie lokale Modelle für schnellere Antworten
- Aktivieren Sie Caching für häufig gestellte Fragen
- Deaktivieren Sie nicht benötigte Funktionen für bessere Leistung

### Fehlerbehebung

- Überprüfen Sie die Verbindung zum Backend
- Stellen Sie sicher, dass die API-Schlüssel korrekt konfiguriert sind
- Prüfen Sie die Logs auf Fehler

## Häufig gestellte Fragen

### Allgemein

**F: Was ist Agent-NN?**
A: Agent-NN ist ein Multi-Agenten-System, das neuronale Netzwerke verwendet, um Aufgaben optimal zu verteilen und zu lösen.

**F: Wie funktioniert die Agenten-Auswahl?**
A: Das System verwendet neuronale Netzwerke, um den besten Agenten für eine Aufgabe auszuwählen, basierend auf der Aufgabenbeschreibung und der Leistung der Agenten.

### Technisch

**F: Welche LLM-Backends werden unterstützt?**
A: Das System unterstützt OpenAI, LM Studio und lokale Modelle.

**F: Kann ich eigene Agenten erstellen?**
A: Ja, das System kann automatisch neue Agenten erstellen oder Sie können sie manuell konfigurieren.

**F: Wie kann ich die Wissensbasis eines Agenten erweitern?**
A: Sie können Dokumente hochladen oder direkt Wissen hinzufügen, um die Wissensbasis eines Agenten zu erweitern.

## Support

Bei Fragen oder Problemen wenden Sie sich bitte an:

- GitHub Issues: https://github.com/EcoSphereNetwork/Agent-NN/issues
- E-Mail: support@ecosphere.network

## Nächste Schritte

- Erkunden Sie die verschiedenen Agenten und ihre Fähigkeiten
- Testen Sie verschiedene Anfragen im Chat
- Passen Sie die Einstellungen an Ihre Bedürfnisse an
- Geben Sie Feedback zur Verbesserung des Systems
