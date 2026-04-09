"""Planner that maps task input to required canonical capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.model_context import ModelContext, TaskContext

from .capabilities import CapabilityRisk
from .task_intent import PlannerResult, TaskIntent

_PLANNER_RULES: dict[str, dict[str, Any]] = {
    "code_refactor": {
        "domain": "code",
        "risk": CapabilityRisk.MEDIUM,
        "required_capabilities": ["analysis.code", "code.refactor"],
    },
    "code_review": {
        "domain": "code",
        "risk": CapabilityRisk.MEDIUM,
        "required_capabilities": ["analysis.code", "review.code"],
    },
    "system_health": {
        "domain": "system",
        "risk": CapabilityRisk.LOW,
        "required_capabilities": ["system.read", "system.health"],
    },
    "system_status": {
        "domain": "system",
        "risk": CapabilityRisk.LOW,
        "required_capabilities": ["system.read", "system.status"],
    },
    "service_status": {
        "domain": "system",
        "risk": CapabilityRisk.LOW,
        "required_capabilities": ["system.read", "service.status"],
    },
    "list_agents": {
        "domain": "registry",
        "risk": CapabilityRisk.LOW,
        "required_capabilities": ["registry.read"],
    },
    "agent_selection": {
        "domain": "decision",
        "risk": CapabilityRisk.LOW,
        "required_capabilities": ["analysis.general", "routing.agent"],
    },
}

_DOMAIN_FALLBACKS: dict[str, list[str]] = {
    "code": ["analysis.code"],
    "system": ["system.read"],
    "registry": ["registry.read"],
    "decision": ["analysis.general", "routing.agent"],
}


class Planner:
    """Rule-based V1 planner for required capabilities."""

    def __init__(self, rules: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self._rules = {**_PLANNER_RULES, **(dict(rules or {}))}

    def plan(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> PlannerResult:
        """Normalize task input and return a structured intent."""
        normalized = self._normalize_task(task)
        task_type = normalized["task_type"]
        rule = dict(self._rules.get(task_type, {}))
        domain = str(
            normalized["preferences"].get("domain")
            or rule.get("domain")
            or self._infer_domain(task_type)
        )
        required_capabilities = self._merge_required_capabilities(
            rule.get("required_capabilities", []),
            normalized["preferences"].get("required_capabilities", []),
            _DOMAIN_FALLBACKS.get(domain, ["analysis.general"]),
        )
        risk = normalized["preferences"].get("risk") or rule.get("risk") or CapabilityRisk.MEDIUM
        execution_hints = {
            **(rule.get("execution_hints") or {}),
            **(
                normalized["preferences"].get("execution_hints")
                if isinstance(normalized["preferences"].get("execution_hints"), dict)
                else {}
            ),
        }
        intent = TaskIntent(
            task_type=task_type,
            domain=domain,
            risk=risk,
            required_capabilities=required_capabilities,
            execution_hints=execution_hints,
            description=normalized["description"],
        )
        diagnostics = {
            "planner_version": "v1",
            "rule_applied": task_type if task_type in self._rules else None,
            "domain_fallback": task_type not in self._rules,
        }
        return PlannerResult(
            intent=intent,
            normalized_task=normalized,
            diagnostics=diagnostics,
        )

    def _normalize_task(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(task, ModelContext):
            task_context = task.task_context or TaskContext(task_type=task.task or "analysis")
            return self._normalize_task(task_context)
        if isinstance(task, TaskContext):
            return {
                "task_type": task.task_type,
                "description": getattr(task.description, "text", None),
                "preferences": dict(task.preferences or {}),
            }
        if isinstance(task, Mapping):
            preferences = task.get("preferences", {})
            return {
                "task_type": str(task.get("task_type") or task.get("task") or "analysis").strip(),
                "description": str(task.get("description") or "").strip() or None,
                "preferences": dict(preferences) if isinstance(preferences, Mapping) else {},
            }
        raise TypeError(f"Unsupported task input for Planner: {type(task)!r}")

    def _merge_required_capabilities(self, *capability_lists: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for values in capability_lists:
            for value in values:
                normalized = value.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged.append(normalized)
        return merged

    def _infer_domain(self, task_type: str) -> str:
        if task_type.startswith("system_") or task_type.startswith("service_"):
            return "system"
        if task_type.startswith("code_"):
            return "code"
        if task_type.startswith("list_"):
            return "registry"
        return "analysis"
