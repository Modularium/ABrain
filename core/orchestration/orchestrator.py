"""Plan execution orchestrator for multi-agent workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from typing import Any

from core.decision import AgentCreationEngine, AgentDescriptor, AgentRegistry, FeedbackLoop, RoutingDecision, RoutingEngine
from core.decision.plan_models import ExecutionPlan, PlanStep, PlanStrategy
from core.execution.execution_engine import ExecutionEngine

from .result_aggregation import PlanExecutionResult, ResultAggregator, StepExecutionResult

logger = logging.getLogger(__name__)


class PlanExecutionOrchestrator:
    """Execute a structured plan through the canonical routing and execution stack."""

    def __init__(
        self,
        *,
        result_aggregator: ResultAggregator | None = None,
        allow_parallel_groups: bool = False,
        max_parallel_steps: int = 2,
    ) -> None:
        self.result_aggregator = result_aggregator or ResultAggregator()
        self.allow_parallel_groups = allow_parallel_groups
        self.max_parallel_steps = max_parallel_steps

    def execute_plan(
        self,
        plan: ExecutionPlan,
        registry: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
        routing_engine: RoutingEngine,
        execution_engine: ExecutionEngine,
        feedback_loop: FeedbackLoop,
        *,
        creation_engine: AgentCreationEngine | None = None,
    ) -> PlanExecutionResult:
        creation_engine = creation_engine or AgentCreationEngine()
        ordered_results: list[StepExecutionResult] = []
        results_by_step: dict[str, StepExecutionResult] = {}
        for group in self._iter_step_groups(plan):
            group_results = self._execute_group(
                group,
                plan,
                registry,
                routing_engine,
                execution_engine,
                feedback_loop,
                creation_engine,
                results_by_step,
            )
            for result in group_results:
                ordered_results.append(result)
                results_by_step[result.step_id] = result
            if any(not result.success for result in group_results):
                break
        return self.result_aggregator.aggregate(
            plan.task_id,
            ordered_results,
            metadata={
                "strategy": plan.strategy.value,
                "plan_metadata": plan.metadata,
                "parallel_groups_enabled": self.allow_parallel_groups,
            },
        )

    def _iter_step_groups(self, plan: ExecutionPlan) -> list[list[PlanStep]]:
        if plan.strategy != PlanStrategy.PARALLEL_GROUPS:
            return [[step] for step in plan.steps]
        groups: list[list[PlanStep]] = []
        pending_group: list[PlanStep] = []
        current_group_id: str | None = None
        for step in plan.steps:
            if step.allow_parallel_group is None:
                if pending_group:
                    groups.append(pending_group)
                    pending_group = []
                    current_group_id = None
                groups.append([step])
                continue
            if current_group_id == step.allow_parallel_group:
                pending_group.append(step)
                continue
            if pending_group:
                groups.append(pending_group)
            pending_group = [step]
            current_group_id = step.allow_parallel_group
        if pending_group:
            groups.append(pending_group)
        return groups

    def _execute_group(
        self,
        steps: list[PlanStep],
        plan: ExecutionPlan,
        registry: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
        routing_engine: RoutingEngine,
        execution_engine: ExecutionEngine,
        feedback_loop: FeedbackLoop,
        creation_engine: AgentCreationEngine,
        results_by_step: dict[str, StepExecutionResult],
    ) -> list[StepExecutionResult]:
        if len(steps) == 1 or not self.allow_parallel_groups:
            results: list[StepExecutionResult] = []
            for step in steps:
                results.append(
                    self._execute_step(
                        step,
                        plan,
                        registry,
                        routing_engine,
                        execution_engine,
                        feedback_loop,
                        creation_engine,
                        results_by_step,
                    )
                )
            return results

        with ThreadPoolExecutor(max_workers=min(len(steps), self.max_parallel_steps)) as pool:
            futures = [
                pool.submit(
                    self._execute_step,
                    step,
                    plan,
                    registry,
                    routing_engine,
                    execution_engine,
                    feedback_loop,
                    creation_engine,
                    results_by_step,
                )
                for step in steps
            ]
            return [future.result() for future in futures]

    def _execute_step(
        self,
        step: PlanStep,
        plan: ExecutionPlan,
        registry: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
        routing_engine: RoutingEngine,
        execution_engine: ExecutionEngine,
        feedback_loop: FeedbackLoop,
        creation_engine: AgentCreationEngine,
        results_by_step: dict[str, StepExecutionResult],
    ) -> StepExecutionResult:
        step_task = self._build_step_task(plan, step, results_by_step)
        descriptors = registry.list_descriptors() if isinstance(registry, AgentRegistry) else registry
        decision = routing_engine.route_step(step, step_task, descriptors)
        created_agent = None
        if creation_engine.should_create_agent(decision.selected_score):
            created_agent = creation_engine.create_agent_from_task(
                step_task,
                step.required_capabilities,
                registry=registry if isinstance(registry, AgentRegistry) else None,
            )
            descriptors = registry.list_descriptors() if isinstance(registry, AgentRegistry) else registry
            rerouted = routing_engine.route_step(step, step_task, descriptors)
            if rerouted.selected_agent_id:
                decision = rerouted
            else:
                decision = RoutingDecision(
                    task_type=decision.task_type,
                    required_capabilities=decision.required_capabilities,
                    ranked_candidates=decision.ranked_candidates,
                    selected_agent_id=created_agent.agent_id,
                    selected_score=decision.selected_score,
                    diagnostics={**decision.diagnostics, "created_agent": created_agent.agent_id},
                )
        execution = execution_engine.execute(step_task, decision, registry)
        feedback = None
        feedback_error: dict[str, Any] | None = None
        if execution.agent_id and isinstance(registry, AgentRegistry):
            try:
                feedback = feedback_loop.update_performance(
                    execution.agent_id,
                    execution,
                    task=step_task,
                    agent_descriptor=registry.get(execution.agent_id),
                )
            except Exception as exc:  # pragma: no cover - defensive containment
                warning = f"feedback_loop_failed:{exc.__class__.__name__}"
                execution.warnings.append(warning)
                feedback_error = {
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "warning": warning,
                }
                logger.warning(
                    json.dumps(
                        {
                            "event": "plan_feedback_loop_failed",
                            "agent_id": execution.agent_id,
                            "step_id": step.step_id,
                            "task_id": plan.task_id,
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                        },
                        sort_keys=True,
                    )
                )
        metadata = {
            "title": step.title,
            "routing_decision": decision.model_dump(mode="json"),
            "feedback": feedback.model_dump(mode="json") if feedback else None,
            "feedback_error": feedback_error,
            "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
            "dependencies": list(step.inputs_from_steps),
        }
        if feedback:
            execution.warnings.extend(warning for warning in feedback.warnings if warning not in execution.warnings)
        return StepExecutionResult.from_execution_result(step.step_id, execution, metadata=metadata)

    def _build_step_task(
        self,
        plan: ExecutionPlan,
        step: PlanStep,
        results_by_step: Mapping[str, StepExecutionResult],
    ) -> dict[str, Any]:
        dependency_outputs = {
            step_id: results_by_step[step_id].output
            for step_id in step.inputs_from_steps
            if step_id in results_by_step
        }
        description = step.description
        if dependency_outputs:
            dependency_summary = "; ".join(
                f"{step_id}: {results_by_step[step_id].output!r}" for step_id in step.inputs_from_steps if step_id in results_by_step
            )
            description = f"{step.description}\n\nInputs from prior steps: {dependency_summary}"
        execution_hints: dict[str, Any] = {
            "required_capabilities": list(step.required_capabilities),
        }
        if step.preferred_source_types:
            execution_hints["allowed_source_types"] = [item.value for item in step.preferred_source_types]
        if step.preferred_execution_kinds:
            execution_hints["allowed_execution_kinds"] = [item.value for item in step.preferred_execution_kinds]
        return {
            "task_id": f"{plan.task_id}:{step.step_id}",
            "task_type": str(step.metadata.get("task_type") or step.step_id),
            "description": description,
            "input_data": dependency_outputs or None,
            "preferences": {
                "domain": str(step.metadata.get("domain") or plan.metadata.get("intent_domain") or "analysis"),
                "required_capabilities": list(step.required_capabilities),
                "execution_hints": execution_hints,
                "plan_step_id": step.step_id,
                "plan_strategy": plan.strategy.value,
            },
        }
