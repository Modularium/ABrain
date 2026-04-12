from __future__ import annotations

import os
import sys
from datetime import datetime
from importlib import metadata
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

try:
    dist_path = metadata.distribution("mcp").locate_file("mcp")
    sys.path.insert(0, str(dist_path.parent))
    from mcp.types import BaseModel, Field

    sys.path.pop(0)
except Exception:  # fallback to local pydantic
    from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AccessLevel(str, Enum):
    """Access classification for text fields."""

    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class AccessText(BaseModel):
    """Text content tagged with an access level and permissions."""

    text: str
    access: AccessLevel = AccessLevel.PUBLIC
    permissions: list[str] = Field(default_factory=list)


class AgentRunContext(BaseModel):
    """Result information for a single agent run."""

    agent_id: str
    role: str | None = None
    url: str | None = None
    result: Any | None = None
    subtask_result: Any | None = None
    metrics: Optional[Dict[str, float]] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    voted_by: List[str] = []
    priority: int | None = None
    exclusive: bool = False


class ModelContext(BaseModel):
    """Context information for a model invocation."""

    uuid: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task: Optional[str] = None
    task_context: "TaskContext | None" = None
    agent_selection: Optional[str] = None
    result: Optional[Any] = None
    metrics: Optional[Dict[str, float]] = None
    audit_trace: List[str] = []
    agents: List["AgentRunContext"] = []
    elevated_roles: List[str] = []
    memory: Optional[List[AccessText]] = None
    aggregated_result: Optional[Any] = None
    task_value: Optional[float] = None
    max_tokens: Optional[int] = None
    token_spent: int = 0
    applied_limits: Dict[str, Any] = Field(default_factory=dict)
    warning: Optional[str] = None
    required_skills: List[str] | None = None
    enforce_certification: bool = False
    require_endorsement: bool = False
    signed_by: Optional[str] = None
    signature: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[int] = None
    submitted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    dispatch_state: Literal["queued", "running", "expired", "completed"] = "queued"
    mission_id: str | None = None
    mission_step: int | None = None
    mission_role: str | None = None
    delegate_info: Dict[str, Any] | None = None


class TaskContext(BaseModel):
    """Description and payload for an incoming task."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str
    description: Optional[AccessText] = None
    input_data: Optional[AccessText] = None
    preferences: Optional[Dict[str, Any]] = None

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v: Any) -> Any:
        if isinstance(v, str):
            return AccessText(text=v)
        if isinstance(v, dict) and "text" in v:
            return AccessText(
                text=v.get("text", ""),
                access=AccessLevel(v.get("access", "public")),
                permissions=v.get("permissions", []),
            )
        return v

    @field_validator("input_data", mode="before")
    @classmethod
    def validate_input(cls, v: Any) -> Any:
        limit = int(os.getenv("INPUT_LIMIT_BYTES", "4096"))
        if isinstance(v, str):
            text = v
            if len(text) > limit:
                raise ValueError("text too long")
            return AccessText(text=text)
        if isinstance(v, dict) and "text" in v:
            text = v.get("text", "")
            if len(text) > limit:
                raise ValueError("text too long")
            return AccessText(
                text=text,
                access=AccessLevel(v.get("access", "public")),
                permissions=v.get("permissions", []),
            )
        return v


ModelContext.model_rebuild()
AgentRunContext.model_rebuild()
