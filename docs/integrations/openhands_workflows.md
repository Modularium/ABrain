# OpenHands Workflows in FlowiseAI

Diese Anleitung beschreibt die bereitgestellten Flowise-Workflows unter `integrations/flowise-agentnn`. Sie erlauben es, mehrere OpenHands-Agenten parallel anzusteuern. Jede JSON-Datei steht für ein eigenes Szenario.

## Dateien

* `openhands.json` – Standard-Workflow für ein 16-köpfiges Entwicklungsteam.
* `openhands_linux.json` – Variante für Linux-Distributionen (Kernel, Packages usw.).
* `openhands_app.json` – Variante für mobile Apps (Android/iOS).
* `openhands_nn.json` – Team für neuronale Netze (Ports 3031–3040).
* `openhands_mldl.json` – Team für ML- & DL-Algorithmen (Ports 3041–3050).
* `sample_flow.json` – Minimalbeispiel zum Testen der Komponente `AgentNN`.

Alle Workflows besitzen denselben Aufbau und unterscheiden sich hauptsächlich bei den Agentennamen, Ports und Tokens. Die Dateien lassen sich direkt in der Flowise-UI importieren.

## Aufbau der Workflows

1. **Start-Formular**: 
   - Das Start-Node sammelt die Benutzeraufgabe (`task`) und lässt mehrere Agenten auswählen.
2. **Variablen setzen**:
   - Ein `SetVariable`-Node speichert den Text der Aufgabe.
3. **Bedingungsprüfungen**:
   - Für jeden Agenten existiert ein `IfElse`-Node. Er prüft, ob der Agent ausgewählt wurde.
4. **API-Aufruf**:
   - Bei Erfolg verzweigt der Flow zu einem `HttpRequest`-Node. Dort wird mit `POST /api/conversations` eine neue Konversation beim jeweiligen OpenHands-Agent gestartet.
5. **Conversation-ID speichern**:
   - Die Antwort enthält eine `conversation_id`, die per `SetVariable` in der Flow-Variable gesichert wird.
6. **Trajectory abrufen**:
   - Anschließend führt ein weiterer `HttpRequest` ein `GET /api/trajectory` aus. Die URL enthält die gespeicherte ID. So lässt sich der Fortschritt des Agenten abrufen.

### Beispiel für einen Request-Node
```json
{
  "id": "request_0_init",
  "label": "POST /api/conversations (Frontend Engineer)",
  "name": "httpRequest",
  "inputs": {
    "method": "POST",
    "url": "http://localhost:3001/api/conversations",
    "headers": "{\"Authorization\": \"Bearer {{secrets.TOKEN_FRONTEND}}\"}",
    "body": "{\"initial_user_msg\": \"{{ $flow.state.task }}\"}"
  }
}
```
Dieser Knoten sendet die eingegebene Aufgabe an den Frontend-Agenten und speichert anschließend die Antwortdaten.

## Szenarien

### Standard-Team (openhands.json)
Enthält Rollen wie Frontend Engineer, Backend Engineer, QA Tester, Security Analyst und weitere Spezialisten. Die Ports reichen von 3001 bis 3010.

### Linux-Distribution (openhands_linux.json)
Richtet sich an ein Linux-Team mit Rollen wie Kernel Engineer, Package Maintainer oder System Services Developer. Die Ports beginnen bei 3021.

### Mobile Apps (openhands_app.json)
Für mobile Projekte: Android App DevOps, iOS App DevOps usw. Die Ports beginnen bei 3011.

### Neuronale Netze (openhands_nn.json)
Dieses Team entwickelt Modelle für Agent‑NN. Die Ports reichen von 3031 bis 3040.

### ML- & DL-Algorithmen (openhands_mldl.json)
Enthält zehn Spezialisten für neue Lernverfahren. Die Ports reichen von 3041 bis 3050.

## Verwendung
1. Öffne Flowise und wähle **Import Flow**.
2. Lade eine der JSON-Dateien hoch.
3. Prüfe die Ports und API-Tokens in den `HttpRequest`-Nodes. Passe sie bei Bedarf an.
4. Starte den Flow und gib eine Aufgabe sowie die gewünschten Agenten an.

## Minimaler Beispiel-Flow
`sample_flow.json` demonstriert lediglich den Aufruf der Komponente `AgentNN`:
```json
{
  "nodes": [
    {"id": "start", "type": "input"},
    {"id": "agentnn", "type": "AgentNN", "properties": {"endpoint": "http://localhost:8000"}},
    {"id": "output", "type": "output"}
  ],
  "edges": [
    {"source": "start", "target": "agentnn"},
    {"source": "agentnn", "target": "output"}
  ]
}
```
Damit kann geprüft werden, ob die Verbindung zu ABrain funktioniert.

## Tipps
- Die Workflows sind als Vorlage gedacht. Du kannst weitere Agenten hinzufügen oder überflüssige entfernen.
- Beachte, dass `npm install` und `npx tsc` im Ordner `integrations/flowise-agentnn` ausgeführt wurden, bevor die Komponente genutzt wird.
- Für Offline-Umgebungen lassen sich die Endpunkte leicht an interne Hostnamen anpassen.
