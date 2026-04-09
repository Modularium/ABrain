# Session Management

Note: the historical MCP session endpoints below are `legacy (disabled)`. The canonical runtime uses `services/session_manager` directly.

The session pool enables multiple agents to collaborate within the same dialogue.
A session is identified by a unique ID and holds the following data:

- `linked_agents`: list of agent IDs participating in the session
- `message_history`: chronological list of executed tasks and results

New MCP endpoints support this behaviour:

```
POST /v1/mcp/session/create             -> {"session_id": "..."}
POST /v1/mcp/session/{id}/add_agent     -> {"agent_id": "agent"}
POST /v1/mcp/session/{id}/run_task      -> {"task": "message"}
```

The `run_task` route executes the provided task sequentially with all linked
agents. Each result is appended to the session's `message_history` which can be
retrieved via the session manager API.
