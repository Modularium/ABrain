# Plugin Agent API

Der Plugin-Agent-Pfad ist historisch und fuer sicherheitsrelevante Integrationen
nicht mehr freigegeben.

Es gibt dafuer bewusst keine aktuelle OpenAPI-Vertragsdatei mehr, weil der
Runtime-Pfad nicht als nutzbare Schnittstelle veroeffentlicht werden soll.

## `POST /execute_tool`

Dieser Endpunkt ist bewusst deaktiviert und liefert `410 Gone`.
Neue Integrationen muessen den festen Core-Pfad ueber
`services/core.py` sowie `core/tools/*` verwenden.

## `GET /tools`

Gibt nur historische Metadaten zurueck. Er ist kein Hinweis auf eine
freigegebene generische Tool-Ausfuehrung.
