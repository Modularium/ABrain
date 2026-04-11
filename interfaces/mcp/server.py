"""Thin MCP v2 stdio server over the canonical ABrain core."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, IO

from pydantic import ValidationError

from .tool_registry import TOOLS

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-06-18"

LOGGER = logging.getLogger("abrain.mcp_v2")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


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


class MCPV2Server:
    """Minimal JSON-RPC 2.0 MCP v2 server."""

    def __init__(self) -> None:
        self._initialized = False
        self._client_name = "unknown-client"

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
                    "name": "abrain-mcp-v2",
                    "title": "ABrain MCP v2 Server",
                    "version": "1.2.0",
                },
                "instructions": (
                    "ABrain MCP v2 is a thin interface layer over services/core.py. "
                    "All calls run through the canonical routing, governance, approval, execution, learning and audit path."
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
                    for tool in TOOLS.values()
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
        exposed = TOOLS.get(tool_name)
        if exposed is None:
            return _jsonrpc_error(request_id, -32602, f"Unknown tool: {tool_name}")

        try:
            structured = exposed.handler.handle(arguments)
        except ValidationError as exc:
            return _jsonrpc_error(
                request_id,
                -32602,
                f"Invalid arguments for tool: {tool_name}",
                data={"details": exc.errors(include_url=False)},
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            LOGGER.exception("mcp_v2_tool_call_failed", extra={"tool_name": tool_name})
            return _jsonrpc_error(
                request_id,
                -32000,
                f"Tool execution failed: {tool_name}",
                data={
                    "details": {
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                },
            )

        return _jsonrpc_result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": _json_dumps(structured),
                    }
                ],
                "isError": bool(structured.get("status") == "error"),
                "structuredContent": structured,
            },
        )


def run_stdio_server(
    *,
    input_stream: IO[str] | None = None,
    output_stream: IO[str] | None = None,
) -> None:
    """Run the MCP v2 stdio loop."""
    server = MCPV2Server()
    source = input_stream or sys.stdin
    sink = output_stream or sys.stdout
    for raw_line in source:
        line = raw_line.strip()
        if not line:
            continue
        response = server.handle_line(line)
        if response is None:
            continue
        if isinstance(response, list):
            sink.write(_json_dumps(response) + "\n")
        else:
            sink.write(_json_dumps(response) + "\n")
        sink.flush()


def main() -> None:
    """Console entry point for the MCP v2 stdio server."""
    run_stdio_server()


if __name__ == "__main__":  # pragma: no cover - script
    main()
