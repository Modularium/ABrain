# Security Hardening

Dieses Dokument beschreibt empfohlene Sicherheitsmaßnahmen für die ABrain-Services.

## Token-Authentifizierung

Aktiviere die Middleware mit `AUTH_ENABLED=true`. Gültige Tokens werden über `API_TOKENS` als kommagetrennte Liste gesetzt. Bei Austausch der Tokens müssen die Services neu gestartet werden.

## Rate-Limiting

Über `slowapi` lassen sich Aufrufe begrenzen. Der Parameter `RATE_LIMIT_TASK` definiert z.B. das Limit für den Dispatcher (Standard `10/minute`). Limiter sind nur aktiv, wenn `RATE_LIMITS_ENABLED=true` gesetzt ist.

## Input-Validierung

Alle Anfragen werden validiert. Text in `task_context.input_data.text` darf maximal 4096 Zeichen enthalten. Fehlerhafte Payloads führen zu einem `422` Response.

## Deployment-Tipps

- Reverse Proxy mit TLS verwenden
- API-Tokens nie im Repository ablegen, sondern per `.env` oder Orchestrierung setzen
- Docker-Images härten und falls möglich mit nicht privilegierten Nutzern ausführen
