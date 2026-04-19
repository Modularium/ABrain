"""MCP v2 handler for read-only routing-model catalog inspection.

Thin mirror of :func:`services.core.get_routing_models` — the same
reader consumed by the ``abrain routing models`` CLI (Turn 7 / Turn
16) and the ``/control-plane/routing/models`` HTTP endpoint (Turn
17).  MCP callers get the catalog with quantization / distillation
lineage and per-model ``energy_profile`` without any second
catalog projection.

Error policy
------------
The canonical service returns ``{"error": "invalid_<x>", "detail":
"..."}`` for bad enum values.  This handler forwards that envelope
with ``status="error"`` so the MCP server flips ``isError=true``
on the response — callers can branch on either field.  The
service's happy-path payload is returned verbatim with an added
``status="success"`` marker, same convention as the other MCP
handlers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ListRoutingModelsParams(BaseModel):
    """Strict MCP input for the routing-catalog read.

    All four fields mirror the query params accepted by the canonical
    reader — same names, same defaults.  Empty strings normalise to
    ``None`` so callers can hand through unset optional args without
    triggering the service-side enum validation.
    """

    model_config = ConfigDict(extra="forbid")

    tier: str | None = Field(default=None, max_length=64)
    provider: str | None = Field(default=None, max_length=64)
    purpose: str | None = Field(default=None, max_length=64)
    available_only: bool = Field(default=False)

    @field_validator("tier", "provider", "purpose")
    @classmethod
    def normalize_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ListRoutingModelsHandler:
    """Return the read-only routing-model catalog projection."""

    name = "abrain.list_routing_models"
    description = (
        "List the canonical ABrain routing-model catalog with "
        "quantization, distillation and energy_profile metadata. "
        "Read-only; accepts optional tier / provider / purpose / "
        "available_only filters."
    )
    input_model = ListRoutingModelsParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import get_routing_models

        request = self.input_model.model_validate(params)
        payload = get_routing_models(
            tier=request.tier,
            provider=request.provider,
            purpose=request.purpose,
            available_only=request.available_only,
        )
        if "error" in payload:
            return {
                "status": "error",
                "error": payload["error"],
                "detail": payload.get("detail"),
            }
        return {"status": "success", **payload}
