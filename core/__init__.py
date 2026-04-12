"""Core utilities for ABrain."""

try:
    from .logging_utils import LoggingMiddleware, exception_handler, init_logging
    from .metrics_utils import MetricsMiddleware, metrics_router
    from .auth_utils import AuthMiddleware
except Exception:  # pragma: no cover - optional deps
    LoggingMiddleware = exception_handler = init_logging = None
    MetricsMiddleware = metrics_router = None
    AuthMiddleware = None
from .audit_log import AuditLog, AuditEntry
from .execution import ExecutionDispatcher, maybe_await, run_sync
from .models import (
    AdminBotAction,
    AdminBotErrorPayload,
    AdminBotRequestEnvelope,
    AdminBotRequestedBy,
    AdminBotServiceStatusInput,
    AdminBotSuccessPayload,
    AdminBotSystemHealthInput,
    AdminBotSystemStatusInput,
    CoreErrorCode,
    CoreExecutionError,
    DispatchTaskToolInput,
    EmptyToolInput,
    ListAgentsToolInput,
    RequesterIdentity,
    RequesterType,
    StructuredError,
    ToolExecutionRequest,
    ToolExecutionResult,
)
from .tools import ToolDefinition, ToolRegistry, build_default_registry

__all__ = [
    "AdminBotAction",
    "AdminBotErrorPayload",
    "AdminBotRequestEnvelope",
    "AdminBotRequestedBy",
    "AdminBotServiceStatusInput",
    "AdminBotSuccessPayload",
    "AdminBotSystemHealthInput",
    "AdminBotSystemStatusInput",
    "AuditLog",
    "AuditEntry",
    "CoreErrorCode",
    "CoreExecutionError",
    "DispatchTaskToolInput",
    "EmptyToolInput",
    "ExecutionDispatcher",
    "LoggingMiddleware",
    "ListAgentsToolInput",
    "RequesterIdentity",
    "RequesterType",
    "StructuredError",
    "ToolDefinition",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolRegistry",
    "build_default_registry",
    "exception_handler",
    "init_logging",
    "maybe_await",
    "MetricsMiddleware",
    "metrics_router",
    "run_sync",
    "AuthMiddleware",
]
