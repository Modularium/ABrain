import time
try:  # pragma: no cover - optional web deps
    from fastapi import APIRouter, Request
    from fastapi.responses import Response
    from starlette.middleware.base import BaseHTTPMiddleware
except Exception:  # pragma: no cover - optional web deps
    APIRouter = Request = Response = None

    class BaseHTTPMiddleware:  # type: ignore[override]
        """Fallback stub when FastAPI/Starlette is unavailable."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("FastAPI middleware dependencies are not installed")
try:  # pragma: no cover - optional metrics deps
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
except Exception:  # pragma: no cover - optional metrics deps
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class _DummyValue:
        def __init__(self) -> None:
            self._current = 0.0

        def get(self) -> float:
            return self._current

    class _DummyMetricChild:
        def __init__(self) -> None:
            self._value = _DummyValue()

        def inc(self, amount: float = 1.0) -> None:
            self._value._current += amount

        def observe(self, amount: float) -> None:
            self._value._current = amount

        def set(self, value: float) -> None:
            self._value._current = value

    class _DummyMetric:
        def __init__(self, *args, **kwargs) -> None:
            self._children: dict[tuple[str, ...], _DummyMetricChild] = {}

        def labels(self, *label_values: str) -> _DummyMetricChild:
            key = tuple(str(value) for value in label_values)
            if key not in self._children:
                self._children[key] = _DummyMetricChild()
            return self._children[key]

    def Counter(*args, **kwargs):  # type: ignore[misc]
        return _DummyMetric()

    def Gauge(*args, **kwargs):  # type: ignore[misc]
        return _DummyMetric()

    def Histogram(*args, **kwargs):  # type: ignore[misc]
        return _DummyMetric()

    def generate_latest() -> bytes:
        return b""

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
    if APIRouter is None or Response is None:
        raise RuntimeError("FastAPI metrics router dependencies are not installed")
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
