"""ABrain V2 Domain Reasoning for LabOS.

Deterministic reasoning over a LabOS context snapshot.  The caller
(e.g. Smolit-AI-Assistant) pulls the snapshot from LabOS via its
MCP server, passes it to ABrain, and receives a structured Response
Shape V2 it can render or forward.  ABrain does not call LabOS,
does not execute LabOS actions, and never invents actions that are
not present in the action catalogue the caller supplies.

Public entry points live on :mod:`services.core` as
``get_labos_<usecase>`` functions and ultimately call into
:mod:`core.reasoning.labos.usecases`.
"""

from .schemas import (
    CapabilityStatus,
    DomainReasoningResponse,
    LabOsActionCatalogEntry,
    LabOsContext,
    LabOsModule,
    LabOsModuleCapability,
    LabOsModuleDependency,
    ModuleAutonomyLevel,
    ModuleDependencyKind,
    PrioritizedEntity,
    RecommendedAction,
    RecommendedCheck,
)
from .usecases import (
    cross_domain_overview,
    incident_review,
    maintenance_suggestions,
    module_capability_risk_review,
    module_coordination_review,
    module_daily_overview,
    module_incident_review,
    reactor_daily_overview,
    robotops_cross_domain_overview,
    schedule_runtime_review,
)

__all__ = [
    "CapabilityStatus",
    "DomainReasoningResponse",
    "LabOsActionCatalogEntry",
    "LabOsContext",
    "LabOsModule",
    "LabOsModuleCapability",
    "LabOsModuleDependency",
    "ModuleAutonomyLevel",
    "ModuleDependencyKind",
    "PrioritizedEntity",
    "RecommendedAction",
    "RecommendedCheck",
    "cross_domain_overview",
    "incident_review",
    "maintenance_suggestions",
    "module_capability_risk_review",
    "module_coordination_review",
    "module_daily_overview",
    "module_incident_review",
    "reactor_daily_overview",
    "robotops_cross_domain_overview",
    "schedule_runtime_review",
]
