"""MCP v2 handlers for trace and explainability retrieval."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TraceLookupParams(BaseModel):
    """Strict MCP input for trace lookup calls."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)

    @field_validator("trace_id")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("trace_id must not be empty")
        return normalized


class GetTraceHandler:
    """Return a persisted trace snapshot."""

    name = "abrain.get_trace"
    description = "Return a stored ABrain trace with spans and explainability payloads."
    input_model = TraceLookupParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import get_trace

        request = self.input_model.model_validate(params)
        return get_trace(request.trace_id)


class ExplainHandler:
    """Return stored explainability records for a trace."""

    name = "abrain.explain"
    description = "Return stored explainability records for a trace."
    input_model = TraceLookupParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import get_explainability

        request = self.input_model.model_validate(params)
        records = get_explainability(request.trace_id)["explainability"]
        summary = _build_summary(records)
        return {
            "trace_id": request.trace_id,
            "explainability": records,
            "explainability_summary": summary,
        }


def _build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    record = records[-1]
    return {
        "selected_agent": record.get("selected_agent_id"),
        "policy_decision": "require_approval" if record.get("approval_required") else "allow",
        "reason": record.get("routing_reason_summary"),
        "matched_policy_ids": record.get("matched_policy_ids", []),
    }
