"""LEGACY (disabled): historical MCP server, not part of canonical runtime."""

from __future__ import annotations

import os
from fastapi import APIRouter, FastAPI, HTTPException, status

from api_gateway.connectors import ServiceConnector
from ..storage import context_store
from ..context import generate_map
from ..prompting import propose_refinement
from ..storage import snapshot_store
from core.voting import ProposalVote, record_vote
from datetime import datetime
from ..session.session_manager import SessionManager
from .mcp_ws import ws_server
from core.model_context import ModelContext
from core.run_service import run_service

DISPATCHER_URL = os.getenv("DISPATCHER_URL", "http://task_dispatcher:8000")
SESSION_MANAGER_URL = os.getenv("SESSION_MANAGER_URL", "http://session_manager:8000")
REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "http://agent_registry:8001")
TOOLS_URL = os.getenv("PLUGIN_AGENT_URL", "http://plugin_agent_service:8110")

session_pool = SessionManager()


def _legacy_disabled(path: str, canonical_path: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error_code": "legacy_mcp_runtime_disabled",
            "message": (
                "Legacy MCP runtime endpoints are disabled. "
                "Use the canonical services/* runtime instead."
            ),
            "details": {
                "canonical_path": canonical_path,
                "legacy_route": path,
            },
        },
    )


def create_app() -> FastAPI:
    """Return the FastAPI application."""
    router = APIRouter(prefix="/v1/mcp")
    dispatcher = ServiceConnector(DISPATCHER_URL)
    sessions = ServiceConnector(SESSION_MANAGER_URL)
    registry = ServiceConnector(REGISTRY_URL)
    @router.get("/ping")
    async def ping() -> dict:
        return {"status": "legacy_disabled"}

    @router.post("/execute", response_model=ModelContext)
    async def execute(ctx: ModelContext) -> ModelContext:
        _ = ctx
        _legacy_disabled("/v1/mcp/execute", "services/core.py")

    @router.post("/task/execute", response_model=ModelContext)
    async def execute_task(ctx: ModelContext) -> ModelContext:
        _ = ctx
        _legacy_disabled("/v1/mcp/task/execute", "services/core.py")

    @router.post("/context")
    async def update_context(ctx: ModelContext) -> dict:
        _ = ctx
        _legacy_disabled("/v1/mcp/context", "services/session_manager")

    @router.post("/context/save")
    async def save_context_route(ctx: ModelContext) -> dict:
        _ = ctx
        _legacy_disabled("/v1/mcp/context/save", "services/session_manager")

    @router.get("/context/load/{sid}")
    async def load_context_route(sid: str) -> dict:
        _ = sid
        _legacy_disabled("/v1/mcp/context/load/{sid}", "services/session_manager")

    @router.get("/context/history")
    async def list_contexts_route() -> dict:
        _legacy_disabled("/v1/mcp/context/history", "services/session_manager")

    @router.get("/context/map")
    async def context_map_route() -> dict:
        _legacy_disabled("/v1/mcp/context/map", "services/session_manager")

    @router.get("/context/{sid}")
    async def get_context(sid: str) -> dict:
        _ = sid
        _legacy_disabled("/v1/mcp/context/{sid}", "services/session_manager")

    @router.get("/context/get/{sid}")
    async def get_context_alt(sid: str) -> dict:
        _ = sid
        _legacy_disabled("/v1/mcp/context/get/{sid}", "services/session_manager")

    @router.post("/agent/create")
    async def create_agent(agent: dict) -> dict:
        _ = agent
        _legacy_disabled("/v1/mcp/agent/create", "services/agent_registry")

    @router.post("/agent/register")
    async def agent_register(agent: dict) -> dict:
        _ = agent
        _legacy_disabled("/v1/mcp/agent/register", "services/agent_registry")

    @router.get("/agent/list")
    async def agent_list() -> list:
        _legacy_disabled("/v1/mcp/agent/list", "services/agent_registry")

    @router.get("/agent/info/{name}")
    async def agent_info(name: str) -> dict:
        _ = name
        _legacy_disabled("/v1/mcp/agent/info/{name}", "services/agent_registry")

    @router.post("/tool/use")
    async def use_tool(payload: dict) -> dict:
        # legacy (disabled): kept only to reject the historical generic tool proxy
        _ = payload
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error_code": "legacy_tool_proxy_disabled",
                "message": (
                    "Legacy dynamic tool execution via MCP is disabled. "
                    "Use the fixed core tool surface instead."
                ),
                "details": {
                    "canonical_path": "services.core.execute_tool",
                    "legacy_route": "/v1/mcp/tool/use",
                },
            },
        )

    @router.post("/session/start")
    async def session_start(payload: dict | None = None) -> dict:
        _ = payload
        _legacy_disabled("/v1/mcp/session/start", "services/session_manager")

    @router.get("/session/status/{sid}")
    async def session_status_route(sid: str) -> dict:
        _ = sid
        _legacy_disabled("/v1/mcp/session/status/{sid}", "services/session_manager")

    @router.post("/session/restore/{snapshot_id}")
    async def session_restore(snapshot_id: str) -> dict:
        _ = snapshot_id
        _legacy_disabled("/v1/mcp/session/restore/{snapshot_id}", "services/session_manager")

    @router.post("/session/create")
    async def create_session_route() -> dict:
        _legacy_disabled("/v1/mcp/session/create", "services/session_manager")

    @router.post("/session/{sid}/add_agent")
    async def add_agent_route(sid: str, payload: dict) -> dict:
        _ = (sid, payload)
        _legacy_disabled("/v1/mcp/session/{sid}/add_agent", "services/session_manager")

    @router.post("/session/{sid}/run_task")
    async def run_task_route(sid: str, payload: dict) -> dict:
        _ = (sid, payload)
        _legacy_disabled("/v1/mcp/session/{sid}/run_task", "services/core.py")

    @router.post("/task/ask", response_model=ModelContext)
    async def task_ask(ctx: ModelContext) -> ModelContext:
        _ = ctx
        _legacy_disabled("/v1/mcp/task/ask", "services/core.py")

    @router.post("/task/dispatch", response_model=ModelContext)
    async def task_dispatch(ctx: ModelContext) -> ModelContext:
        _ = ctx
        _legacy_disabled("/v1/mcp/task/dispatch", "services/core.py")

    @router.get("/task/result/{task_id}")
    async def task_result(task_id: str) -> dict:
        _ = task_id
        _legacy_disabled("/v1/mcp/task/result/{task_id}", "services/core.py")

    @router.post("/prompt/refine")
    async def prompt_refine(payload: dict) -> dict:
        _ = payload
        _legacy_disabled("/v1/mcp/prompt/refine", "services/core.py")

    @router.post("/train/start")
    async def train_start_route(payload: dict) -> dict:
        _ = payload
        _legacy_disabled("/v1/mcp/train/start", "services/core.py")

    @router.post("/feedback/record/{sid}")
    async def feedback_record(sid: str, payload: dict) -> dict:
        _ = (sid, payload)
        _legacy_disabled("/v1/mcp/feedback/record/{sid}", "services/session_manager")

    @router.post("/governance/vote")
    async def governance_vote(payload: dict) -> dict:
        _ = payload
        _legacy_disabled("/v1/mcp/governance/vote", "services/core.py")

    app = FastAPI(title="ABrain MCP Server")
    app.include_router(router)
    return app


def main() -> None:  # pragma: no cover - entrypoint
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8090"))
    run_service(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover - script
    main()
