"""Unix-domain-socket client for the AdminBot adapter."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass

from core.models.adminbot import (
    AdminBotErrorPayload,
    AdminBotRequestEnvelope,
    AdminBotSuccessPayload,
)
from core.models.errors import CoreExecutionError, StructuredError


@dataclass(frozen=True)
class AdminBotClientConfig:
    """Runtime configuration for the AdminBot IPC client."""

    socket_path: str = "/var/run/smolit_adminbot.sock"
    timeout_seconds: float = 5.0
    adapter_id: str = "agentnn-adminbot-adapter"


class AdminBotTransport:
    """Transport implementation for newline-delimited AdminBot IPC."""

    def __init__(self, config: AdminBotClientConfig) -> None:
        self.config = config

    def send(self, payload: bytes) -> bytes:
        """Send a payload and return one newline-delimited response."""
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.config.timeout_seconds)
                sock.connect(self.config.socket_path)
                sock.sendall(payload + b"\n")

                chunks: list[bytes] = []
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if b"\n" in chunk:
                        break
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

        if not chunks:
            raise CoreExecutionError(
                StructuredError(
                    error_code="ADMINBOT_PROTOCOL_ERROR",
                    message="Empty response from AdminBot",
                    details={"socket_path": self.config.socket_path},
                )
            )

        return b"".join(chunks).split(b"\n", 1)[0]


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
        """Send one strict AdminBot request and return the decoded success payload."""
        raw_request = envelope.model_dump(mode="json")

        try:
            raw_response = self.transport.send(json.dumps(raw_request).encode("utf-8"))
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

        if response.get("ok") is True:
            success = AdminBotSuccessPayload.model_validate(response)
            return success.model_dump(mode="json")

        if "error_code" in response and "message" in response:
            error = AdminBotErrorPayload.model_validate(response)
            raise CoreExecutionError(
                StructuredError(
                    error_code=error.error_code,
                    message=error.message,
                    details=error.details or {},
                    audit_ref=error.audit_ref,
                    warnings=error.warnings,
                )
            )

        raise CoreExecutionError(
            StructuredError(
                error_code="ADMINBOT_PROTOCOL_ERROR",
                message="Unexpected response structure from AdminBot",
                details={"response": response},
            )
        )
