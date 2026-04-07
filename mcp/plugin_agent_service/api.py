from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from .service import PluginAgentService

router = APIRouter()
service = PluginAgentService()


class ToolRequest(BaseModel):
    tool_name: str
    input: dict
    context: dict | None = None


@router.post("/execute_tool")
async def execute_tool(req: ToolRequest) -> dict:
    result = service.execute_tool(req.tool_name, req.input, req.context)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=result,
    )


@router.get("/tools")
async def list_tools() -> list[str]:
    return service.list_tools()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
