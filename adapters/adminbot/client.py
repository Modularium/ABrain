"""Unix-domain-socket client for the AdminBot v2 adapter."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass

from pydantic import ValidationError

from core.models.adminbot import (
    AdminBotErrorResponse,
    AdminBotRequestEnvelope,
    AdminBotSuccessPayload,
)
from core.models.errors import CoreExecutionError, StructuredError


@dataclass(frozen=True)
class AdminBotClientConfig:
    """Runtime configuration for the AdminBot IPC client."""

    socket_path: str = "/run/adminbot/adminbot.sock"
    timeout_seconds: float = 5.0
    adapter_id: str = "agentnn-adminbot-adapter"


class AdminBotTransport:
    """Transport implementation for AdminBot v2 length-prefixed IPC."""

    def __init__(self, config: AdminBotClientConfig) -> None:
        self.config = config

    def send(self, payload: bytes) -> bytes:
        """Send a framed payload and return one framed response."""
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.config.timeout_seconds)
                sock.connect(self.config.socket_path)
                sock.sendall(payload)
                length_prefix = self._recv_exact(sock, 4)
                response_length = int.from_bytes(length_prefix, byteorder="big", signed=False)
                response_payload = self._recv_exact(sock, response_length)
        except socket.timeout as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_TIMEOUT",
                    message="AdminBot IPC request timed out",
                    details={"socket_path": self.config.socket_path},
                )
            ) from exc
        except FileNotFoundError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_UNAVAILABLE",
                    message="AdminBot socket not found",
                    details={"socket_path": self.config.socket_path},
                )
            ) from exc
        except OSError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_UNAVAILABLE",
                    message="AdminBot IPC connection failed",
                    details={
                        "socket_path": self.config.socket_path,
                        "os_error": str(exc),
                    },
                )
            ) from exc
        return length_prefix + response_payload

    def _recv_exact(self, sock: socket.socket, size: int) -> bytes:
        """Read exactly ``size`` bytes or raise a protocol error."""
        remaining = size
        chunks: list[bytes] = []

        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                raise CoreExecutionError(
                    StructuredError(
                        error_code="ADMINBOT_PROTOCOL_ERROR",
                        message="Truncated response from AdminBot",
                        details={"socket_path": self.config.socket_path},
                    )
                )
            chunks.append(chunk)
            remaining -= len(chunk)

        return b"".join(chunks)


class AdminBotClient:
    """Strict request/response client for AdminBot."""

    def __init__(
        self,
        config: AdminBotClientConfig | None = None,
        transport: AdminBotTransport | None = None,
    ) -> None:
        self.config = config or AdminBotClientConfig()
        self.transport = transport or AdminBotTransport(self.config)

    def send_request(self, envelope: AdminBotRequestEnvelope) -> dict[str, object]:
        """Send one strict AdminBot request and return the decoded v2 response."""
        raw_request = envelope.model_dump(mode="json")

        try:
            request_bytes = json.dumps(raw_request, separators=(",", ":")).encode("utf-8")
            raw_response = self._decode_frame(self.transport.send(self._encode_frame(request_bytes)))
            response = json.loads(raw_response.decode("utf-8"))
        except CoreExecutionError:
            raise
        except socket.timeout as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_TIMEOUT",
                    message="AdminBot IPC request timed out",
                    details={"socket_path": self.config.socket_path},
                )
            ) from exc
        except FileNotFoundError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_UNAVAILABLE",
                    message="AdminBot socket not found",
                    details={"socket_path": self.config.socket_path},
                )
            ) from exc
        except OSError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_UNAVAILABLE",
                    message="AdminBot IPC connection failed",
                    details={
                        "socket_path": self.config.socket_path,
                        "os_error": str(exc),
                    },
                )
            ) from exc
        except json.JSONDecodeError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Invalid JSON response from AdminBot",
                )
            ) from exc
        except UnicodeDecodeError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Invalid text response from AdminBot",
                )
            ) from exc

        if not isinstance(response, dict):
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Unexpected non-object response from AdminBot",
                    details={"response": response},
                    tool_name=envelope.tool_name,
                    run_id=envelope.agent_run_id,
                    correlation_id=envelope.correlation_id,
                )
            )

        if response.get("status") == "error":
            try:
                error_response = AdminBotErrorResponse.model_validate(response)
            except ValidationError as exc:
                raise CoreExecutionError(
                    StructuredError(
                        error_code="ADMINBOT_PROTOCOL_ERROR",
                        message="Invalid AdminBot error response structure",
                        details={"response": response},
                        tool_name=envelope.tool_name,
                        run_id=envelope.agent_run_id,
                        correlation_id=envelope.correlation_id,
                    )
                ) from exc
            details = dict(error_response.error.details or {})
            if error_response.request_id is not None:
                details.setdefault("request_id", error_response.request_id)
            details.setdefault("status", error_response.status)
            if error_response.error.retryable is not None:
                details.setdefault("retryable", error_response.error.retryable)

            raise CoreExecutionError(
                StructuredError(
                    error_code=error_response.error.code,
                    message=error_response.error.message,
                    tool_name=envelope.tool_name,
                    details=details,
                    run_id=envelope.agent_run_id,
                    correlation_id=envelope.correlation_id,
                )
            )

        if not isinstance(response.get("status"), str):
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Missing or invalid status in AdminBot response",
                    details={"response": response},
                    tool_name=envelope.tool_name,
                    run_id=envelope.agent_run_id,
                    correlation_id=envelope.correlation_id,
                )
            )

        try:
            success = AdminBotSuccessPayload.model_validate(response)
        except ValidationError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Invalid AdminBot success response structure",
                    details={"response": response},
                    tool_name=envelope.tool_name,
                    run_id=envelope.agent_run_id,
                    correlation_id=envelope.correlation_id,
                )
            ) from exc
        return success.model_dump(mode="json")

        raise CoreExecutionError(
            StructuredError(
                error_code="ADMINBOT_PROTOCOL_ERROR",
                message="Unexpected response structure from AdminBot",
                details={"response": response},
                tool_name=envelope.tool_name,
                run_id=envelope.agent_run_id,
                correlation_id=envelope.correlation_id,
            )
        )

    @staticmethod
    def _encode_frame(payload: bytes) -> bytes:
        """Encode one AdminBot v2 frame."""
        return len(payload).to_bytes(4, byteorder="big", signed=False) + payload

    @staticmethod
    def _decode_frame(frame: bytes) -> bytes:
        """Decode one AdminBot v2 frame payload."""
        if len(frame) < 4:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Incomplete framed response from AdminBot",
                )
            )

        expected_length = int.from_bytes(frame[:4], byteorder="big", signed=False)
        payload = frame[4:]
        if len(payload) != expected_length:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Mismatched AdminBot frame length",
                    details={
                        "expected_length": expected_length,
                        "actual_length": len(payload),
                    },
                )
            )
        return payload
