"""Deterministic strategy engine for the ABrain decision layer.

Fuses :class:`Planner`, :class:`PlanBuilder` and :class:`PolicyEngine`
outputs into one :class:`StrategyDecision`.  The engine is a pure composer:
it does not re-implement planning, policy matching or agent selection.

Decision rules (in order):

1. ``policy.effect == "deny"``            → ``REJECT``              (not allowed)
2. ``policy.effect == "require_approval"``→ ``REQUEST_APPROVAL``    (allowed, approval required)
3. ``policy.effect == "allow"`` and
   ``intent.risk == CapabilityRisk.HIGH`` → ``REQUEST_APPROVAL``    (risk-driven gate)
4. ``policy.effect == "allow"`` and
   ``plan_builder.build(task)`` yields a
   plan with more than one step         → ``PLAN_AND_EXECUTE``
5. otherwise                            → ``DIRECT_EXECUTION``

Rules 1-3 can be evaluated without calling :class:`PlanBuilder`; rule 4 is
the only path that builds a plan, keeping the engine cheap for the common
approval/reject branches.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.governance import PolicyEngine
from core.model_context import ModelContext, TaskContext

from .capabilities import CapabilityRisk
from .plan_builder import PlanBuilder
from .planner import Planner
from .strategy_decision import StrategyChoice, StrategyDecision
from .task_intent import PlannerResult


_HIGH_RISK_CONFIDENCE = 0.85
_PLAN_CONFIDENCE = 0.9
_DIRECT_CONFIDENCE = 0.95
_POLICY_GATE_CONFIDENCE = 1.0


class StrategyEngine:
    """Compose planner, plan builder and policy engine into a strategy verdict."""

    def __init__(
        self,
        *,
        planner: Planner | None = None,
        plan_builder: PlanBuilder | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.planner = planner or Planner()
        self.plan_builder = plan_builder or PlanBuilder(planner=self.planner)
        self.policy_engine = policy_engine or PolicyEngine()

    def decide(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        *,
        trace_id: str | None = None,
    ) -> StrategyDecision:
        """Return the deterministic strategy verdict for *task*."""
        planner_result = self.planner.plan(task)
        intent = planner_result.intent
        task_mapping = self._task_mapping(task, planner_result)

        context = PolicyEngine.build_execution_context(
            intent,
            agent_descriptor=None,
            task=task_mapping,
            task_id=task_mapping.get("task_id"),
        )
        policy_decision = self.policy_engine.evaluate(intent, None, context)

        effect = policy_decision.effect
        matched_rules = list(policy_decision.matched_rules)

        if effect == "deny":
            return StrategyDecision(
                trace_id=trace_id,
                task_type=intent.task_type,
                risk=intent.risk,
                policy_effect=effect,
                matched_policy_rules=matched_rules,
                requires_approval=False,
                allowed=False,
                selected_strategy=StrategyChoice.REJECT,
                reasoning=self._compose_reasoning(
                    "policy denied execution",
                    policy_decision.reason,
                    intent.risk,
                ),
                confidence=_POLICY_GATE_CONFIDENCE,
            )

        if effect == "require_approval":
            return StrategyDecision(
                trace_id=trace_id,
                task_type=intent.task_type,
                risk=intent.risk,
                policy_effect=effect,
                matched_policy_rules=matched_rules,
                requires_approval=True,
                allowed=True,
                selected_strategy=StrategyChoice.REQUEST_APPROVAL,
                reasoning=self._compose_reasoning(
                    "policy required human approval",
                    policy_decision.reason,
                    intent.risk,
                ),
                confidence=_POLICY_GATE_CONFIDENCE,
            )

        # effect == "allow" from here on.
        if intent.risk == CapabilityRisk.HIGH:
            return StrategyDecision(
                trace_id=trace_id,
                task_type=intent.task_type,
                risk=intent.risk,
                policy_effect=effect,
                matched_policy_rules=matched_rules,
                requires_approval=True,
                allowed=True,
                selected_strategy=StrategyChoice.REQUEST_APPROVAL,
                reasoning=self._compose_reasoning(
                    "high-risk intent requires approval",
                    policy_decision.reason,
                    intent.risk,
                ),
                confidence=_HIGH_RISK_CONFIDENCE,
            )

        plan = self.plan_builder.build(task, planner_result=planner_result)
        step_count = len(plan.steps)
        if step_count > 1:
            return StrategyDecision(
                trace_id=trace_id,
                task_type=intent.task_type,
                risk=intent.risk,
                policy_effect=effect,
                matched_policy_rules=matched_rules,
                requires_approval=False,
                allowed=True,
                selected_strategy=StrategyChoice.PLAN_AND_EXECUTE,
                reasoning=self._compose_reasoning(
                    f"multi-step plan with {step_count} steps",
                    policy_decision.reason,
                    intent.risk,
                ),
                confidence=_PLAN_CONFIDENCE,
            )

        return StrategyDecision(
            trace_id=trace_id,
            task_type=intent.task_type,
            risk=intent.risk,
            policy_effect=effect,
            matched_policy_rules=matched_rules,
            requires_approval=False,
            allowed=True,
            selected_strategy=StrategyChoice.DIRECT_EXECUTION,
            reasoning=self._compose_reasoning(
                "single-step task, direct execution",
                policy_decision.reason,
                intent.risk,
            ),
            confidence=_DIRECT_CONFIDENCE,
        )

    @staticmethod
    def _task_mapping(
        task: TaskContext | ModelContext | Mapping[str, Any],
        planner_result: PlannerResult,
    ) -> dict[str, Any]:
        normalized = dict(planner_result.normalized_task or {})
        if isinstance(task, Mapping):
            raw_id = task.get("task_id") or task.get("id")
            if raw_id:
                normalized.setdefault("task_id", str(raw_id))
        elif isinstance(task, TaskContext):
            normalized.setdefault("task_id", task.task_id)
        elif isinstance(task, ModelContext) and task.task_context is not None:
            normalized.setdefault("task_id", task.task_context.task_id)
        return normalized

    @staticmethod
    def _compose_reasoning(headline: str, policy_reason: str, risk: CapabilityRisk) -> str:
        return f"{headline}; risk={risk.value}; policy={policy_reason}"
