# CORE_REFACTOR

Diese Beschreibung bezieht sich auf den gehärteten ABrain-Core. Historische Dateisystem- und Paketpfade können weiterhin `Agent-NN` oder `agentnn` enthalten.

## Neue Struktur

Die Stabilisierung fuehrt eine kleine, feste Kernschicht ein:

- `core/agents`
  Enthält Runtime-Wrapper, die Legacy-Agenten hinter stabilen Sync/Async-Grenzen kapseln.
- `core/tools`
  Enthält eine feste Tool-Registry ohne dynamisches Laden sowie die zugeordneten Handler.
- `core/execution`
  Enthält den Dispatcher, der Toolnamen und Payload validiert, ausfuehrt und strukturierte Fehler erzeugt.
- `core/models`
  Enthält Pydantic-Modelle fuer Tool-Inputs, Execution-Requests, Identitaeten und Fehler.

Die vorhandenen Legacy-Module bleiben bestehen, werden aber nicht mehr als rohe Einstiegspunkte fuer kuenftige Adapter betrachtet.

## Tool-System

Das Tool-System ist absichtlich minimal gehalten:

- Feste Tool-Definitionen, keine Plugin- oder Reflection-Lader.
- Pro Tool ein getyptes Input-Modell.
- `requested_by` ist verpflichtend und enthaelt:
  - `type`: `agent` oder `human`
  - `id`: technische Identitaet des Aufrufers
- Optionale Korrelationsdaten:
  - `run_id`
  - `correlation_id`

Aktuell sind die festen internen Tools:

- `dispatch_task`
- `list_agents`

Diese Tools kapseln bestehende interne HTTP-/SDK-Aufrufe, ohne Raw-Execution von beliebigen Funktionen freizugeben.

`dispatch_task` ist dabei nicht mehr offen generisch. Er akzeptiert nur feste interne `task_type`-Werte:

- `chat`
- `dev`
- `docker`
- `container_ops`
- `semantic`
- `qa`
- `search`

`generic` wird ueber die gehärtete Tool-Schicht nicht mehr akzeptiert.

## Execution Flow

Der neue Ablauf ist:

1. Ein Aufrufer erzeugt einen `ToolExecutionRequest`.
2. Der `ExecutionDispatcher` sucht das Tool in der `ToolRegistry`.
3. Das Payload wird gegen das deklarierte Pydantic-Modell validiert.
   Dazu gehoert auch die Pflicht-Identity `requested_by` mit gueltigem `type` und gesetzter `id`.
4. Der Handler wird kontrolliert ausgefuehrt.
5. Sync- und Async-Handler werden ueber dieselbe Boundary vereinheitlicht.
6. Fehler werden als `StructuredError` mit `error_code`, `message` und optionalen `details` zurueckgegeben bzw. hochgereicht.

## Stabilisierungseffekt

Die Refaktorierung fuehrt keine neue Fachlogik ein. Sie reduziert vor allem:

- unsichere direkte Funktionsaufrufe
- inkonsistente Sync/Async-Grenzen
- fehlende Request-Identitaet
- unstrukturierte Fehler fuer kuenftige Adapter

Damit ist eine kontrollierte Adapter-Anbindung moeglich, ohne dass externe Systeme direkt an volatile Legacy-Module gekoppelt werden.
