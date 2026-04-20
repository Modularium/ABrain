import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Path as ApiPath, Query, Request
from .connectors import ServiceConnector
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from api_gateway.schemas import (
    API_DESCRIPTION,
    OPENAPI_TAGS,
    AgentCatalogResponse,
    ApiErrorResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalListResponse,
    ControlPlaneOverviewResponse,
    ControlPlaneRunRequest,
    ExplainabilityResponse,
    GovernanceListResponse,
    LabOsReasoningRequest,
    PlanListResponse,
    PlanRunResponse,
    RoutingModelsResponse,
    TaskRunResponse,
    TraceDetailResponse,
    TraceListResponse,
)
from core.logging_utils import LoggingMiddleware, exception_handler, init_logging
from core.metrics_utils import MetricsMiddleware, metrics_router
from jose import JWTError, jwt


def api_route(version: str) -> Callable:
    """Mark an API route with a version string."""
    def decorator(func: Callable) -> Callable:
        func.api_version = version
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        return wrapper
    return decorator


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
REPO_ROOT = Path(__file__).resolve().parents[1]
API_VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
COMMON_ERROR_RESPONSES = {
    403: {
        "model": ApiErrorResponse,
        "description": "The caller is authenticated but not authorized for the requested scope.",
    },
    503: {
        "model": ApiErrorResponse,
        "description": "An internal upstream service is temporarily unavailable.",
    },
}

app = FastAPI(
    title="ABrain Developer API",
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
)
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
@app.post("/llm/generate", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def llm_generate(request: Request) -> dict:
    check_scope(request, "llm:generate")
    payload = await request.json()
    return await llm_conn.post("/generate", payload)


@api_route(version="dev")  # \U0001F6A7 experimental
@app.post("/chat", include_in_schema=False)
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
@app.get("/chat/history/{sid}", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def chat_history(sid: str, request: Request) -> dict:
    check_scope(request, "chat:read")
    return await session_conn.get(f"/context/{sid}")


@api_route(version="dev")  # \U0001F6A7 experimental
@app.post("/chat/feedback", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def chat_feedback(request: Request) -> dict:
    check_scope(request, "feedback:write")
    payload = await request.json()
    sid = payload.get("session_id")
    return await session_conn.post(f"/session/{sid}/feedback", payload)


@api_route(version="dev")
@app.post("/sessions", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def start_session_route(request: Request) -> dict:
    """Public route to start a new session."""
    check_scope(request, "session:write")
    return await session_conn.post("/start_session", {})


@api_route(version="dev")
@app.get("/sessions/{sid}/history", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def session_history_route(sid: str, request: Request) -> dict:
    """Return conversation history for a session."""
    check_scope(request, "session:read")
    return await session_conn.get(f"/context/{sid}")


@api_route(version="dev")
@app.get("/agents", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def list_agents_route(request: Request) -> dict:
    """List available agents."""
    check_scope(request, "agents:read")
    return await registry_conn.get("/agents")


@api_route(version="dev")
@app.get(
    "/control-plane/overview",
    response_model=ControlPlaneOverviewResponse,
    tags=["Control Plane"],
    summary="Inspect the control-plane overview",
    description="Return the top-level control-plane overview assembled from canonical read-only `services/core.py` helpers.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_overview(request: Request) -> dict:
    """Return a thin overview assembled from canonical control-plane reads."""
    check_scope(request, "agents:read")
    from services.core import get_control_plane_overview

    return get_control_plane_overview(
        agent_limit=5,
        approval_limit=5,
        trace_limit=5,
        plan_limit=5,
        governance_limit=5,
    )


@api_route(version="dev")
@app.get(
    "/control-plane/agents",
    response_model=AgentCatalogResponse,
    tags=["Agents"],
    summary="List agents exposed by the control plane",
    description="Return the projected agent catalog built from the canonical core agent listing path.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_agents(request: Request) -> dict:
    """Return agents projected from the canonical agent listing path."""
    check_scope(request, "agents:read")
    from services.core import list_agent_catalog

    return list_agent_catalog()


@api_route(version="dev")
@app.get(
    "/control-plane/traces",
    response_model=TraceListResponse,
    tags=["Traces"],
    summary="List recent traces",
    description="Return recent canonical audit traces for debugging, approval follow-up and explainability lookup.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_traces(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of traces to return."),
) -> dict:
    """Return recent canonical traces."""
    check_scope(request, "agents:read")
    from services.core import list_recent_traces

    return list_recent_traces(limit=limit)


@api_route(version="dev")
@app.get(
    "/control-plane/traces/{trace_id}",
    response_model=TraceDetailResponse,
    tags=["Traces"],
    summary="Get one trace snapshot",
    description="Return the stored trace snapshot, including spans and explainability records when present.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_trace(
    request: Request,
    trace_id: str = ApiPath(..., description="Trace identifier returned by task or plan execution."),
) -> dict:
    """Return a single trace snapshot."""
    check_scope(request, "agents:read")
    from services.core import get_trace

    return get_trace(trace_id)


@api_route(version="dev")
@app.get(
    "/control-plane/traces/{trace_id}/explainability",
    response_model=ExplainabilityResponse,
    tags=["Traces"],
    summary="Get explainability for one trace",
    description="Return explainability records for a single trace without bypassing the canonical audit store.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_explainability(
    request: Request,
    trace_id: str = ApiPath(..., description="Trace identifier whose explainability records should be returned."),
) -> dict:
    """Return explainability records for a single trace."""
    check_scope(request, "agents:read")
    from services.core import get_explainability

    return get_explainability(trace_id)


@api_route(version="dev")
@app.get(
    "/control-plane/governance",
    response_model=GovernanceListResponse,
    tags=["Control Plane"],
    summary="List recent governance decisions",
    description="Return recent allow, deny and approval-required decisions derived from canonical trace and explainability data.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_governance(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of governance events to return."),
) -> dict:
    """Return recent governance decisions derived from canonical traces."""
    check_scope(request, "agents:read")
    from services.core import list_recent_governance_decisions

    return list_recent_governance_decisions(limit=limit)


@api_route(version="dev")
@app.get(
    "/control-plane/routing/models",
    response_model=RoutingModelsResponse,
    tags=["Routing"],
    summary="List the canonical routing-model catalog",
    description=(
        "Return the read-only routing-model catalog with quantization and "
        "distillation lineage plus per-model energy profile, projected from "
        "`services.core.get_routing_models` without duplicating the catalog. "
        "Unknown filter values surface as HTTP 400 `invalid_tier` / "
        "`invalid_provider` / `invalid_purpose` so operator typos fail loud."
    ),
    responses={
        **COMMON_ERROR_RESPONSES,
        400: {
            "model": ApiErrorResponse,
            "description": "A filter value is not part of the canonical enum.",
        },
    },
)
@limiter.limit(RATE_LIMIT)
async def control_plane_routing_models(
    request: Request,
    tier: str | None = Query(
        default=None,
        description="Restrict to one of local, small, medium, large.",
    ),
    provider: str | None = Query(
        default=None,
        description="Restrict to one of anthropic, openai, google, local, custom.",
    ),
    purpose: str | None = Query(
        default=None,
        description="Restrict to models that include this ModelPurpose value.",
    ),
    available_only: bool = Query(
        default=False,
        description="Drop entries with is_available=False when set.",
    ),
) -> dict:
    """Return the canonical routing-model catalog with lineage and energy metadata."""
    check_scope(request, "agents:read")
    from services.core import get_routing_models

    payload = get_routing_models(
        tier=tier,
        provider=provider,
        purpose=purpose,
        available_only=available_only,
    )
    if "error" in payload:
        raise HTTPException(
            status_code=400,
            detail=payload.get("detail") or payload["error"],
        )
    return payload


_LABOS_REASONING_ENDPOINT_SUMMARIES: dict[str, str] = {
    "reactor_daily_overview": "Which reactors need attention today, which are nominal.",
    "incident_review": "Prioritised review of open/critical LabOS incidents.",
    "maintenance_suggestions": "Overdue/due maintenance items and allowed follow-up actions.",
    "schedule_runtime_review": "Schedules and commands that are failing or blocked.",
    "cross_domain_overview": "Combined reactor + incident + maintenance + schedule focus list.",
    # RobotOps V1 — module-scoped reasoning.
    "module_daily_overview": "RobotOps V1 — which modules are nominal / attention / offline.",
    "module_incident_review": "RobotOps V1 — modules with open incidents / capability impact.",
    "module_coordination_review": "RobotOps V1 — blocked/impacted module dependency edges.",
    "module_capability_risk_review": "RobotOps V1 — modules with missing/degraded critical capabilities.",
    "robotops_cross_domain_overview": "RobotOps V1 — combined ReactorOps + RobotOps focus list.",
}


def _register_labos_reasoning_endpoint(mode: str, summary: str) -> None:
    """Register one `POST /control-plane/reasoning/labos/<mode>` endpoint.

    All five endpoints share the same thin delegation to
    ``services.core.run_labos_reasoning`` — the only per-mode difference is
    the URL path and the OpenAPI summary.
    """

    @api_route(version="dev")
    @app.post(
        f"/control-plane/reasoning/labos/{mode}",
        tags=["Reasoning"],
        summary=summary,
        description=(
            "Run the deterministic ABrain V2 LabOS domain reasoner for "
            f"`{mode}` over a caller-supplied LabOS context snapshot. "
            "Thin delegate of `services.core.run_labos_reasoning` — no "
            "parallel implementation. Invalid contexts surface as HTTP 400 "
            "`invalid_context` with the pydantic error detail; unknown "
            "reasoning modes cannot occur since the mode is fixed in the URL."
        ),
        responses={
            **COMMON_ERROR_RESPONSES,
            400: {
                "model": ApiErrorResponse,
                "description": "The supplied context fails LabOS schema validation.",
            },
        },
    )
    @limiter.limit(RATE_LIMIT)
    async def _endpoint(request: Request, payload: LabOsReasoningRequest) -> dict:
        check_scope(request, "agents:read")
        from services.core import run_labos_reasoning

        response = run_labos_reasoning(mode, payload.context)
        if "error" in response:
            raise HTTPException(
                status_code=400,
                detail=response.get("detail") or response["error"],
            )
        return response

    _endpoint.__name__ = f"control_plane_reasoning_labos_{mode}"


for _mode, _summary in _LABOS_REASONING_ENDPOINT_SUMMARIES.items():
    _register_labos_reasoning_endpoint(_mode, _summary)


@api_route(version="dev")
@app.get(
    "/control-plane/approvals",
    response_model=ApprovalListResponse,
    tags=["Approvals"],
    summary="List pending approvals",
    description="Return approvals that currently pause canonical plan execution and require a human decision.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_approvals(request: Request) -> dict:
    """Return currently pending approvals."""
    check_scope(request, "agents:read")
    from services.core import list_pending_approvals

    return list_pending_approvals()


@api_route(version="dev")
@app.post(
    "/control-plane/approvals/{approval_id}/approve",
    response_model=ApprovalDecisionResponse,
    tags=["Approvals"],
    summary="Approve a paused plan step",
    description="Record an approval decision and resume the paused plan through the canonical approval and orchestration path.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_approve(
    request: Request,
    payload: ApprovalDecisionRequest,
    approval_id: str = ApiPath(..., description="Pending approval identifier returned by a paused task or plan."),
) -> dict:
    """Approve a pending plan step through the canonical core."""
    check_scope(request, "chat:write")
    from services.core import approve_plan_step

    return approve_plan_step(
        approval_id,
        decided_by=payload.decided_by,
        comment=payload.comment,
        rating=payload.rating,
    )


@api_route(version="dev")
@app.post(
    "/control-plane/approvals/{approval_id}/reject",
    response_model=ApprovalDecisionResponse,
    tags=["Approvals"],
    summary="Reject a paused plan step",
    description="Record a rejection and return the terminal canonical plan result without introducing alternate approval logic.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_reject(
    request: Request,
    payload: ApprovalDecisionRequest,
    approval_id: str = ApiPath(..., description="Pending approval identifier returned by a paused task or plan."),
) -> dict:
    """Reject a pending plan step through the canonical core."""
    check_scope(request, "chat:write")
    from services.core import reject_plan_step

    return reject_plan_step(
        approval_id,
        decided_by=payload.decided_by,
        comment=payload.comment,
        rating=payload.rating,
    )


@api_route(version="dev")
@app.get(
    "/control-plane/plans",
    response_model=PlanListResponse,
    tags=["Plans"],
    summary="List recent plans",
    description="Return recent plan runs projected from the canonical plan and trace state stores.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_plans(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of plans to return."),
) -> dict:
    """Return recent plan runs derived from canonical traces."""
    check_scope(request, "agents:read")
    from services.core import list_recent_plans

    return list_recent_plans(limit=limit)


@api_route(version="dev")
@app.post(
    "/control-plane/tasks/run",
    response_model=TaskRunResponse,
    tags=["Tasks"],
    summary="Run one task through the control plane",
    description="Launch a single task through the canonical decision, governance, approval, execution and audit pipeline.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_run_task(payload: ControlPlaneRunRequest, request: Request) -> dict:
    """Run a single task through the canonical core pipeline."""
    check_scope(request, "chat:write")
    from services.core import run_task

    return run_task(payload.to_core_payload())


@api_route(version="dev")
@app.post(
    "/control-plane/plans/run",
    response_model=PlanRunResponse,
    tags=["Plans"],
    summary="Run a multi-step plan through the control plane",
    description="Launch a canonical multi-step plan through the existing orchestration pipeline without bypassing governance or audit.",
    responses=COMMON_ERROR_RESPONSES,
)
@limiter.limit(RATE_LIMIT)
async def control_plane_run_plan(payload: ControlPlaneRunRequest, request: Request) -> dict:
    """Run a plan through the canonical orchestration pipeline."""
    check_scope(request, "chat:write")
    from services.core import run_task_plan

    return run_task_plan(payload.to_core_payload())


@api_route(version="dev")
@app.post("/embed", include_in_schema=False)
@limiter.limit(RATE_LIMIT)
async def embed_route(request: Request) -> dict:
    """Return embedding for provided text."""
    check_scope(request, "embed:write")
    payload = await request.json()
    return await vector_conn.post("/embed", payload)
