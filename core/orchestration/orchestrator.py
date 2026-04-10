"""Plan execution orchestrator for multi-agent workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import logging
from typing import Any

from core.approval import ApprovalPolicy, ApprovalRequest, ApprovalStore
from core.decision import AgentCreationEngine, AgentDescriptor, AgentRegistry, FeedbackLoop, RoutingDecision, RoutingEngine
from core.decision.plan_models import ExecutionPlan, PlanStep, PlanStrategy
from core.execution.execution_engine import ExecutionEngine

from .result_aggregation import (
    OrchestrationStatus,
    PlanExecutionResult,
    PlanExecutionState,
    ResultAggregator,
    StepExecutionResult,
)

logger = logging.getLogger(__name__)


@dataclass
class _StepOutcome:
    step_result: StepExecutionResult | None = None
    approval_request: ApprovalRequest | None = None
    approval_metadata: dict[str, Any] | None = None


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
        approval_policy: ApprovalPolicy | None = None,
        approval_store: ApprovalStore | None = None,
        start_step_index: int = 0,
        existing_step_results: list[StepExecutionResult] | None = None,
        approved_step_ids: set[str] | None = None,
    ) -> PlanExecutionResult:
        creation_engine = creation_engine or AgentCreationEngine()
        approval_policy = approval_policy or ApprovalPolicy()
        approved_step_ids = set(approved_step_ids or set())
        ordered_results: list[StepExecutionResult] = list(existing_step_results or [])
        results_by_step: dict[str, StepExecutionResult] = {
            result.step_id: result for result in ordered_results
        }
        remaining_steps = plan.steps[start_step_index:]
        for group in self._iter_step_groups(plan.strategy, remaining_steps):
            group_results = self._execute_group(
                group,
                plan,
                registry,
                routing_engine,
                execution_engine,
                feedback_loop,
                creation_engine,
                results_by_step,
                approval_policy,
                approval_store,
                approved_step_ids,
                step_index_offset=plan.steps.index(group[0]),
                ordered_results=ordered_results,
            )
            if isinstance(group_results, PlanExecutionResult):
                return group_results
            for result in group_results:
                ordered_results.append(result)
                results_by_step[result.step_id] = result
            if any(not result.success for result in group_results):
                break
        return self.result_aggregator.aggregate(
            plan.task_id,
            ordered_results,
            status=OrchestrationStatus.COMPLETED,
            state=PlanExecutionState(
                status=OrchestrationStatus.COMPLETED,
                next_step_index=None,
                next_step_id=None,
                pending_approval_id=None,
                step_results=ordered_results,
                metadata={"completed_step_ids": [result.step_id for result in ordered_results]},
            ),
            metadata={
                "strategy": plan.strategy.value,
                "plan_metadata": plan.metadata,
                "parallel_groups_enabled": self.allow_parallel_groups,
            },
        )

    def _iter_step_groups(self, strategy: PlanStrategy, steps: list[PlanStep]) -> list[list[PlanStep]]:
        if strategy != PlanStrategy.PARALLEL_GROUPS:
            return [[step] for step in steps]
        groups: list[list[PlanStep]] = []
        pending_group: list[PlanStep] = []
        current_group_id: str | None = None
        for step in steps:
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
        approval_policy: ApprovalPolicy,
        approval_store: ApprovalStore | None,
        approved_step_ids: set[str],
        *,
        step_index_offset: int,
        ordered_results: list[StepExecutionResult],
    ) -> list[StepExecutionResult] | PlanExecutionResult:
        if len(steps) == 1 or not self.allow_parallel_groups:
            results: list[StepExecutionResult] = []
            for index, step in enumerate(steps):
                outcome = self._execute_step(
                    step,
                    step_index=step_index_offset + index,
                    plan=plan,
                    registry=registry,
                    routing_engine=routing_engine,
                    execution_engine=execution_engine,
                    feedback_loop=feedback_loop,
                    creation_engine=creation_engine,
                    results_by_step=results_by_step,
                    approval_policy=approval_policy,
                    approval_store=approval_store,
                    approved_step_ids=approved_step_ids,
                )
                if outcome.approval_request is not None:
                    return self._build_paused_result(
                        plan,
                        ordered_results + results,
                        step_index=step_index_offset + index,
                        step=step,
                        approval_request=outcome.approval_request,
                        approval_metadata=outcome.approval_metadata or {},
                        approval_store=approval_store,
                    )
                assert outcome.step_result is not None
                results.append(outcome.step_result)
            return results

        with ThreadPoolExecutor(max_workers=min(len(steps), self.max_parallel_steps)) as pool:
            futures = [
                pool.submit(
                    self._execute_step,
                    step,
                    step_index=step_index_offset + index,
                    plan=plan,
                    registry=registry,
                    routing_engine=routing_engine,
                    execution_engine=execution_engine,
                    feedback_loop=feedback_loop,
                    creation_engine=creation_engine,
                    results_by_step=results_by_step,
                    approval_policy=approval_policy,
                    approval_store=approval_store,
                    approved_step_ids=approved_step_ids,
                )
                for index, step in enumerate(steps)
            ]
            outcomes = [future.result() for future in futures]
            paused = next((outcome for outcome in outcomes if outcome.approval_request is not None), None)
            if paused is not None:
                paused_index = next(index for index, outcome in enumerate(outcomes) if outcome.approval_request is not None)
                return self._build_paused_result(
                    plan,
                    ordered_results,
                    step_index=step_index_offset + paused_index,
                    step=steps[paused_index],
                    approval_request=paused.approval_request,
                    approval_metadata=paused.approval_metadata or {},
                    approval_store=approval_store,
                )
            return [outcome.step_result for outcome in outcomes if outcome.step_result is not None]

    def _execute_step(
        self,
        step: PlanStep,
        *,
        step_index: int,
        plan: ExecutionPlan,
        registry: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
        routing_engine: RoutingEngine,
        execution_engine: ExecutionEngine,
        feedback_loop: FeedbackLoop,
        creation_engine: AgentCreationEngine,
        results_by_step: dict[str, StepExecutionResult],
        approval_policy: ApprovalPolicy,
        approval_store: ApprovalStore | None,
        approved_step_ids: set[str],
    ) -> _StepOutcome:
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
        selected_descriptor = self._resolve_descriptor(decision.selected_agent_id, registry)
        if approval_store is not None and step.step_id not in approved_step_ids:
            approval_check = approval_policy.evaluate(
                step,
                selected_descriptor,
                task=step_task,
            )
            if approval_check.required:
                approval_request = ApprovalRequest(
                    plan_id=plan.task_id,
                    step_id=step.step_id,
                    task_summary=step.description,
                    agent_id=decision.selected_agent_id,
                    source_type=selected_descriptor.source_type if selected_descriptor else None,
                    execution_kind=selected_descriptor.execution_kind if selected_descriptor else None,
                    reason=approval_check.reason or "approval_required",
                    risk=step.risk,
                    preview={
                        "task_type": step_task["task_type"],
                        "required_capabilities": list(step.required_capabilities),
                        "dependencies": list(step.inputs_from_steps),
                    },
                    proposed_action_summary=approval_check.proposed_action_summary,
                    metadata={
                        "matched_rules": approval_check.matched_rules,
                        "plan": plan.model_dump(mode="json"),
                    },
                )
                return _StepOutcome(
                    approval_request=approval_request,
                    approval_metadata={
                        "routing_decision": decision.model_dump(mode="json"),
                        "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
                        "selected_agent": selected_descriptor.model_dump(mode="json") if selected_descriptor else None,
                        "step_index": step_index,
                    },
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
        return _StepOutcome(
            step_result=StepExecutionResult.from_execution_result(step.step_id, execution, metadata=metadata)
        )

    def _build_paused_result(
        self,
        plan: ExecutionPlan,
        ordered_results: list[StepExecutionResult],
        *,
        step_index: int,
        step: PlanStep,
        approval_request: ApprovalRequest,
        approval_metadata: dict[str, Any],
        approval_store: ApprovalStore | None,
    ) -> PlanExecutionResult:
        state = PlanExecutionState(
            status=OrchestrationStatus.PAUSED,
            next_step_index=step_index,
            next_step_id=step.step_id,
            pending_approval_id=approval_request.approval_id,
            step_results=ordered_results,
            metadata={
                "approval_request": approval_request.model_dump(mode="json"),
                "approval_context": approval_metadata,
            },
        )
        approval_request.metadata.update(
            {
                "plan_state": state.model_dump(mode="json"),
            }
        )
        if approval_store is not None and approval_store.get_request(approval_request.approval_id) is None:
            approval_store.create_request(approval_request)
        return self.result_aggregator.aggregate(
            plan.task_id,
            ordered_results,
            status=OrchestrationStatus.PAUSED,
            state=state,
            metadata={
                "strategy": plan.strategy.value,
                "plan_metadata": plan.metadata,
                "parallel_groups_enabled": self.allow_parallel_groups,
                "pending_approval_id": approval_request.approval_id,
            },
        )

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

    def _resolve_descriptor(
        self,
        agent_id: str | None,
        registry: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
    ) -> AgentDescriptor | None:
        if not agent_id:
            return None
        if isinstance(registry, AgentRegistry):
            return registry.get(agent_id)
        if isinstance(registry, Mapping):
            return registry.get(agent_id)
        for descriptor in registry:
            if descriptor.agent_id == agent_id:
                return descriptor
        return None
