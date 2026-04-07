"""Identity models for tool execution requests."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RequesterType(str, Enum):
    """Supported requester types for execution metadata."""

    AGENT = "agent"
    HUMAN = "human"


class RequesterIdentity(BaseModel):
    """Identify who requested a tool execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: RequesterType
    id: str = Field(min_length=1)
