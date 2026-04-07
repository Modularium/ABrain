# Plugin Agent API

Diese Seite beschreibt einen `legacy (disabled)` Pfad. Sie ist nur noch
`historical / legacy (not active runtime path)` und keine aktive API-Freigabe.

Es gibt dafuer bewusst keine aktuelle OpenAPI-Vertragsdatei mehr, weil der
Runtime-Pfad nicht als nutzbare Schnittstelle veroeffentlicht werden soll.

## `POST /execute_tool`

Dieser Endpunkt ist bewusst deaktiviert und liefert `410 Gone`.
Neue Integrationen muessen den `canonical path` ueber `services/core.py` sowie
`core/tools/*` verwenden.

## `GET /tools`

Gibt nur historische Metadaten zurueck. Er ist kein Hinweis auf eine
freigegebene generische Tool-Ausfuehrung.
