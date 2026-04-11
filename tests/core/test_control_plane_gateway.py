import asyncio
import importlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit


def _install_gateway_dependency_stubs() -> None:
    class _BoundLogger:
        def bind(self, **kwargs):
            return self

        def log(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

    structlog_module = types.SimpleNamespace(
        BoundLogger=_BoundLogger,
        processors=types.SimpleNamespace(
            TimeStamper=lambda *args, **kwargs: object(),
            add_log_level=object(),
            JSONRenderer=lambda *args, **kwargs: object(),
        ),
        dev=types.SimpleNamespace(ConsoleRenderer=lambda *args, **kwargs: object()),
        configure=lambda *args, **kwargs: None,
        make_filtering_bound_logger=lambda level: _BoundLogger,
        PrintLoggerFactory=lambda *args, **kwargs: object(),
        get_logger=lambda: _BoundLogger(),
    )
    limiter_module = types.SimpleNamespace(
        Limiter=lambda *args, **kwargs: types.SimpleNamespace(limit=lambda *a, **k: (lambda func: func))
    )
    slowapi_util = types.SimpleNamespace(get_remote_address=lambda request: "127.0.0.1")
    core_config = types.SimpleNamespace(settings=types.SimpleNamespace(LOG_DIR="/tmp"))
    jose_module = types.SimpleNamespace(
        JWTError=Exception,
        jwt=types.SimpleNamespace(decode=lambda *args, **kwargs: {}),
    )
    sys.modules.setdefault("structlog", structlog_module)
    sys.modules.setdefault("slowapi", limiter_module)
    sys.modules.setdefault("slowapi.util", slowapi_util)
    sys.modules.setdefault("core.config", core_config)
    sys.modules.setdefault("jose", jose_module)


def test_control_plane_overview_aggregates_core_reads(monkeypatch):
    _install_gateway_dependency_stubs()
    sys.modules.pop("api_gateway.main", None)
    sys.modules.pop("core.logging_utils", None)
    gateway = importlib.import_module("api_gateway.main")

    monkeypatch.setattr(
        "services.core.list_agent_catalog",
        lambda: {"agents": [{"agent_id": "agent-1", "display_name": "Agent One"}]},
    )
    monkeypatch.setattr(
        "services.core.list_pending_approvals",
        lambda: {"approvals": [{"approval_id": "approval-1"}]},
    )
    monkeypatch.setattr(
        "services.core.list_recent_traces",
        lambda limit=8: {"traces": [{"trace_id": "trace-1"}]},
    )
    monkeypatch.setattr(
        "services.core.list_recent_plans",
        lambda limit=6: {"plans": [{"trace_id": "trace-plan-1"}]},
    )
    monkeypatch.setattr(
        "services.core.list_recent_governance_decisions",
        lambda limit=8: {"governance": [{"trace_id": "trace-1", "effect": "allow"}]},
    )
    monkeypatch.setattr(
        "services.core.get_governance_state",
        lambda: {"engine": "PolicyEngine", "registry": "PolicyRegistry", "policy_path": None},
    )

    request = types.SimpleNamespace(headers={})
    payload = asyncio.run(gateway.control_plane_overview(request))

    assert payload["summary"]["agent_count"] == 1
    assert payload["summary"]["pending_approvals"] == 1
    assert payload["recent_governance"][0]["effect"] == "allow"
    assert payload["system"]["layers"][-1]["name"] == "MCP v2"


def test_control_plane_approve_forwards_to_canonical_core(monkeypatch):
    _install_gateway_dependency_stubs()
    sys.modules.pop("api_gateway.main", None)
    sys.modules.pop("core.logging_utils", None)
    gateway = importlib.import_module("api_gateway.main")
    captured = {}

    def fake_approve(approval_id: str, *, decided_by: str, comment: str | None = None):
        captured["approval_id"] = approval_id
        captured["decided_by"] = decided_by
        captured["comment"] = comment
        return {"approval": {"approval_id": approval_id}, "result": {"status": "completed"}}

    monkeypatch.setattr("services.core.approve_plan_step", fake_approve)

    payload = asyncio.run(
        gateway.control_plane_approve(
            "approval-42",
            gateway.ApprovalDecisionRequest(decided_by="tester", comment="looks good"),
            types.SimpleNamespace(headers={}),
        )
    )

    assert payload["approval"]["approval_id"] == "approval-42"
    assert captured == {
        "approval_id": "approval-42",
        "decided_by": "tester",
        "comment": "looks good",
    }
