import json
import socket
from pathlib import Path
from uuid import uuid4

import pytest


SOCKET_PATH = Path("/run/adminbot/adminbot.sock")
TIMEOUT_SECONDS = 5.0

pytestmark = pytest.mark.integration


def _encode_frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(4, byteorder="big", signed=False) + payload


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    remaining = size
    chunks: list[bytes] = []

    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError(
                f"AdminBot closed the socket before {size} bytes were received"
            )
        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def _call_adminbot_system_status() -> tuple[bytes, dict[str, object]]:
    request = {
        "version": 1,
        "request_id": str(uuid4()),
        "correlation_id": "adminbot-v2-real-test-correlation",
        "tool_name": "adminbot_system_status",
        "agent_run_id": "adminbot-v2-real-test-run",
        "action": "system.status",
        "requested_by": {
            "type": "agent",
            "id": "agentnn-adminbot-real-test",
        },
        "params": {},
        "dry_run": False,
        "timeout_ms": int(TIMEOUT_SECONDS * 1000),
    }
    request_bytes = json.dumps(request, separators=(",", ":")).encode("utf-8")

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(TIMEOUT_SECONDS)
            sock.connect(str(SOCKET_PATH))
            sock.sendall(_encode_frame(request_bytes))

            response_length_bytes = _recv_exact(sock, 4)
            response_length = int.from_bytes(
                response_length_bytes, byteorder="big", signed=False
            )
            response_payload = _recv_exact(sock, response_length)
    except FileNotFoundError as exc:
        pytest.skip(f"AdminBot v2 socket not found: {SOCKET_PATH}")
    except (socket.timeout, TimeoutError) as exc:
        pytest.fail(f"AdminBot v2 request timed out via {SOCKET_PATH}: {exc}")
    except OSError as exc:
        pytest.fail(f"AdminBot v2 Unix-socket request failed via {SOCKET_PATH}: {exc}")

    try:
        parsed = json.loads(response_payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        pytest.fail(
            "AdminBot v2 returned non-UTF-8 payload.\n"
            f"raw response bytes: {response_payload!r}\n"
            f"decode error: {exc}"
        )
    except json.JSONDecodeError as exc:
        pytest.fail(
            "AdminBot v2 returned invalid JSON.\n"
            f"raw response bytes: {response_payload!r}\n"
            f"raw response text: {response_payload.decode('utf-8', errors='replace')}\n"
            f"json error: {exc}"
        )

    return response_payload, parsed


def test_adminbot_v2_real_system_status():
    if not SOCKET_PATH.exists():
        pytest.skip(f"AdminBot v2 socket not available: {SOCKET_PATH}")

    raw_response, parsed_response = _call_adminbot_system_status()
    raw_text = raw_response.decode("utf-8", errors="replace")

    print(f"raw response: {raw_text}")
    print("parsed response:")
    print(json.dumps(parsed_response, indent=2, sort_keys=True))

    request_id = parsed_response.get("request_id")
    status = parsed_response.get("status")

    if not isinstance(request_id, str) or not request_id:
        pytest.fail(
            "AdminBot v2 response misses request_id.\n"
            f"raw response: {raw_text}\n"
            f"parsed response: {json.dumps(parsed_response, indent=2, sort_keys=True)}"
        )

    if not isinstance(status, str) or not status:
        pytest.fail(
            "AdminBot v2 response misses status.\n"
            f"raw response: {raw_text}\n"
            f"parsed response: {json.dumps(parsed_response, indent=2, sort_keys=True)}"
        )

    if status == "error":
        error = parsed_response.get("error")
        pytest.fail(
            "AdminBot v2 returned an application error for system.status.\n"
            f"raw response: {raw_text}\n"
            f"error object: {json.dumps(error, indent=2, sort_keys=True) if isinstance(error, dict) else error}\n"
            f"parsed response: {json.dumps(parsed_response, indent=2, sort_keys=True)}"
        )

    assert status != "error"
