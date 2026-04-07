import socket

import pytest

from adapters.adminbot.client import AdminBotClient, AdminBotClientConfig
from core.models import AdminBotRequestEnvelope, CoreExecutionError

pytestmark = pytest.mark.unit


class FakeTransport:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.payload = None

    def send(self, payload: bytes) -> bytes:
        self.payload = payload
        if self.exc is not None:
            raise self.exc
        return self.response


def _envelope() -> AdminBotRequestEnvelope:
    return AdminBotRequestEnvelope(
        action="get_health",
        requested_by={"type": "agent", "id": "agentnn-adminbot-adapter"},
        payload={"include_checks": True},
        run_id="run-1",
        correlation_id="corr-1",
    )


def test_adminbot_client_preserves_denial_semantics():
    transport = FakeTransport(
        response=(
            b'{"error_code":"ADMINBOT_DENIED","message":"Denied","details":{"reason":"policy"},'
            b'"audit_ref":"audit-7","warnings":["logged"]}\n'
        )
    )
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    with pytest.raises(CoreExecutionError) as exc_info:
        client.send_request(_envelope())

    assert exc_info.value.error.error_code == "ADMINBOT_DENIED"
    assert exc_info.value.error.message == "Denied"
    assert exc_info.value.error.details == {"reason": "policy"}
    assert exc_info.value.error.audit_ref == "audit-7"
    assert exc_info.value.error.warnings == ["logged"]


def test_adminbot_client_maps_transport_timeout():
    transport = FakeTransport(exc=socket.timeout())
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    with pytest.raises(CoreExecutionError) as exc_info:
        client.send_request(_envelope())

    assert exc_info.value.error.error_code == "ADMINBOT_TIMEOUT"
    assert exc_info.value.error.details["socket_path"] == "/tmp/adminbot.sock"


def test_adminbot_client_rejects_unexpected_protocol_payload():
    transport = FakeTransport(response=b'{"status":"unknown"}\n')
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    with pytest.raises(CoreExecutionError) as exc_info:
        client.send_request(_envelope())

    assert exc_info.value.error.error_code == "ADMINBOT_PROTOCOL_ERROR"
    assert "response" in exc_info.value.error.details
