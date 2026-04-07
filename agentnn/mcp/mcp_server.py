"""Lightweight MCP compatible server exposing context and execution endpoints."""

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


def create_app() -> FastAPI:
    """Return the FastAPI application."""
    router = APIRouter(prefix="/v1/mcp")
    dispatcher = ServiceConnector(DISPATCHER_URL)
    sessions = ServiceConnector(SESSION_MANAGER_URL)
    registry = ServiceConnector(REGISTRY_URL)
    @router.get("/ping")
    async def ping() -> dict:
        return {"status": "ok"}

    @router.post("/execute", response_model=ModelContext)
    async def execute(ctx: ModelContext) -> ModelContext:
        return await dispatcher.post("/dispatch", ctx.model_dump())

    @router.post("/task/execute", response_model=ModelContext)
    async def execute_task(ctx: ModelContext) -> ModelContext:
        return await dispatcher.post("/dispatch", ctx.model_dump())

    @router.post("/context")
    async def update_context(ctx: ModelContext) -> dict:
        await sessions.post("/update_context", ctx.model_dump())
        return {"status": "ok"}

    @router.post("/context/save")
    async def save_context_route(ctx: ModelContext) -> dict:
        await sessions.post("/update_context", ctx.model_dump())
        context_store.save_context(ctx.session_id or "default", ctx.model_dump())
        return {"status": "ok"}

    @router.get("/context/load/{sid}")
    async def load_context_route(sid: str) -> dict:
        return {"context": context_store.load_context(sid)}

    @router.get("/context/history")
    async def list_contexts_route() -> dict:
        return {"sessions": context_store.list_contexts()}

    @router.get("/context/map")
    async def context_map_route() -> dict:
        return generate_map()

    @router.get("/context/{sid}")
    async def get_context(sid: str) -> dict:
        return await sessions.get(f"/context/{sid}")

    @router.get("/context/get/{sid}")
    async def get_context_alt(sid: str) -> dict:
        return await sessions.get(f"/context/{sid}")

    @router.post("/agent/create")
    async def create_agent(agent: dict) -> dict:
        return await registry.post("/register", agent)

    @router.post("/agent/register")
    async def agent_register(agent: dict) -> dict:
        return await registry.post("/register", agent)

    @router.get("/agent/list")
    async def agent_list() -> list:
        return await registry.get("/agents")

    @router.get("/agent/info/{name}")
    async def agent_info(name: str) -> dict:
        agents = await registry.get("/agents")
        for a in agents:
            if a.get("name") == name:
                return a
        return {}

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
        data = payload or {}
        return await sessions.post("/session", {"data": data})

    @router.get("/session/status/{sid}")
    async def session_status_route(sid: str) -> dict:
        return await sessions.get(f"/session/{sid}/status")

    @router.post("/session/restore/{snapshot_id}")
    async def session_restore(snapshot_id: str) -> dict:
        sid = snapshot_store.restore_snapshot(snapshot_id)
        return {"session_id": sid}

    @router.post("/session/create")
    async def create_session_route() -> dict:
        sid = session_pool.create_session()
        return {"session_id": sid}

    @router.post("/session/{sid}/add_agent")
    async def add_agent_route(sid: str, payload: dict) -> dict:
        session_pool.add_agent(sid, payload.get("agent_id"))
        return {"status": "ok"}

    @router.post("/session/{sid}/run_task")
    async def run_task_route(sid: str, payload: dict) -> dict:
        ctx = session_pool.run_task(sid, payload.get("task", ""))
        return ctx.model_dump()

    @router.post("/task/ask", response_model=ModelContext)
    async def task_ask(ctx: ModelContext) -> ModelContext:
        return await dispatcher.post("/dispatch", ctx.model_dump())

    @router.post("/task/dispatch", response_model=ModelContext)
    async def task_dispatch(ctx: ModelContext) -> ModelContext:
        return await dispatcher.post("/dispatch", ctx.model_dump())

    @router.get("/task/result/{task_id}")
    async def task_result(task_id: str) -> dict:
        return {"status": "unknown", "task_id": task_id}

    @router.post("/prompt/refine")
    async def prompt_refine(payload: dict) -> dict:
        prompt = payload.get("prompt", "")
        strategy = payload.get("strategy", "direct")
        return {"refined": propose_refinement(prompt, strategy)}

    @router.post("/train/start")
    async def train_start_route(payload: dict) -> dict:
        # minimal stub for training start
        return {"started": payload.get("agent")}

    @router.post("/feedback/record/{sid}")
    async def feedback_record(sid: str, payload: dict) -> dict:
        return await sessions.post(f"/session/{sid}/feedback", payload)

    @router.post("/governance/vote")
    async def governance_vote(payload: dict) -> dict:
        vote = ProposalVote(
            proposal_id=payload.get("proposal_id", "unknown"),
            agent_id=payload.get("agent_id", "anon"),
            decision=payload.get("decision", "yes"),
            comment=payload.get("comment"),
            created_at=datetime.utcnow().isoformat(),
        )
        record_vote(vote)
        return {"status": "recorded"}

    app = FastAPI(title="ABrain MCP Server")
    app.include_router(router)
    app.include_router(ws_server.router)
    return app


def main() -> None:  # pragma: no cover - entrypoint
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8090"))
    run_service(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover - script
    main()
