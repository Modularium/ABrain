"""ABrain MCP v1 interface layer."""

from __future__ import annotations

__all__ = ["MCPV1Server", "run_stdio_server"]


def __getattr__(name: str):
    if name in __all__:
        from .server import MCPV1Server, run_stdio_server

        exports = {
            "MCPV1Server": MCPV1Server,
            "run_stdio_server": run_stdio_server,
        }
        return exports[name]
    raise AttributeError(name)
