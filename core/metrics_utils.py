import time

try:  # pragma: no cover - depends on optional runtime extras
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback for slim test envs
    class _NoOpMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs) -> None:
            return None

        def observe(self, *args, **kwargs) -> None:
            return None

    def Counter(*args, **kwargs):  # type: ignore[misc]
        return _NoOpMetric()

    def Gauge(*args, **kwargs):  # type: ignore[misc]
        return _NoOpMetric()

    def Histogram(*args, **kwargs):  # type: ignore[misc]
        return _NoOpMetric()

    def generate_latest() -> bytes:
        return b""

    CONTENT_TYPE_LATEST = "text/plain"

try:  # pragma: no cover - depends on optional runtime extras
    from fastapi import APIRouter, Request
    from fastapi.responses import Response
    from starlette.middleware.base import BaseHTTPMiddleware
except ModuleNotFoundError:  # pragma: no cover - fallback for slim test envs
    class Request:  # type: ignore[override]
        def __init__(self, url=None):
            self.url = url

    class Response:  # type: ignore[override]
        def __init__(self, content=None, media_type: str | None = None, status_code: int = 200):
            self.content = content
            self.media_type = media_type
            self.status_code = status_code

    class APIRouter:  # type: ignore[override]
        def get(self, _path: str):
            def decorator(func):
                return func

            return decorator

    class BaseHTTPMiddleware:  # type: ignore[override]
        def __init__(self, app):
            self.app = app

TASKS_PROCESSED = Counter(
    "agentnn_tasks_processed_total", "Total processed tasks", ["service"]
)
ACTIVE_SESSIONS = Gauge(
    "agentnn_active_sessions", "Active sessions", ["service"]
)
TOKENS_IN = Counter("agentnn_tokens_in_total", "Tokens received", ["service"])
TOKENS_OUT = Counter("agentnn_tokens_out_total", "Tokens sent", ["service"])
RESPONSE_TIME = Histogram(
    "agentnn_response_seconds", "Response time in seconds", ["service", "path"]
)
REQUEST_ERRORS = Counter(
    "agentnn_request_errors_total",
    "Total error responses",
    ["service", "path", "status"],
)

# additional metrics for feedback and routing
FEEDBACK_POSITIVE = Counter(
    "agentnn_feedback_positive_total",
    "Positive feedback entries",
    ["agent"],
)
FEEDBACK_NEGATIVE = Counter(
    "agentnn_feedback_negative_total",
    "Negative feedback entries",
    ["agent"],
)
TASK_SUCCESS = Counter(
    "agentnn_task_success_total",
    "Successful tasks per type",
    ["task_type"],
)
ROUTING_DECISIONS = Counter(
    "agentnn_routing_decisions_total",
    "Routing decisions",
    ["task_type", "worker"],
)


def metrics_router() -> APIRouter:
    router = APIRouter()

    @router.get("/metrics")
    async def metrics() -> Response:
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return router


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request durations."""

    def __init__(self, app, service: str):
        super().__init__(app)
        self.service = service

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            RESPONSE_TIME.labels(self.service, request.url.path).observe(duration)
            REQUEST_ERRORS.labels(self.service, request.url.path, "500").inc()
            raise
        duration = time.perf_counter() - start
        RESPONSE_TIME.labels(self.service, request.url.path).observe(duration)
        if response.status_code >= 400:
            REQUEST_ERRORS.labels(
                self.service,
                request.url.path,
                str(response.status_code),
            ).inc()
        return response
