"""Flowise runtime bridge for ABrain."""

from __future__ import annotations

import httpx
from fastapi import Body, APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Any, Dict, Optional

from utils.logging_util import LoggerMixin


class RunTaskRequest(BaseModel):
    """Request model for run_task."""

    description: str
    domain: Optional[str] = None


class FlowiseBridge(LoggerMixin):
    """Router to map Flowise nodes to ABrain API calls."""

    def __init__(self, api_base: str = "http://localhost:8000/api/v2") -> None:
        super().__init__()
        self.api_base = api_base.rstrip("/")
        self.router = APIRouter(prefix="/flowise", tags=["flowise"])
        self._register_routes()

    async def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.api_base}{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.request(method, url, json=payload)
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, resp.text)
        try:
            return resp.json()
        except Exception:  # pragma: no cover - non-json response
            return {"detail": resp.text}

    def _register_routes(self) -> None:
        @self.router.post("/run_task")
        async def run_task(req: RunTaskRequest = Body(...)) -> Dict[str, Any]:
            try:
                result = await self._request(
                    "POST",
                    "/tasks",
                    {"description": req.description, "domain": req.domain},
                )
                return {"result": result}
            except Exception as exc:  # pragma: no cover - network errors
                self.log_error(exc, req.dict())
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))

        @self.router.get("/status/{task_id}")
        async def get_status(task_id: str) -> Dict[str, Any]:
            try:
                return await self._request("GET", f"/tasks/{task_id}")
            except Exception as exc:  # pragma: no cover - network errors
                self.log_error(exc, {"task_id": task_id})
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))

        @self.router.get("/agents")
        async def list_agents() -> Dict[str, Any]:
            try:
                return await self._request("GET", "/agents")
            except Exception as exc:  # pragma: no cover - network errors
                self.log_error(exc)
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))

        @self.router.get("/agents/{agent_id}")
        async def get_agent(agent_id: str) -> Dict[str, Any]:
            try:
                return await self._request("GET", f"/agents/{agent_id}")
            except Exception as exc:  # pragma: no cover - network errors
                self.log_error(exc, {"agent_id": agent_id})
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
