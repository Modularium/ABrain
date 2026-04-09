"""CLI wrapper for the ABrain MCP v1 stdio server."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from interfaces.mcp_v1.server import run_stdio_server


def main() -> None:
    run_stdio_server()


if __name__ == "__main__":  # pragma: no cover - script
    main()
