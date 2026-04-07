import pytest

from adapters.adminbot.client import AdminBotClientConfig
from adapters.adminbot.service import AdminBotService
from core.execution import ExecutionDispatcher
from core.models import (
    AdminBotGetHealthInput,
    AdminBotGetServiceStatusInput,
    AdminBotGetStatusInput,
    CoreExecutionError,
    RequesterIdentity,
    RequesterType,
    ToolExecutionRequest,
)
from core.tools.handlers import build_default_registry
import core.tools.handlers as handlers_module

pytestmark = pytest.mark.unit


class FakeAdminBotClient:
    def __init__(self):
        self.config = AdminBotClientConfig()
        self.last_envelope = None
        self.response = {"ok": True, "result": {"status": "ok"}}

    def send_request(self, envelope):
        self.last_envelope = envelope
        return self.response


def _tool_request(tool_name: str, payload: dict) -> ToolExecutionRequest:
    return ToolExecutionRequest.from_raw(
        tool_name=tool_name,
        payload=payload,
        requested_by=RequesterIdentity(type=RequesterType.AGENT, id="agent-1"),
        run_id="run-123",
        correlation_id="corr-456",
    )


def test_adminbot_get_status_maps_exact_action():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)

    result = service.get_status(
        _tool_request("adminbot_get_status", {"target": "summary"}),
        AdminBotGetStatusInput(),
    )

    assert result["ok"] is True
    assert fake_client.last_envelope.action == "get_status"
    assert fake_client.last_envelope.requested_by.type == "agent"
    assert fake_client.last_envelope.requested_by.id == "agentnn-adminbot-adapter"
    assert fake_client.last_envelope.run_id == "run-123"
    assert fake_client.last_envelope.correlation_id == "corr-456"


def test_adminbot_service_overrides_user_requested_by_identity():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)
    human_request = ToolExecutionRequest.from_raw(
        tool_name="adminbot_get_status",
        payload={"target": "summary"},
        requested_by=RequesterIdentity(type=RequesterType.HUMAN, id="human-42"),
        run_id="run-human",
        correlation_id="corr-human",
    )

    service.get_status(human_request, AdminBotGetStatusInput())

    assert fake_client.last_envelope.requested_by.type == "agent"
    assert fake_client.last_envelope.requested_by.id == "agentnn-adminbot-adapter"
    assert fake_client.last_envelope.run_id == "run-human"
    assert fake_client.last_envelope.correlation_id == "corr-human"


def test_adminbot_get_health_maps_exact_action():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)

    service.get_health(
        _tool_request("adminbot_get_health", {"include_checks": False}),
        AdminBotGetHealthInput(include_checks=False),
    )

    assert fake_client.last_envelope.action == "get_health"
    assert fake_client.last_envelope.payload["include_checks"] is False


def test_adminbot_get_service_status_maps_exact_action():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)

    service.get_service_status(
        _tool_request(
            "adminbot_get_service_status",
            {"service_name": "ssh.service", "allow_nonsystem": False},
        ),
        AdminBotGetServiceStatusInput(service_name="ssh.service"),
    )

    assert fake_client.last_envelope.action == "get_service_status"
    assert fake_client.last_envelope.payload["service_name"] == "ssh.service"
    assert fake_client.last_envelope.payload["allow_nonsystem"] is False


def test_dispatcher_rejects_unimplemented_adminbot_tool():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(
            _tool_request("adminbot_restart_service", {"service_name": "ssh.service"})
        )

    assert exc_info.value.error.error_code.value == "unknown_tool"


def test_registry_contains_only_allowed_adminbot_tools():
    registry = build_default_registry(client_factory=lambda: None)

    adminbot_tools = [tool_name for tool_name in registry.list_tools() if tool_name.startswith("adminbot_")]

    assert adminbot_tools == [
        "adminbot_get_health",
        "adminbot_get_service_status",
        "adminbot_get_status",
    ]


def test_dispatcher_rejects_invalid_adminbot_inputs():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(
            _tool_request(
                "adminbot_get_service_status",
                {"service_name": "ssh.service;rm -rf /", "allow_nonsystem": False},
            )
        )

    assert exc_info.value.error.error_code.value == "validation_error"


def test_dispatcher_rejects_action_injection():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(
            _tool_request(
                "adminbot_get_status",
                {"target": "summary", "action": "restart_service"},
            )
        )

    assert exc_info.value.error.error_code.value == "validation_error"


def test_dispatcher_executes_adminbot_tool_via_fixed_handler(monkeypatch):
    fake_client = FakeAdminBotClient()
    monkeypatch.setattr(handlers_module, "_adminbot_service", AdminBotService(client=fake_client))
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    result = dispatcher.execute_sync(
        _tool_request("adminbot_get_status", {"target": "daemon"})
    )

    assert result.output["ok"] is True
    assert fake_client.last_envelope.action == "get_status"
