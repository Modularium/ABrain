# Flowise Nodes for ABrain

Dieses Dokument listet Flowise-Komponenten, die ABrain bereitstellt. Jede Node kann in Flowise importiert werden und kommuniziert über HTTP mit dem jeweiligen Service.

## ListAgents

* **Typ:** Utility
* **Datei:** `integrations/flowise-nodes/ListAgents.ts`
* **Beschreibung:** Gibt alle registrierten Agenten des Registry-Dienstes zurück.
* **Parameter:**
  - `endpoint` (string): Basis-URL des Agent Registry Service.
  - `path` (string): API-Pfad, standardmäßig `/agents`.
  - `headers` (object): optionale HTTP-Header.
  - `timeout` (number): Timeout in Millisekunden.
* **Rückgabe:** JSON-Objekt mit Agenteninformationen oder Fehlermeldung.

Beispielaufruf:

```ts
const node = new ListAgents('http://localhost:8000');
const agents = await node.run();
```

## CreateTask

* **Typ:** Task
* **Datei:** `integrations/flowise-nodes/CreateTask.ts`
* **Beschreibung:** Erstellt einen neuen Task beim Dispatcher.
* **Parameter:**
  - `endpoint` (string): Basis-URL des Dispatchers.
  - `taskType` (string): Typ des Tasks, Standard `chat`.
  - `input` (object): Nutzlast des Tasks.
  - `path` (string): API-Pfad, standardmäßig `/tasks`.
  - `method` (string): HTTP-Methode, standardmäßig `POST`.
  - `headers` (object): optionale HTTP-Header.
  - `timeout` (number): Timeout in Millisekunden.
* **Rückgabe:** JSON-Objekt mit dem API-Ergebnis oder Fehlermeldung.

Beispielaufruf:

```ts
const node = new CreateTask('http://localhost:8000', 'chat', {prompt: 'Hi'});
const result = await node.run();
```


## Node-Vorschau und Deployment

Die generierten `.node.json` Dateien enthalten jetzt zusätzliche Felder für Farbe, Icon und Kategorie. Damit erscheinen die ABrain Nodes in Flowise einheitlich unter der Kategorie **ABrain**.

> TODO: Screenshot "flowise_example.png" ergänzen

Zur Installation in einer lokalen Flowise Instanz kann das Skript `flowise_deploy.py` verwendet werden:

```bash
python flowise_deploy.py
```

Das Skript kopiert die Node-Definitionen nach `~/.flowise/nodes/agent-nn/` und löst optional über `--reload-url` einen Reload der Nodes aus.
