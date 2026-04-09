"""LEGACY (disabled): Smolitux bridge is not part of the canonical runtime."""

from fastapi import APIRouter, HTTPException, WebSocket, status

from utils.logging_util import LoggerMixin


class SmolituxIntegration(LoggerMixin):
    """Expose disabled legacy Smolitux routes for explicit rejection only."""

    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/smolitux", tags=["smolitux"])
        self._register_routes()

    @staticmethod
    def _disabled() -> None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error_code": "legacy_smolitux_disabled",
                "message": (
                    "The legacy Smolitux integration is disabled and not part of the "
                    "canonical ABrain runtime."
                ),
                "details": {
                    "canonical_path": "services/core.py",
                    "legacy_prefix": "/smolitux",
                },
            },
        )

    def _register_routes(self):
        @self.router.post("/tasks")
        async def create_task() -> dict:
            self._disabled()

        @self.router.get("/tasks")
        async def get_tasks() -> dict:
            self._disabled()

        @self.router.get("/tasks/{task_id}")
        async def get_task(task_id: str) -> dict:
            _ = task_id
            self._disabled()

        @self.router.get("/agents")
        async def get_agents() -> dict:
            self._disabled()

        @self.router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.close(code=1008, reason="legacy_smolitux_disabled")
