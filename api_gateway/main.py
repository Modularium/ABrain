import os
from fastapi import FastAPI, Request, HTTPException
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
@app.post("/embed")
@limiter.limit(RATE_LIMIT)
async def embed_route(request: Request) -> dict:
    """Return embedding for provided text."""
    check_scope(request, "embed:write")
    payload = await request.json()
    return await vector_conn.post("/embed", payload)
