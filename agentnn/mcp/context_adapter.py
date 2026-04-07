"""Utility functions to convert between ABrain ``ModelContext`` objects and
Model Context Protocol (MCP) compatible dictionaries."""

from __future__ import annotations

from core.model_context import ModelContext


def to_mcp(ctx: ModelContext) -> dict:
    """Return a plain dictionary representation for MCP payloads."""
    return ctx.model_dump(mode="json", exclude_none=True)


def from_mcp(data: dict | ModelContext) -> ModelContext:
    """Create a :class:`ModelContext` instance from MCP payload data."""
    if isinstance(data, ModelContext):
        return data
    return ModelContext.model_validate(data)
