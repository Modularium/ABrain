"""Minimal MCP v1 stdio server backed only by the hardened core."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Callable, IO
from uuid import uuid4

from pydantic import ValidationError

from core.models import (
    AdminBotServiceStatusInput,
    AdminBotSystemHealthInput,
    AdminBotSystemStatusInput,
    CoreExecutionError,
    ListAgentsToolInput,
    RequesterIdentity,
    RequesterType,
)

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"

LOGGER = logging.getLogger("abrain.mcp_v1")


@dataclass(frozen=True)
class ExposedTool:
    """Static MCP tool metadata mapped to a canonical core tool."""

    name: str
    description: str
    input_model: type[Any]

    @property
    def input_schema(self) -> dict[str, Any]:
        schema = self.input_model.model_json_schema(by_alias=True)
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        return schema


EXPOSED_TOOLS: dict[str, ExposedTool] = {
    "list_agents": ExposedTool(
        name="list_agents",
        description="List registered agents via the internal registry API.",
        input_model=ListAgentsToolInput,
    ),
    "adminbot_system_status": ExposedTool(
        name="adminbot_system_status",
        description="Get system-level status from AdminBot v2.",
        input_model=AdminBotSystemStatusInput,
    ),
    "adminbot_system_health": ExposedTool(
        name="adminbot_system_health",
        description="Get system-level health from AdminBot v2.",
        input_model=AdminBotSystemHealthInput,
    ),
    "adminbot_service_status": ExposedTool(
        name="adminbot_service_status",
        description="Get validated service status from AdminBot v2.",
        input_model=AdminBotServiceStatusInput,
    ),
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _default_execute_tool(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from services.core import execute_tool

    return execute_tool(*args, **kwargs)


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _jsonrpc_error(
    request_id: Any,
    code: int,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": error}


def _output_summary(output: Any) -> dict[str, Any]:
    if isinstance(output, dict):
        return {"output_type": "dict", "output_keys": sorted(output.keys())}
    return {"output_type": type(output).__name__}


def _log_event(
    level: int,
    *,
    event: str,
    tool_name: str | None = None,
    correlation_id: str | None = None,
    status: str,
    error_code: str | None = None,
    output: Any | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": event,
        "status": status,
    }
    if tool_name is not None:
        payload["tool_name"] = tool_name
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    if error_code is not None:
        payload["error_code"] = error_code
    if output is not None:
        payload.update(_output_summary(output))
    LOGGER.log(level, _json_dumps(payload))


class MCPV1Server:
    """Handle a minimal MCP v1 tool server lifecycle over stdio JSON-RPC."""

    def __init__(
        self,
        *,
        execute_tool: Callable[..., dict[str, Any]] = _default_execute_tool,
    ) -> None:
        self._execute_tool = execute_tool
        self._initialized = False
        self._client_name = "unknown-client"

    def _requester_identity(self) -> RequesterIdentity:
        client_id = self._client_name.strip() or "unknown-client"
        return RequesterIdentity(type=RequesterType.AGENT, id=f"mcp-v1:{client_id}")

    def handle_line(self, raw_line: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            return _jsonrpc_error(
                None,
                -32700,
                "Parse error",
                data={"details": {"message": str(exc)}},
            )
        return self.handle_message(payload)

    def handle_message(self, message: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
        if isinstance(message, list):
            if not message:
                return _jsonrpc_error(None, -32600, "Invalid Request")
            responses = []
            for item in message:
                response = self._handle_single(item)
                if response is not None:
                    responses.append(response)
            return responses or None
        return self._handle_single(message)

    def _handle_single(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return _jsonrpc_error(None, -32600, "Invalid Request")

        if message.get("jsonrpc") != JSONRPC_VERSION:
            return _jsonrpc_error(message.get("id"), -32600, "Invalid Request")

        method = message.get("method")
        if not isinstance(method, str) or not method:
            return _jsonrpc_error(message.get("id"), -32600, "Invalid Request")

        request_id = message.get("id")
        params = message.get("params", {})

        if method == "notifications/initialized":
            self._initialized = True
            return None

        if request_id is None:
            return None

        if method == "initialize":
            return self._handle_initialize(request_id, params)

        if not self._initialized:
            return _jsonrpc_error(request_id, -32002, "Server not initialized")

        if method == "tools/list":
            return self._handle_tools_list(request_id, params)

        if method == "tools/call":
            return self._handle_tools_call(request_id, params)

        return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, request_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")

        client_info = params.get("clientInfo")
        if isinstance(client_info, dict):
            client_name = client_info.get("name")
            if isinstance(client_name, str) and client_name.strip():
                self._client_name = client_name.strip()

        self._initialized = True
        return _jsonrpc_result(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "abrain-mcp-v1",
                    "title": "ABrain MCP v1 Server",
                    "version": "1.0.0",
                },
                "instructions": (
                    "ABrain MCP v1 is a thin interface layer over the canonical "
                    "services/core.py -> dispatcher -> registry -> handlers path. "
                    "Only the fixed allowlisted tools are exposed."
                ),
            },
        )

    def _handle_tools_list(self, request_id: Any, params: Any) -> dict[str, Any]:
        if params is not None and not isinstance(params, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")

        return _jsonrpc_result(
            request_id,
            {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                    }
                    for tool in EXPOSED_TOOLS.values()
                ]
            },
        )

    def _handle_tools_call(self, request_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")

        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not isinstance(tool_name, str) or not tool_name:
            return _jsonrpc_error(request_id, -32602, "Invalid params")
        if not isinstance(arguments, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")
        if tool_name not in EXPOSED_TOOLS:
            return _jsonrpc_error(request_id, -32602, f"Unknown tool: {tool_name}")

        try:
            EXPOSED_TOOLS[tool_name].input_model.model_validate(arguments)
        except ValidationError as exc:
            return _jsonrpc_error(
                request_id,
                -32602,
                f"Invalid arguments for tool: {tool_name}",
                data={"details": {"errors": exc.errors()}},
            )

        correlation_id = f"mcp-v1:{request_id}" if request_id is not None else f"mcp-v1:{uuid4()}"

        try:
            _log_event(
                logging.INFO,
                event="mcp_v1_tool_call",
                tool_name=tool_name,
                correlation_id=correlation_id,
                status="start",
            )
            output = self._execute_tool(
                tool_name,
                arguments,
                requested_by=self._requester_identity(),
                correlation_id=correlation_id,
            )
        except CoreExecutionError as exc:
            error_payload = exc.error.model_dump(mode="json", by_alias=True)
            _log_event(
                logging.WARNING,
                event="mcp_v1_tool_call",
                tool_name=tool_name,
                correlation_id=correlation_id,
                status="error",
                error_code=str(error_payload.get("error_code")),
            )
            return _jsonrpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": _json_dumps(error_payload)}],
                    "isError": True,
                    "structuredContent": error_payload,
                },
            )

        _log_event(
            logging.INFO,
            event="mcp_v1_tool_call",
            tool_name=tool_name,
            correlation_id=correlation_id,
            status="ok",
            output=output,
        )
        result: dict[str, Any] = {
            "content": [{"type": "text", "text": _json_dumps(output)}],
            "isError": False,
        }
        if isinstance(output, dict):
            result["structuredContent"] = output
        return _jsonrpc_result(request_id, result)


def run_stdio_server(
    *,
    input_stream: IO[str] = sys.stdin,
    output_stream: IO[str] = sys.stdout,
) -> None:
    """Run the MCP server over newline-delimited stdio JSON messages."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    server = MCPV1Server()
    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue
        response = server.handle_line(line)
        if response is None:
            continue
        output_stream.write(_json_dumps(response))
        output_stream.write("\n")
        output_stream.flush()


def main() -> None:  # pragma: no cover - entrypoint
    run_stdio_server()


if __name__ == "__main__":  # pragma: no cover - script
    main()
