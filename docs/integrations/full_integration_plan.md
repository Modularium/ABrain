# Plan zur vollständigen Integration von ABrain mit n8n und FlowiseAI

Dieser Plan beschreibt die nötigen Schritte, um Agent‑NN in beide Richtungen mit n8n und FlowiseAI zu koppeln. Ziel ist es, Workflows zwischen den Systemen auszutauschen und Agent‑NN sowohl als Quelle als auch als Ziel von Automatisierungsflüssen zu verwenden.

## 1. Überblick

- **Agent‑NN in n8n nutzen:** Bereitstellung eines eigenen n8n Nodes, der Aufgaben an den Agent‑NN Dispatcher sendet und Antworten verarbeitet.
- **Agent‑NN in FlowiseAI nutzen:** Entwicklung einer Flowise-Komponente, die Agent‑NN als externen Chat-Endpunkt anspricht.
- **n8n und FlowiseAI aus Agent‑NN heraus aufrufen:** Erweiterung der bestehenden Plugins, um Authentifizierung und Fehlerbehandlung zu unterstützen.

## 2. n8n Node für Agent‑NN

1. Neues Paket unter `integrations/n8n-agentnn` mit TypeScript-Quellcode anlegen (bereits im Repository enthalten).
2. Implementation eines `AgentNN` Nodes, der folgende Parameter besitzt:
   - `endpoint`: Basis-URL des API-Gateways
   - `task_type`: Art der Aufgabe (z. B. `chat`)
   - `payload`: Freies JSON-Feld für Eingabedaten
   - `method`: HTTP-Methode (Standard `POST`)
   - `headers`: optionale HTTP-Header für Authentifizierung
   - `timeout`: Zeitlimit in Millisekunden
3. Der Node ruft `/task` über die angegebene Methode auf und gibt die JSON-Antwort zurück.
4. Führe `npm install` und anschließend `npx tsc` aus, um die JavaScript-Dateien in `dist/` zu erzeugen.
5. Veröffentlichung als benutzerdefiniertes n8n-Paket (Installationsanleitung in der Doku).

## 3. FlowiseAI Komponente

1. Neues Modul `integrations/flowise-agentnn` mit einem Custom Component Script (`AgentNN.ts`) (bereits im Repository enthalten).
2. Das Script erlaubt die Konfiguration der Agent‑NN URL sowie `taskType`, `method`, Header und Timeout.
3. Eingehende Prompts werden an Agent‑NN weitergeleitet; die Antwort des Dispatchers wird als Chatbot-Antwort ausgegeben.
4. Nach `npm install` und `npx tsc` liegt die kompilierte Datei unter `dist/AgentNN.js`.
5. Bereitstellung über das Flowise Plugin System.

## 4. Verbesserte Plugins in Agent‑NN

- Erweiterung der Plugins `n8n_workflow` und `flowise_workflow` um optionale Auth‑Header, frei wählbare HTTP-Methoden sowie konfigurierbare Timeouts.
- Dokumentation aller Felder in den Plugin-Manifests.
- Beispielskript `run_plugin_task.py` aktualisieren, um beide Plugins komfortabel testen zu können.

## 5. Dokumentation

- Ausführliche Installations‑ und Nutzungshinweise in `docs/integrations/n8n.md` und `docs/integrations/flowise.md` ergänzen.
- Neue Seite `full_integration_plan.md` in `mkdocs.yml` verlinken.
- Schritt-für-Schritt-Anleitung zur Einrichtung der Custom Nodes/Components.

## 6. Tests und CI

- Unit Tests für die Plugin-Erweiterungen schreiben (z. B. Fehlerfälle und Header-Weitergabe).
- End-to-End-Test, der einen simplen n8n bzw. Flowise Mock aufruft.
- Sicherstellen, dass `tests/ci_check.sh` alle neuen Module erfasst.

Durch Umsetzung dieses Plans wird Agent‑NN sowohl von n8n als auch von FlowiseAI aus ansprechbar sein und umgekehrt externe Workflows nutzen können.
