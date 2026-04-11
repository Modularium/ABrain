"""MCP v2 handlers for approval-aware plan control."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApprovalParams(BaseModel):
    """Strict MCP input for approval decisions."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1, max_length=128)

    @field_validator("approval_id")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("approval_id must not be empty")
        return normalized


class ListPendingApprovalsParams(BaseModel):
    """Strict empty MCP input for listing pending approvals."""

    model_config = ConfigDict(extra="forbid")


class ApproveHandler:
    """Resume a paused plan step after human approval."""

    name = "abrain.approve"
    description = "Approve a pending ABrain approval request and resume the paused plan."
    input_model = ApprovalParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import approve_plan_step

        request = self.input_model.model_validate(params)
        core_result = approve_plan_step(request.approval_id)
        return _normalize_approval_result(core_result)


class RejectHandler:
    """Reject a pending plan step."""

    name = "abrain.reject"
    description = "Reject a pending ABrain approval request and finish the paused plan consistently."
    input_model = ApprovalParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import reject_plan_step

        request = self.input_model.model_validate(params)
        core_result = reject_plan_step(request.approval_id)
        return _normalize_approval_result(core_result)


class ListPendingApprovalsHandler:
    """Return pending approvals in a condensed form."""

    name = "abrain.list_pending_approvals"
    description = "List pending approval requests emitted by the canonical ABrain approval store."
    input_model = ListPendingApprovalsParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import list_pending_approvals

        self.input_model.model_validate(params)
        approvals = list_pending_approvals()["approvals"]
        return {
            "approvals": [
                {
                    "approval_id": item["approval_id"],
                    "step": item["step_id"],
                    "risk": item["risk"],
                    "reason": item["reason"],
                }
                for item in approvals
            ]
        }


def _normalize_approval_result(core_result: dict[str, Any]) -> dict[str, Any]:
    result = dict(core_result.get("result") or {})
    status = str(result.get("status") or "error")
    return {
        "status": "success" if status == "completed" else status,
        "approval": core_result.get("approval"),
        "plan_result": result,
        "trace_id": (core_result.get("trace") or {}).get("trace_id"),
        "warnings": list(result.get("aggregated_warnings") or []),
    }
