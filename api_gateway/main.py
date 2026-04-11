import os
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from utils.api_utils import api_route
from .connectors import ServiceConnector
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.logging_utils import LoggingMiddleware, exception_handler, init_logging
from core.metrics_utils import MetricsMiddleware, metrics_router
from jose import JWTError, jwt


API_AUTH_ENABLED = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
API_GATEWAY_KEY = os.getenv("API_GATEWAY_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
API_KEY_SCOPES = os.getenv("API_KEY_SCOPES", "*").split(",")
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")
DISPATCHER_URL = os.getenv("DISPATCHER_URL", "http://dispatcher:8001")
SESSION_MANAGER_URL = os.getenv("SESSION_MANAGER_URL", "http://session_manager:8005")
AGENT_REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "http://registry:8002")
VECTOR_STORE_URL = os.getenv("VECTOR_STORE_URL", "http://vector_store:8004")
RATE_LIMIT = os.getenv("RATE_LIMIT", "60/minute")
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

logger = init_logging("api_gateway")
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
app = FastAPI(title="API Gateway")
app.add_middleware(LoggingMiddleware, logger=logger)
app.add_middleware(MetricsMiddleware, service="api_gateway")
app.add_exception_handler(Exception, exception_handler(logger))
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(metrics_router())

# service connectors
dispatcher_conn = ServiceConnector(DISPATCHER_URL)
session_conn = ServiceConnector(SESSION_MANAGER_URL)
llm_conn = ServiceConnector(LLM_GATEWAY_URL)
registry_conn = ServiceConnector(AGENT_REGISTRY_URL)
vector_conn = ServiceConnector(VECTOR_STORE_URL)


class ControlPlaneRunRequest(BaseModel):
    """Canonical task/plan launch payload for the control plane."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=4096)
    task_id: str | None = Field(default=None, max_length=128)
    input_data: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)

    def to_core_payload(self) -> dict[str, Any]:
        payload = dict(self.input_data)
        payload["task_type"] = self.task_type
        if self.description:
            payload["description"] = self.description
        if self.task_id:
            payload["task_id"] = self.task_id
        if self.options:
            payload["preferences"] = {"execution_hints": dict(self.options)}
        return payload


class ApprovalDecisionRequest(BaseModel):
    """Human approval action passed through the control plane."""

    model_config = ConfigDict(extra="forbid")

    decided_by: str = Field(default="control-plane", min_length=1, max_length=128)
    comment: str | None = Field(default=None, max_length=2048)


def _control_plane_layers() -> list[dict[str, str]]:
    return [
        {"name": "Decision", "status": "available"},
        {"name": "Execution", "status": "available"},
        {"name": "Learning", "status": "available"},
        {"name": "Orchestration", "status": "available"},
        {"name": "Approval", "status": "available"},
        {"name": "Governance", "status": "available"},
        {"name": "Audit/Trace", "status": "available"},
        {"name": "MCP v2", "status": "available"},
    ]


def _safe_control_plane_call(label: str, func) -> tuple[Any, list[str]]:
    try:
        return func(), []
    except Exception as exc:  # pragma: no cover - defensive UI containment
        return None, [f"{label}_unavailable:{exc.__class__.__name__}"]


def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:  # pragma: no cover - invalid tokens
        return None


def check_scope(request: Request, scope: str) -> None:
    """Verify that the caller is authorized for the given scope."""
    if not API_AUTH_ENABLED:
        return
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == API_GATEWAY_KEY:
        if scope in API_KEY_SCOPES or "*" in API_KEY_SCOPES:
            return
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        payload = _decode_token(token.split()[1])
        if payload:
            scopes = payload.get("scopes", [])
            if scope in scopes or "*" in scopes:
                return
    raise HTTPException(status_code=403, detail="Forbidden")


@api_route(version="dev")  # \U0001F6A7 experimental
@app.post("/llm/generate")
@limiter.limit(RATE_LIMIT)
async def llm_generate(request: Request) -> dict:
    check_scope(request, "llm:generate")
    payload = await request.json()
    return await llm_conn.post("/generate", payload)


@api_route(version="dev")  # \U0001F6A7 experimental
@app.post("/chat")
@limiter.limit(RATE_LIMIT)
async def chat(request: Request) -> dict:
    check_scope(request, "chat:write")
    payload = await request.json()
    sid = payload.get("session_id")
    if not sid:
        resp = await session_conn.post("/start_session", {})
        sid = resp.get("session_id")

    data = {
        "task_type": "chat",
        "input": payload.get("message", ""),
        "session_id": sid,
    }
    result = await dispatcher_conn.post("/task", data)
    return {"session_id": sid, **result}


@api_route(version="dev")  # \U0001F6A7 experimental
@app.get("/chat/history/{sid}")
@limiter.limit(RATE_LIMIT)
async def chat_history(sid: str, request: Request) -> dict:
    check_scope(request, "chat:read")
    return await session_conn.get(f"/context/{sid}")


@api_route(version="dev")  # \U0001F6A7 experimental
@app.post("/chat/feedback")
@limiter.limit(RATE_LIMIT)
async def chat_feedback(request: Request) -> dict:
    check_scope(request, "feedback:write")
    payload = await request.json()
    sid = payload.get("session_id")
    return await session_conn.post(f"/session/{sid}/feedback", payload)


@api_route(version="dev")
@app.post("/sessions")
@limiter.limit(RATE_LIMIT)
async def start_session_route(request: Request) -> dict:
    """Public route to start a new session."""
    check_scope(request, "session:write")
    return await session_conn.post("/start_session", {})


@api_route(version="dev")
@app.get("/sessions/{sid}/history")
@limiter.limit(RATE_LIMIT)
async def session_history_route(sid: str, request: Request) -> dict:
    """Return conversation history for a session."""
    check_scope(request, "session:read")
    return await session_conn.get(f"/context/{sid}")


@api_route(version="dev")
@app.get("/agents")
@limiter.limit(RATE_LIMIT)
async def list_agents_route(request: Request) -> dict:
    """List available agents."""
    check_scope(request, "agents:read")
    return await registry_conn.get("/agents")


@api_route(version="dev")
@app.get("/control-plane/overview")
@limiter.limit(RATE_LIMIT)
async def control_plane_overview(request: Request) -> dict:
    """Return a thin overview assembled from canonical control-plane reads."""
    check_scope(request, "agents:read")
    from services.core import (
        get_governance_state,
        list_agent_catalog,
        list_pending_approvals,
        list_recent_governance_decisions,
        list_recent_plans,
        list_recent_traces,
    )

    warnings: list[str] = []
    agents_result, issues = _safe_control_plane_call("agents", list_agent_catalog)
    warnings.extend(issues)
    approvals_result, issues = _safe_control_plane_call("approvals", list_pending_approvals)
    warnings.extend(issues)
    traces_result, issues = _safe_control_plane_call("traces", lambda: list_recent_traces(limit=8))
    warnings.extend(issues)
    plans_result, issues = _safe_control_plane_call("plans", lambda: list_recent_plans(limit=6))
    warnings.extend(issues)
    governance_result, issues = _safe_control_plane_call(
        "governance", lambda: list_recent_governance_decisions(limit=8)
    )
    warnings.extend(issues)
    governance_state, issues = _safe_control_plane_call("governance_state", get_governance_state)
    warnings.extend(issues)

    agents = (agents_result or {}).get("agents", [])
    approvals = (approvals_result or {}).get("approvals", [])
    traces = (traces_result or {}).get("traces", [])
    plans = (plans_result or {}).get("plans", [])
    governance = (governance_result or {}).get("governance", [])

    return {
        "system": {
            "name": "ABrain Control Plane",
            "layers": _control_plane_layers(),
            "governance": governance_state or {},
            "warnings": warnings,
        },
        "summary": {
            "agent_count": len(agents),
            "pending_approvals": len(approvals),
            "recent_traces": len(traces),
            "recent_plans": len(plans),
            "recent_governance_events": len(governance),
        },
        "agents": agents[:5],
        "pending_approvals": approvals[:5],
        "recent_traces": traces[:5],
        "recent_plans": plans[:5],
        "recent_governance": governance[:5],
    }


@api_route(version="dev")
@app.get("/control-plane/agents")
@limiter.limit(RATE_LIMIT)
async def control_plane_agents(request: Request) -> dict:
    """Return agents projected from the canonical agent listing path."""
    check_scope(request, "agents:read")
    from services.core import list_agent_catalog

    return list_agent_catalog()


@api_route(version="dev")
@app.get("/control-plane/traces")
@limiter.limit(RATE_LIMIT)
async def control_plane_traces(request: Request, limit: int = 10) -> dict:
    """Return recent canonical traces."""
    check_scope(request, "agents:read")
    from services.core import list_recent_traces

    return list_recent_traces(limit=max(1, min(limit, 50)))


@api_route(version="dev")
@app.get("/control-plane/traces/{trace_id}")
@limiter.limit(RATE_LIMIT)
async def control_plane_trace(request: Request, trace_id: str) -> dict:
    """Return a single trace snapshot."""
    check_scope(request, "agents:read")
    from services.core import get_trace

    return get_trace(trace_id)


@api_route(version="dev")
@app.get("/control-plane/traces/{trace_id}/explainability")
@limiter.limit(RATE_LIMIT)
async def control_plane_explainability(request: Request, trace_id: str) -> dict:
    """Return explainability records for a single trace."""
    check_scope(request, "agents:read")
    from services.core import get_explainability

    return get_explainability(trace_id)


@api_route(version="dev")
@app.get("/control-plane/governance")
@limiter.limit(RATE_LIMIT)
async def control_plane_governance(request: Request, limit: int = 10) -> dict:
    """Return recent governance decisions derived from canonical traces."""
    check_scope(request, "agents:read")
    from services.core import list_recent_governance_decisions

    return list_recent_governance_decisions(limit=max(1, min(limit, 50)))


@api_route(version="dev")
@app.get("/control-plane/approvals")
@limiter.limit(RATE_LIMIT)
async def control_plane_approvals(request: Request) -> dict:
    """Return currently pending approvals."""
    check_scope(request, "agents:read")
    from services.core import list_pending_approvals

    return list_pending_approvals()


@api_route(version="dev")
@app.post("/control-plane/approvals/{approval_id}/approve")
@limiter.limit(RATE_LIMIT)
async def control_plane_approve(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
) -> dict:
    """Approve a pending plan step through the canonical core."""
    check_scope(request, "chat:write")
    from services.core import approve_plan_step

    return approve_plan_step(
        approval_id,
        decided_by=payload.decided_by,
        comment=payload.comment,
    )


@api_route(version="dev")
@app.post("/control-plane/approvals/{approval_id}/reject")
@limiter.limit(RATE_LIMIT)
async def control_plane_reject(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
) -> dict:
    """Reject a pending plan step through the canonical core."""
    check_scope(request, "chat:write")
    from services.core import reject_plan_step

    return reject_plan_step(
        approval_id,
        decided_by=payload.decided_by,
        comment=payload.comment,
    )


@api_route(version="dev")
@app.get("/control-plane/plans")
@limiter.limit(RATE_LIMIT)
async def control_plane_plans(request: Request, limit: int = 10) -> dict:
    """Return recent plan runs derived from canonical traces."""
    check_scope(request, "agents:read")
    from services.core import list_recent_plans

    return list_recent_plans(limit=max(1, min(limit, 50)))


@api_route(version="dev")
@app.post("/control-plane/tasks/run")
@limiter.limit(RATE_LIMIT)
async def control_plane_run_task(payload: ControlPlaneRunRequest, request: Request) -> dict:
    """Run a single task through the canonical core pipeline."""
    check_scope(request, "chat:write")
    from services.core import run_task

    return run_task(payload.to_core_payload())


@api_route(version="dev")
@app.post("/control-plane/plans/run")
@limiter.limit(RATE_LIMIT)
async def control_plane_run_plan(payload: ControlPlaneRunRequest, request: Request) -> dict:
    """Run a plan through the canonical orchestration pipeline."""
    check_scope(request, "chat:write")
    from services.core import run_task_plan

    return run_task_plan(payload.to_core_payload())


@api_route(version="dev")
@app.post("/embed")
@limiter.limit(RATE_LIMIT)
async def embed_route(request: Request) -> dict:
    """Return embedding for provided text."""
    check_scope(request, "embed:write")
    payload = await request.json()
    return await vector_conn.post("/embed", payload)
