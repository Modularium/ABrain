"""High level HTTP client for ABrain services."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from core.model_context import ModelContext

from ..config import SDKSettings


class AgentClient:
    """Wrapper for the ABrain REST API."""

    def __init__(self, settings: Optional[SDKSettings] = None) -> None:
        self.settings = settings or SDKSettings.load()
        self._client = httpx.Client(base_url=self.settings.host)

    def _headers(self) -> Dict[str, str]:
        if self.settings.api_token:
            return {"Authorization": f"Bearer {self.settings.api_token}"}
        return {}

    def submit_task(
        self,
        text: str,
        value: float | None = None,
        max_tokens: int | None = None,
        priority: int | None = None,
        deadline: str | None = None,
    ) -> Dict[str, Any]:
        """Submit a task description and return the response."""
        payload: Dict[str, Any] = {"task": text}
        if value is not None:
            payload["task_value"] = value
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if priority is not None:
            payload["priority"] = priority
        if deadline is not None:
            payload["deadline"] = deadline
        resp = self._client.post("/task", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def list_agents(self) -> Dict[str, Any]:
        resp = self._client.get("/agents", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # backwards compatibility helpers
    def get_agents(self) -> Dict[str, Any]:
        """Alias for :meth:`list_agents`."""
        return self.list_agents()

    def list_sessions(self) -> Dict[str, Any]:
        resp = self._client.get("/sessions", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_sessions(self) -> Dict[str, Any]:
        """Alias for :meth:`list_sessions`."""
        return self.list_sessions()

    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        resp = self._client.get(f"/context/{session_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def vector_search(self, query: str, collection: str = "default") -> Dict[str, Any]:
        payload = {"query": query, "collection": collection}
        resp = self._client.post(
            "/vector_search", json=payload, headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def get_embeddings(self, text: str) -> Dict[str, Any]:
        """Return embeddings using the vector store."""
        resp = self._client.post("/embed", json={"text": text}, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_agent_profile(self, name: str) -> Dict[str, Any]:
        resp = self._client.get(f"/agent_profile/{name}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def update_agent_profile(
        self,
        name: str,
        traits: Dict[str, Any] | None = None,
        skills: list[str] | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if traits is not None:
            payload["traits"] = traits
        if skills is not None:
            payload["skills"] = skills
        resp = self._client.post(
            f"/agent_profile/{name}", json=payload, headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def get_agent_status(self, name: str) -> Dict[str, Any]:
        resp = self._client.get(f"/agent_status/{name}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def create_coalition(
        self,
        goal: str,
        leader: str,
        members: list[str] | None = None,
        strategy: str = "plan-then-split",
    ) -> Dict[str, Any]:
        payload = {
            "goal": goal,
            "leader": leader,
            "members": members or [],
            "strategy": strategy,
        }
        resp = self._client.post(
            "/coalition/init", json=payload, headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def assign_subtask(
        self, coalition_id: str, assigned_to: str, title: str
    ) -> Dict[str, Any]:
        payload = {"title": title, "assigned_to": assigned_to}
        resp = self._client.post(
            f"/coalition/{coalition_id}/assign", json=payload, headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def get_coalition(self, coalition_id: str) -> Dict[str, Any]:
        resp = self._client.get(f"/coalition/{coalition_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def dispatch_task(self, context: "ModelContext") -> Dict[str, Any]:
        """Send a ModelContext to the dispatcher."""
        resp = self._client.post(
            "/dispatch", json=context.model_dump(), headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def chat(self, message: str, task_type: str = "dev") -> Dict[str, Any]:
        """High-level helper for simple task dispatch."""
        from ..utils.context_builder import build_context

        ctx = build_context(message)
        ctx.task_context.task_type = task_type
        return self.dispatch_task(ctx)

    def get_models(self) -> Dict[str, Any]:
        resp = self._client.get("/models", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def set_model(self, model_id: str, user_id: str = "default") -> Dict[str, Any]:
        payload = {"user_id": user_id, "model_id": model_id}
        resp = self._client.post("/model", json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def post_feedback(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._client.post(
            f"/session/{session_id}/feedback",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_feedback(self, session_id: str) -> Dict[str, Any]:
        resp = self._client.get(
            f"/session/{session_id}/feedback",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()
