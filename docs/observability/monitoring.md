# Monitoring und Logging

Dieses Dokument beschreibt die grundlegende Observability des ABrain-Systems.

## Logging

Alle Services konfigurieren sich über `LOG_LEVEL` und `LOG_FORMAT`. Bei `LOG_FORMAT=json` wird jeder Request in JSON-Form mit Feldern wie `timestamp`, `service`, `event`, `context_id`, `session_id` und `agent_id` ausgegeben.

## Metriken

Unter `/metrics` stellt jeder Service Prometheus-kompatible Daten bereit. Erfasst werden unter anderem:

- `agentnn_tasks_processed_total` – Anzahl bearbeiteter Aufgaben
- `agentnn_active_sessions` – aktive Sessions
- `agentnn_response_seconds` – Antwortzeiten je Endpoint
- `agentnn_tokens_in_total` und `agentnn_tokens_out_total` – verarbeitete Token

## Grafana

Im Verzeichnis `monitoring/` befindet sich ein Beispiel-Docker-Compose mit Prometheus und Grafana. Die bereitgestellten Dashboards visualisieren Taskvolumen, Tokenverbrauch und Sessionwachstum.
