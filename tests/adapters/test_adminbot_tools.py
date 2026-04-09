import pytest
from uuid import UUID

from adapters.adminbot.client import AdminBotClientConfig
from adapters.adminbot.service import AdminBotService
from core.execution import ExecutionDispatcher
from core.models import (
    AdminBotServiceStatusInput,
    AdminBotSystemHealthInput,
    AdminBotSystemStatusInput,
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
        self.response = {"request_id": "req-1", "status": "ok", "result": {"status": "ok"}}

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


def test_adminbot_system_status_maps_exact_action():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)

    result = service.system_status(
        _tool_request("adminbot_system_status", {}),
        AdminBotSystemStatusInput(),
    )

    assert result["status"] == "ok"
    assert fake_client.last_envelope.action == "system.status"
    assert fake_client.last_envelope.tool_name == "adminbot_system_status"
    assert fake_client.last_envelope.requested_by.type == "agent"
    assert fake_client.last_envelope.requested_by.id == "agentnn-adminbot-adapter"
    assert fake_client.last_envelope.agent_run_id == "run-123"
    assert fake_client.last_envelope.correlation_id == "corr-456"
    assert fake_client.last_envelope.params == {}
    assert fake_client.last_envelope.timeout_ms == 5000
    UUID(fake_client.last_envelope.request_id)


def test_adminbot_service_overrides_user_requested_by_identity():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)
    human_request = ToolExecutionRequest.from_raw(
        tool_name="adminbot_system_status",
        payload={},
        requested_by=RequesterIdentity(type=RequesterType.HUMAN, id="human-42"),
        run_id="run-human",
        correlation_id="corr-human",
    )

    service.system_status(human_request, AdminBotSystemStatusInput())

    assert fake_client.last_envelope.requested_by.type == "agent"
    assert fake_client.last_envelope.requested_by.id == "agentnn-adminbot-adapter"
    assert fake_client.last_envelope.agent_run_id == "run-human"
    assert fake_client.last_envelope.correlation_id == "corr-human"


def test_adminbot_system_health_maps_exact_action():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)

    service.system_health(
        _tool_request("adminbot_system_health", {}),
        AdminBotSystemHealthInput(),
    )

    assert fake_client.last_envelope.action == "system.health"
    assert fake_client.last_envelope.tool_name == "adminbot_system_health"
    assert fake_client.last_envelope.params == {}


def test_adminbot_service_status_maps_exact_action():
    fake_client = FakeAdminBotClient()
    service = AdminBotService(client=fake_client)

    service.service_status(
        _tool_request("adminbot_service_status", {"service_name": "ssh.service"}),
        AdminBotServiceStatusInput(service_name="ssh.service"),
    )

    assert fake_client.last_envelope.action == "service.status"
    assert fake_client.last_envelope.tool_name == "adminbot_service_status"
    assert fake_client.last_envelope.params["service_name"] == "ssh.service"
    assert "allow_nonsystem" not in fake_client.last_envelope.params


def test_dispatcher_rejects_unimplemented_adminbot_tool():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(
            _tool_request("adminbot_service_restart", {"service_name": "ssh.service"})
        )

    assert exc_info.value.error.error_code.value == "unknown_tool"


def test_dispatcher_rejects_legacy_adminbot_tool_names():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(_tool_request("adminbot_get_status", {}))

    assert exc_info.value.error.error_code.value == "unknown_tool"


def test_registry_contains_only_allowed_adminbot_tools():
    registry = build_default_registry(client_factory=lambda: None)

    adminbot_tools = [tool_name for tool_name in registry.list_tools() if tool_name.startswith("adminbot_")]

    assert adminbot_tools == [
        "adminbot_service_status",
        "adminbot_system_health",
        "adminbot_system_status",
    ]


def test_dispatcher_rejects_invalid_adminbot_inputs():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(
            _tool_request(
                "adminbot_service_status",
                {"service_name": "ssh.service;rm -rf /"},
            )
        )

    assert exc_info.value.error.error_code.value == "validation_error"


def test_dispatcher_rejects_action_injection():
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(
            _tool_request(
                "adminbot_system_status",
                {"action": "service.restart"},
            )
        )

    assert exc_info.value.error.error_code.value == "validation_error"


def test_dispatcher_executes_adminbot_tool_via_fixed_handler(monkeypatch):
    fake_client = FakeAdminBotClient()
    monkeypatch.setattr(handlers_module, "_adminbot_service", AdminBotService(client=fake_client))
    dispatcher = ExecutionDispatcher(build_default_registry(client_factory=lambda: None))

    result = dispatcher.execute_sync(
        _tool_request("adminbot_system_status", {})
    )

    assert result.output["status"] == "ok"
    assert fake_client.last_envelope.action == "system.status"
