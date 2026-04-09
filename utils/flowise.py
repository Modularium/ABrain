"""Legacy utility wrapper for Flowise compatibility."""

from __future__ import annotations

from typing import Any, Dict

from adapters.flowise.exporter import export_legacy_agent_config_to_flowise


def agent_config_to_flowise(config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a legacy config dict using the canonical descriptor/export path."""
    return export_legacy_agent_config_to_flowise(config)
