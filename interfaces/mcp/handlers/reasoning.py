"""MCP v2 handlers for ABrain V2 LabOS domain reasoning.

One handler instance per use case, all sharing the same canonical
dispatcher :func:`services.core.run_labos_reasoning`.  No reasoning
logic or Response Shape V2 projection lives here — the handler is a
strict-input pass-through that forwards the ``context`` dict to the
service and translates error envelopes to ``status="error"`` so
the MCP server can flip ``isError=true``.

Naming follows ``abrain.reason_labos_<mode>`` — parallel to
``abrain.list_routing_models`` and the other ``abrain.<verb>`` tools.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LabOsReasoningParams(BaseModel):
    """Strict MCP input for all LabOS reasoning tools.

    The concrete per-field validation lives in
    ``core.reasoning.labos.schemas.LabOsContext`` — this wrapper only
    pins that callers pass a single ``context`` object.  Invalid
    contexts surface through the service error envelope, not through
    a second schema here.
    """

    model_config = ConfigDict(extra="forbid")

    context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "LabOS snapshot to reason over. Forwarded verbatim to "
            "services.core.run_labos_reasoning; the reasoner validates "
            "the concrete shape."
        ),
    )


_LABOS_REASONING_TOOL_DESCRIPTIONS: dict[str, str] = {
    "reactor_daily_overview": (
        "Run ABrain V2 LabOS reasoning for the reactor daily overview: "
        "which reactors need attention today and which are nominal. "
        "Input: LabOS context snapshot; output: Response Shape V2."
    ),
    "incident_review": (
        "Run ABrain V2 LabOS reasoning for prioritised review of "
        "open/critical LabOS incidents. Input: LabOS context snapshot; "
        "output: Response Shape V2."
    ),
    "maintenance_suggestions": (
        "Run ABrain V2 LabOS reasoning for overdue and due-soon "
        "maintenance items plus allowed follow-up actions. Input: "
        "LabOS context snapshot; output: Response Shape V2."
    ),
    "schedule_runtime_review": (
        "Run ABrain V2 LabOS reasoning for schedules and commands "
        "that are failing or blocked. Input: LabOS context snapshot; "
        "output: Response Shape V2."
    ),
    "cross_domain_overview": (
        "Run ABrain V2 LabOS reasoning for a combined reactor + "
        "incident + maintenance + schedule focus list. Input: LabOS "
        "context snapshot; output: Response Shape V2."
    ),
    "module_daily_overview": (
        "Run ABrain V2 RobotOps reasoning — which LabOS modules need "
        "attention today, which are offline/disabled, which are nominal. "
        "Input: LabOS context snapshot; output: Response Shape V2."
    ),
    "module_incident_review": (
        "Run ABrain V2 RobotOps reasoning for modules with open incidents "
        "or critical capability impact. Input: LabOS context snapshot; "
        "output: Response Shape V2."
    ),
    "module_coordination_review": (
        "Run ABrain V2 RobotOps reasoning over module dependency edges — "
        "blocked links and upstream-impacted counterparts. Input: LabOS "
        "context snapshot; output: Response Shape V2."
    ),
    "module_capability_risk_review": (
        "Run ABrain V2 RobotOps reasoning for modules with missing or "
        "degraded critical capabilities, plus manual/assisted autonomy "
        "signals. Input: LabOS context snapshot; output: Response Shape V2."
    ),
    "robotops_cross_domain_overview": (
        "Run ABrain V2 combined ReactorOps + RobotOps reasoning — one "
        "prioritised focus list across reactors, modules, incidents, "
        "maintenance, schedules and safety signals. Input: LabOS context "
        "snapshot; output: Response Shape V2."
    ),
}


class _LabOsReasoningHandlerBase:
    """Shared delegate for all five LabOS reasoning tools.

    Concrete handler classes pin ``mode`` and ``name``/``description``
    at class level so the tool registry can construct them exactly like
    the other MCP handlers.
    """

    mode: str = ""  # set in subclass
    name: str = ""
    description: str = ""
    input_model = LabOsReasoningParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import run_labos_reasoning

        request = self.input_model.model_validate(params)
        payload = run_labos_reasoning(self.mode, request.context)
        if "error" in payload:
            return {
                "status": "error",
                "error": payload["error"],
                "detail": payload.get("detail"),
            }
        return {"status": "success", **payload}


def _make_handler_class(mode: str) -> type[_LabOsReasoningHandlerBase]:
    """Build a concrete subclass for one reasoning mode."""
    return type(
        f"ReasonLabos{''.join(part.capitalize() for part in mode.split('_'))}Handler",
        (_LabOsReasoningHandlerBase,),
        {
            "mode": mode,
            "name": f"abrain.reason_labos_{mode}",
            "description": _LABOS_REASONING_TOOL_DESCRIPTIONS[mode],
        },
    )


ReasonLabosReactorDailyOverviewHandler = _make_handler_class("reactor_daily_overview")
ReasonLabosIncidentReviewHandler = _make_handler_class("incident_review")
ReasonLabosMaintenanceSuggestionsHandler = _make_handler_class("maintenance_suggestions")
ReasonLabosScheduleRuntimeReviewHandler = _make_handler_class("schedule_runtime_review")
ReasonLabosCrossDomainOverviewHandler = _make_handler_class("cross_domain_overview")
ReasonLabosModuleDailyOverviewHandler = _make_handler_class("module_daily_overview")
ReasonLabosModuleIncidentReviewHandler = _make_handler_class("module_incident_review")
ReasonLabosModuleCoordinationReviewHandler = _make_handler_class(
    "module_coordination_review"
)
ReasonLabosModuleCapabilityRiskReviewHandler = _make_handler_class(
    "module_capability_risk_review"
)
ReasonLabosRobotopsCrossDomainOverviewHandler = _make_handler_class(
    "robotops_cross_domain_overview"
)


LABOS_REASONING_HANDLERS: tuple[type[_LabOsReasoningHandlerBase], ...] = (
    ReasonLabosReactorDailyOverviewHandler,
    ReasonLabosIncidentReviewHandler,
    ReasonLabosMaintenanceSuggestionsHandler,
    ReasonLabosScheduleRuntimeReviewHandler,
    ReasonLabosCrossDomainOverviewHandler,
    ReasonLabosModuleDailyOverviewHandler,
    ReasonLabosModuleIncidentReviewHandler,
    ReasonLabosModuleCoordinationReviewHandler,
    ReasonLabosModuleCapabilityRiskReviewHandler,
    ReasonLabosRobotopsCrossDomainOverviewHandler,
)


__all__ = [
    "LabOsReasoningParams",
    "LABOS_REASONING_HANDLERS",
    "ReasonLabosReactorDailyOverviewHandler",
    "ReasonLabosIncidentReviewHandler",
    "ReasonLabosMaintenanceSuggestionsHandler",
    "ReasonLabosScheduleRuntimeReviewHandler",
    "ReasonLabosCrossDomainOverviewHandler",
    "ReasonLabosModuleDailyOverviewHandler",
    "ReasonLabosModuleIncidentReviewHandler",
    "ReasonLabosModuleCoordinationReviewHandler",
    "ReasonLabosModuleCapabilityRiskReviewHandler",
    "ReasonLabosRobotopsCrossDomainOverviewHandler",
]
