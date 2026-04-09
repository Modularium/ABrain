# AdminBot Adapter Review Summary

Diese Review-Summary beschreibt den aktuellen, auf AdminBot v2 ausgerichteten Adapterstand.

## Ziel

Sicherer, dünner AdminBot-Adapter für ABrain über die gehärtete Core-Tool-Schicht, ohne neue Trust Boundary und ohne Erweiterung der Tool-Fläche.

## Umgesetzte Tools

- `adminbot_system_status`
- `adminbot_system_health`
- `adminbot_service_status`

## Bewusst ausgeschlossene Tools

- `adminbot_resource_snapshot`
- `adminbot_journal_query`
- `adminbot_process_snapshot`
- `adminbot_service_restart`

## Sicherheitsgarantien

- kein generischer AdminBot-Action-Proxy
- keine freie JSON-Weitergabe vom Tool-Request an AdminBot
- `requested_by` wird gegenüber AdminBot hart auf `agent` mit stabiler Adapter-ID gesetzt
- aus dem Tool-Request werden nur `run_id` und `correlation_id` übernommen
- Socket-Pfad und IPC-Framing folgen dem AdminBot-v2-Vertrag
- AdminBot-Fehler bleiben semantisch erhalten
- Transport- und Protokollfehler werden lokal als Adapterfehler klassifiziert

## Teststand

- gezielte Adapter-, Dispatcher- und Registry-Tests grün
- gezielte `py_compile`-Prüfung der AdminBot- und Core-Module erfolgreich
