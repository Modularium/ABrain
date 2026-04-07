"""Fixed tool registry without dynamic loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from core.models.tooling import BaseToolInput

if TYPE_CHECKING:
    from core.models.tooling import ToolExecutionRequest


@dataclass(frozen=True)
class ToolDefinition:
    """Static definition of an executable tool."""

    name: str
    description: str
    input_model: type[BaseToolInput]
    handler: Callable[["ToolExecutionRequest", BaseToolInput], Any]


class ToolRegistry:
    """Registry for fixed internal tool definitions."""

    def __init__(
        self,
        definitions: list[ToolDefinition] | None = None,
        *,
        frozen: bool = False,
    ) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._frozen = False
        for definition in definitions or []:
            self.register(definition)
        if frozen:
            self.freeze()

    def register(self, definition: ToolDefinition) -> None:
        """Register a static tool definition."""
        if self._frozen:
            raise ValueError("Tool registry is frozen")
        if definition.name in self._definitions:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._definitions[definition.name] = definition

    def freeze(self) -> None:
        """Prevent further mutation after static registry assembly."""
        self._frozen = True

    def get(self, tool_name: str) -> ToolDefinition:
        """Return the tool definition for ``tool_name``."""
        if tool_name not in self._definitions:
            raise KeyError(tool_name)
        return self._definitions[tool_name]

    def list_tools(self) -> list[str]:
        """Return registered tool names."""
        return sorted(self._definitions)

    def validate_input(self, tool_name: str, payload: dict[str, Any]) -> BaseToolInput:
        """Validate input payload for a registered tool."""
        definition = self.get(tool_name)
        return definition.input_model.model_validate(payload)
