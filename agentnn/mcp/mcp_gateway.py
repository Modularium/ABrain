"""Public MCP gateway with authentication."""

from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Request, status

from api_gateway.connectors import ServiceConnector
from core.run_service import run_service
from ..auth.auth_middleware import AuthMiddleware

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8090")
API_KEYS = os.getenv("MCP_API_KEYS", "")
BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN")


def create_gateway() -> FastAPI:
    app = FastAPI(title="MCP Gateway")
    app.add_middleware(AuthMiddleware, api_keys=API_KEYS, bearer_token=BEARER_TOKEN)
    conn = ServiceConnector(MCP_SERVER_URL)
    prefix = "/v1/mcp"

    @app.post(f"{prefix}/task/execute")
    async def execute(request: Request) -> dict:
        payload = await request.json()
        return await conn.post("/execute", payload)

    @app.post(f"{prefix}/tool/use")
    async def tool_use(request: Request) -> dict:
        _ = await request.json()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error_code": "legacy_tool_proxy_disabled",
                "message": (
                    "Legacy dynamic tool execution via the MCP gateway is disabled. "
                    "Use the fixed core tool surface instead."
                ),
                "details": {
                    "canonical_path": "services.core.execute_tool",
                    "legacy_route": f"{prefix}/tool/use",
                },
            },
        )

    @app.post(f"{prefix}/context/save")
    async def save(request: Request) -> dict:
        payload = await request.json()
        return await conn.post("/context/save", payload)

    @app.get(f"{prefix}/context/load/{'{sid}'}")
    async def load(sid: str) -> dict:
        return await conn.get(f"/context/load/{sid}")

    return app


def main() -> None:  # pragma: no cover - entrypoint
    app = create_gateway()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8089"))
    run_service(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover - script
    main()
