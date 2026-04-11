"""CLI wrapper for the ABrain MCP v2 stdio server."""

from __future__ import annotations

from interfaces.mcp.server import run_stdio_server


def main() -> None:
    run_stdio_server()


if __name__ == "__main__":  # pragma: no cover - script
    main()
