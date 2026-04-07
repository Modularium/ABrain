"""Fixed tool definitions for the stabilized execution layer."""

from .registry import ToolDefinition, ToolRegistry

def build_default_registry(*args, **kwargs):  # pragma: no cover - thin lazy wrapper
    """Import the default registry lazily to avoid fragile package init ordering."""
    from .handlers import build_default_registry as _build_default_registry

    return _build_default_registry(*args, **kwargs)

__all__ = ["ToolDefinition", "ToolRegistry", "build_default_registry"]
