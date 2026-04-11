"""Thin MCP v2 interface over the canonical ABrain core."""

from .server import MCPV2Server, main, run_stdio_server

__all__ = ["MCPV2Server", "main", "run_stdio_server"]
