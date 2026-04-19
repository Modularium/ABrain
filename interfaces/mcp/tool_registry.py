"""Static MCP v2 tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .handlers import (
    LABOS_REASONING_HANDLERS,
    ApproveHandler,
    ExplainHandler,
    GetTraceHandler,
    ListPendingApprovalsHandler,
    ListRoutingModelsHandler,
    RejectHandler,
    RunPlanHandler,
    RunTaskHandler,
)


@dataclass(frozen=True)
class ExposedTool:
    """Static MCP tool metadata."""

    name: str
    description: str
    input_model: type[Any]
    handler: Any

    @property
    def input_schema(self) -> dict[str, Any]:
        schema = self.input_model.model_json_schema(by_alias=True)
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        return schema


TOOLS: dict[str, ExposedTool] = {
    RunTaskHandler.name: ExposedTool(
        name=RunTaskHandler.name,
        description=RunTaskHandler.description,
        input_model=RunTaskHandler.input_model,
        handler=RunTaskHandler(),
    ),
    RunPlanHandler.name: ExposedTool(
        name=RunPlanHandler.name,
        description=RunPlanHandler.description,
        input_model=RunPlanHandler.input_model,
        handler=RunPlanHandler(),
    ),
    ApproveHandler.name: ExposedTool(
        name=ApproveHandler.name,
        description=ApproveHandler.description,
        input_model=ApproveHandler.input_model,
        handler=ApproveHandler(),
    ),
    RejectHandler.name: ExposedTool(
        name=RejectHandler.name,
        description=RejectHandler.description,
        input_model=RejectHandler.input_model,
        handler=RejectHandler(),
    ),
    ListPendingApprovalsHandler.name: ExposedTool(
        name=ListPendingApprovalsHandler.name,
        description=ListPendingApprovalsHandler.description,
        input_model=ListPendingApprovalsHandler.input_model,
        handler=ListPendingApprovalsHandler(),
    ),
    GetTraceHandler.name: ExposedTool(
        name=GetTraceHandler.name,
        description=GetTraceHandler.description,
        input_model=GetTraceHandler.input_model,
        handler=GetTraceHandler(),
    ),
    ExplainHandler.name: ExposedTool(
        name=ExplainHandler.name,
        description=ExplainHandler.description,
        input_model=ExplainHandler.input_model,
        handler=ExplainHandler(),
    ),
    ListRoutingModelsHandler.name: ExposedTool(
        name=ListRoutingModelsHandler.name,
        description=ListRoutingModelsHandler.description,
        input_model=ListRoutingModelsHandler.input_model,
        handler=ListRoutingModelsHandler(),
    ),
    **{
        _cls.name: ExposedTool(
            name=_cls.name,
            description=_cls.description,
            input_model=_cls.input_model,
            handler=_cls(),
        )
        for _cls in LABOS_REASONING_HANDLERS
    },
}

__all__ = ["ExposedTool", "TOOLS"]
