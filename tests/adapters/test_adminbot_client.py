import json
import socket
from uuid import UUID

import pytest

from adapters.adminbot.client import AdminBotClient, AdminBotClientConfig
from core.models import AdminBotRequestEnvelope, CoreExecutionError

pytestmark = pytest.mark.unit


def _frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(4, byteorder="big", signed=False) + payload


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


def _envelope(
    *,
    action: str = "system.health",
    tool_name: str = "adminbot_system_health",
    params: dict[str, object] | None = None,
) -> AdminBotRequestEnvelope:
    return AdminBotRequestEnvelope(
        action=action,
        tool_name=tool_name,
        requested_by={"type": "agent", "id": "abrain-adminbot-adapter"},
        params=params or {},
        agent_run_id="run-1",
        correlation_id="corr-1",
    )


def test_adminbot_client_uses_length_prefixed_framing():
    transport = FakeTransport(
        response=_frame(b'{"request_id":"req-1","status":"ok","result":{"status":"ok"}}')
    )
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    result = client.send_request(
        _envelope(action="system.status", tool_name="adminbot_system_status")
    )

    assert result["status"] == "ok"
    assert result["request_id"] == "req-1"
    assert int.from_bytes(transport.payload[:4], byteorder="big", signed=False) == len(
        transport.payload[4:]
    )
    request_payload = json.loads(transport.payload[4:].decode("utf-8"))
    UUID(request_payload["request_id"])
    assert request_payload["action"] == "system.status"
    assert request_payload["tool_name"] == "adminbot_system_status"
    assert request_payload["agent_run_id"] == "run-1"
    assert request_payload["requested_by"]["type"] == "agent"
    assert request_payload["params"] == {}
    assert request_payload["dry_run"] is False
    assert request_payload["timeout_ms"] == 5000
    assert "payload" not in request_payload


def test_adminbot_client_preserves_denial_semantics():
    transport = FakeTransport(
        response=_frame(
            (
                b'{"request_id":"req-7","status":"error","error":{"code":"ADMINBOT_DENIED",'
                b'"message":"Denied","details":{"reason":"policy"},"retryable":false}}'
            )
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
    assert exc_info.value.error.details["reason"] == "policy"
    assert exc_info.value.error.details["request_id"] == "req-7"
    assert exc_info.value.error.details["status"] == "error"
    assert exc_info.value.error.details["retryable"] is False


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


def test_adminbot_client_maps_transport_unavailable():
    transport = FakeTransport(exc=FileNotFoundError())
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    with pytest.raises(CoreExecutionError) as exc_info:
        client.send_request(_envelope())

    assert exc_info.value.error.error_code == "ADMINBOT_UNAVAILABLE"
    assert exc_info.value.error.details["socket_path"] == "/tmp/adminbot.sock"


def test_adminbot_client_rejects_invalid_frame_length():
    transport = FakeTransport(response=b"\x00\x00\x00\x10{}")
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    with pytest.raises(CoreExecutionError) as exc_info:
        client.send_request(_envelope())

    assert exc_info.value.error.error_code == "ADMINBOT_PROTOCOL_ERROR"
    assert exc_info.value.error.details["expected_length"] == 16
    assert exc_info.value.error.details["actual_length"] == 2


def test_adminbot_client_rejects_missing_status():
    transport = FakeTransport(response=_frame(b'{"request_id":"req-3","result":{}}'))
    client = AdminBotClient(
        config=AdminBotClientConfig(socket_path="/tmp/adminbot.sock"),
        transport=transport,
    )

    with pytest.raises(CoreExecutionError) as exc_info:
        client.send_request(_envelope())

    assert exc_info.value.error.error_code == "ADMINBOT_PROTOCOL_ERROR"
    assert "status" in exc_info.value.error.message.lower()
