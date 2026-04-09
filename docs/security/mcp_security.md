# MCP Server Security

Hinweis: Die historischen MCP-Gateway-Endpunkte sind `legacy (disabled)` und liefern bewusst `410 Gone`. Diese Seite ist nur noch fuer den frueheren Sicherheitsrahmen relevant.

The MCP server can optionally protect its routes with API keys or bearer tokens.
Set the environment variables `MCP_API_KEYS` (comma separated) or
`MCP_BEARER_TOKEN` to enable the check. When no values are provided all requests
are accepted.

Historical example using an API key. The request now returns `410 Gone` because the legacy MCP gateway is disabled:

```bash
export MCP_API_KEYS="secret123"
curl -X POST http://localhost:8089/v1/mcp/task/execute \
     -H "X-API-Key: secret123" \
     -H "Content-Type: application/json" \
     -d '{"task_context": {"task_type": "ping"}}'
```

Clients may alternatively use `Authorization: Bearer <token>` if
`MCP_BEARER_TOKEN` is configured.
