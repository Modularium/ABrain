# MCP Overview

Hinweis: Diese Uebersicht beschreibt den frueheren `mcp/*`-Stack. Der aktuelle canonical runtime stack ist `services/*`; `mcp/*` bleibt nur `legacy (disabled)`.

The Modular Control Plane architecture breaks ABrain into small services that communicate over defined APIs. This overview outlines the main building blocks.

```mermaid
graph TD
    A[API-Gateway] --> B[Task-Dispatcher]
    A --> U[User Manager]
    B --> C[Agent Registry]
    B --> D[Session Manager]
    B --> E[Worker Services]
    B --> F[Vector Store]
    B --> G[LLM Gateway]
    E --> F
    E --> G
```

The following sequence shows the end-to-end flow after Phase&nbsp;3:

```mermaid
sequenceDiagram
    participant U as User
    participant D as Dispatcher
    participant W as Worker
    participant L as LLM Gateway
    participant V as Vector Store
    U->>D: task request
    D->>W: execute_task
    W->>L: generate/qa
    L->>V: query (optional)
    L-->>W: answer
    W-->>D: result
    D-->>U: response
```

Each service can be scaled independently and replaced without touching the others. The dispatcher coordinates requests and uses the registry to find suitable workers. Session data and knowledge retrieval are handled by dedicated services.

### Historical Directory Layout

```
mcp/
├── task_dispatcher/
├── agent_registry/
├── session_manager/
├── vector_store/
├── llm_gateway/
├── user_manager/
├── worker_dev/
├── worker_loh/
└── worker_openhands/
```

Diese Verzeichnisstruktur ist kein produktiver Startpfad mehr. Der produktive Compose- und Service-Start liegt jetzt in `docker-compose.yml` und `services/*`.
