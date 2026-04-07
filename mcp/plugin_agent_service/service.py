"""Legacy service for historical plugin tooling paths.

Dynamic plugin execution is intentionally disabled. Security-sensitive
integrations must use the fixed dispatcher/registry path under
``services/core.py`` and ``core/tools/*``.
"""

from __future__ import annotations

from typing import Dict


class PluginAgentService:
    """Expose historical plugin metadata without executing tools.

    This service remains outside the hardened core tool surface. Generic tool
    execution stays disabled so that callers cannot bypass the fixed tool
    registry and typed dispatcher.
    """

    def __init__(self, plugin_dir: str = "plugins") -> None:
        self.plugin_dir = plugin_dir

    def execute_tool(
        self, tool_name: str, input: Dict, context: Dict | None = None
    ) -> Dict:
        _ = (tool_name, input, context)
        return {
            "error_code": "legacy_tool_proxy_disabled",
            "message": (
                "Legacy dynamic plugin execution is disabled. "
                "Use the fixed core tool surface instead."
            ),
            "details": {
                "canonical_path": "services.core.execute_tool",
                "legacy_service": "mcp.plugin_agent_service",
            },
        }

    def list_tools(self) -> list[str]:
        return []
