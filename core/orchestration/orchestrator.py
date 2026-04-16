"""Plan execution orchestrator for multi-agent workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import logging
from typing import Any

from core.approval import ApprovalPolicy, ApprovalRequest, ApprovalStore
from core.audit import ExplainabilityRecord, add_span_event, finish_span, record_error, start_child_span
from core.decision import AgentCreationEngine, AgentDescriptor, AgentRegistry, FeedbackLoop, RoutingDecision, RoutingEngine
from core.decision.plan_models import ExecutionPlan, PlanStep, PlanStrategy
from core.decision.task_intent import TaskIntent
from core.execution.adapters.base import is_fallback_eligible
from core.execution.audit import canonical_execution_span_attributes
from core.execution.execution_engine import ExecutionEngine
from core.governance import PolicyEngine, PolicyViolationError, enforce_policy

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


@dataclass
class _FallbackAttemptResult:
    """Internal result of a single bounded provider-fallback attempt."""

    primary_agent_id: str | None
    primary_error_code: str | None
    primary_feedback: Any | None  # FeedbackUpdate | None
    primary_feedback_error: dict[str, Any] | None
    approval_request: ApprovalRequest | None = None
    approval_metadata: dict[str, Any] | None = None
    fallback_decision: RoutingDecision | None = None
    fallback_execution: Any | None = None  # ExecutionResult | None
    fallback_feedback: Any | None = None   # FeedbackUpdate | None
    fallback_feedback_error: dict[str, Any] | None = None


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
        policy_engine: PolicyEngine | None = None,
        trace_context: Any | None = None,
        start_step_index: int = 0,
        existing_step_results: list[StepExecutionResult] | None = None,
        approved_step_ids: set[str] | None = None,
        approved_step_rating: float | None = None,
    ) -> PlanExecutionResult:
        creation_engine = creation_engine or AgentCreationEngine()
        approval_policy = approval_policy or ApprovalPolicy()
        policy_engine = policy_engine or PolicyEngine()
        approved_step_ids = set(approved_step_ids or set())
        ordered_results: list[StepExecutionResult] = list(existing_step_results or [])
        results_by_step: dict[str, StepExecutionResult] = {
            result.step_id: result for result in ordered_results
        }
        orchestration_span = start_child_span(
            trace_context,
            span_type="orchestration",
            name="execute_plan",
            attributes={
                "plan_id": plan.task_id,
                "strategy": plan.strategy.value,
                "start_step_index": start_step_index,
            },
        )
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
                policy_engine,
                approval_policy,
                approval_store,
                approved_step_ids,
                trace_context,
                step_index_offset=plan.steps.index(group[0]),
                ordered_results=ordered_results,
                approved_step_rating=approved_step_rating,
            )
            if isinstance(group_results, PlanExecutionResult):
                finish_span(
                    trace_context,
                    orchestration_span,
                    status=group_results.status.value,
                    attributes={
                        "success": group_results.success,
                        "step_count": len(group_results.step_results),
                    },
                )
                if trace_context is not None:
                    trace_context.finish_trace(
                        status=_trace_status_for_plan(group_results),
                        metadata={
                            "plan_id": plan.task_id,
                            "plan_status": group_results.status.value,
                            "step_count": len(group_results.step_results),
                        },
                    )
                return group_results
            for result in group_results:
                ordered_results.append(result)
                results_by_step[result.step_id] = result
            if any(not result.success for result in group_results):
                break
        plan_result = self.result_aggregator.aggregate(
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
        finish_span(
            trace_context,
            orchestration_span,
            status="completed" if plan_result.success else "failed",
            attributes={
                "success": plan_result.success,
                "step_count": len(plan_result.step_results),
            },
        )
        if trace_context is not None:
            trace_context.finish_trace(
                status=_trace_status_for_plan(plan_result),
                metadata={
                    "plan_id": plan.task_id,
                    "plan_status": plan_result.status.value,
                    "step_count": len(plan_result.step_results),
                },
            )
        return plan_result

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
        policy_engine: PolicyEngine,
        approval_policy: ApprovalPolicy,
        approval_store: ApprovalStore | None,
        approved_step_ids: set[str],
        trace_context: Any | None,
        *,
        step_index_offset: int,
        ordered_results: list[StepExecutionResult],
        approved_step_rating: float | None = None,
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
                    policy_engine=policy_engine,
                    approval_policy=approval_policy,
                    approval_store=approval_store,
                    approved_step_ids=approved_step_ids,
                    trace_context=trace_context,
                    approved_step_rating=approved_step_rating,
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
                        trace_context=trace_context,
                    )
                assert outcome.step_result is not None
                if outcome.step_result.metadata.get("policy_effect") == "deny":
                    return self._build_denied_result(
                        plan,
                        ordered_results + results + [outcome.step_result],
                        denied_step=step,
                        trace_context=trace_context,
                    )
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
                    policy_engine=policy_engine,
                    approval_policy=approval_policy,
                    approval_store=approval_store,
                    approved_step_ids=approved_step_ids,
                    trace_context=trace_context,
                    approved_step_rating=approved_step_rating,
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
                    trace_context=trace_context,
                )
            step_results = [outcome.step_result for outcome in outcomes if outcome.step_result is not None]
            denied = next(
                (result for result in step_results if result.metadata.get("policy_effect") == "deny"),
                None,
            )
            if denied is not None:
                denied_step = next(step for step in steps if step.step_id == denied.step_id)
                return self._build_denied_result(
                    plan,
                    ordered_results + step_results,
                    denied_step=denied_step,
                    trace_context=trace_context,
                )
            return step_results

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
        policy_engine: PolicyEngine,
        approval_policy: ApprovalPolicy,
        approval_store: ApprovalStore | None,
        approved_step_ids: set[str],
        trace_context: Any | None,
        approved_step_rating: float | None = None,
    ) -> _StepOutcome:
        step_span = start_child_span(
            trace_context,
            span_type="step",
            name=f"plan_step:{step.step_id}",
            attributes={
                "step_id": step.step_id,
                "title": step.title,
                "step_index": step_index,
            },
        )
        step_task = self._build_step_task(plan, step, results_by_step)
        descriptors = registry.list_descriptors() if isinstance(registry, AgentRegistry) else registry
        routing_span = start_child_span(
            trace_context,
            span_type="decision",
            name="route_step",
            parent_span_id=step_span,
            attributes={"step_id": step.step_id},
        )
        try:
            decision = routing_engine.route_step(step, step_task, descriptors)
            routing_span_attrs: dict[str, Any] = {
                "selected_agent_id": decision.selected_agent_id,
                "selected_score": decision.selected_score,
                "candidate_count": len(decision.ranked_candidates),
                "rejected_count": len(decision.diagnostics.get("rejected_agents") or []),
            }
            # S4.2 — confidence metrics
            if decision.routing_confidence is not None:
                routing_span_attrs["routing_confidence"] = decision.routing_confidence
            if decision.score_gap is not None:
                routing_span_attrs["score_gap"] = decision.score_gap
            if decision.confidence_band is not None:
                routing_span_attrs["confidence_band"] = decision.confidence_band
            finish_span(
                trace_context,
                routing_span,
                status="completed",
                attributes=routing_span_attrs,
            )
            # S4.2 — emit span event when routing confidence is low
            if decision.confidence_band == "low":
                add_span_event(
                    trace_context,
                    routing_span,
                    "routing_low_confidence",
                    {
                        "routing_confidence": decision.routing_confidence,
                        "score_gap": decision.score_gap,
                        "selected_agent_id": decision.selected_agent_id,
                    },
                )
        except Exception as exc:
            record_error(
                trace_context,
                routing_span,
                exc,
                message="step_routing_failed",
                payload={"step_id": step.step_id},
            )
            finish_span(trace_context, step_span, status="failed")
            raise
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
        step_intent = self._build_step_intent(plan, step, step_task)
        policy_span = start_child_span(
            trace_context,
            span_type="governance",
            name="policy_check",
            parent_span_id=step_span,
            attributes={"step_id": step.step_id, "selected_agent_id": decision.selected_agent_id},
        )
        policy_decision = policy_engine.evaluate(
            step_intent,
            selected_descriptor,
            policy_engine.build_execution_context(
                step_intent,
                selected_descriptor,
                task=step_task,
                task_id=step_task["task_id"],
                plan_id=plan.task_id,
                step_id=step.step_id,
                metadata={
                    "external_side_effect": step.metadata.get("external_side_effect"),
                    "risky_operation": step.metadata.get("risky_operation"),
                    "requires_human_approval": step.metadata.get("requires_human_approval"),
                },
            ),
        )
        try:
            policy_result = enforce_policy(policy_decision)
        except PolicyViolationError:
            self._store_explainability(
                trace_context,
                step=step,
                decision=decision,
                policy_decision=policy_decision,
                approval_required=False,
                approval_id=None,
                created_agent=created_agent,
            )
            finish_span(
                trace_context,
                policy_span,
                status="denied",
                attributes={"matched_rules": policy_decision.matched_rules},
            )
            finish_span(trace_context, step_span, status="denied")
            return _StepOutcome(
                step_result=StepExecutionResult(
                    step_id=step.step_id,
                    selected_agent_id=decision.selected_agent_id,
                    success=False,
                    output={
                        "policy_status": "deny",
                        "step_id": step.step_id,
                    },
                    warnings=["policy_denied"],
                    metadata={
                        "title": step.title,
                        "policy_effect": "deny",
                        "policy_decision": policy_decision.model_dump(mode="json"),
                        "routing_decision": decision.model_dump(mode="json"),
                        "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
                        "dependencies": list(step.inputs_from_steps),
                    },
                )
            )
        if (
            policy_result == "approval_required"
            and approval_store is not None
            and step.step_id not in approved_step_ids
        ):
            approval_request = ApprovalRequest(
                plan_id=plan.task_id,
                step_id=step.step_id,
                task_summary=step.description,
                agent_id=decision.selected_agent_id,
                source_type=selected_descriptor.source_type if selected_descriptor else None,
                execution_kind=selected_descriptor.execution_kind if selected_descriptor else None,
                reason=policy_decision.reason,
                risk=step.risk,
                preview={
                    "task_type": step_task["task_type"],
                    "required_capabilities": list(step.required_capabilities),
                    "dependencies": list(step.inputs_from_steps),
                },
                proposed_action_summary=(
                    f"Governed step {step.step_id} ({step.title}) via "
                    f"{selected_descriptor.display_name if selected_descriptor else 'unselected-agent'}"
                ),
                metadata={
                    "policy_decision": policy_decision.model_dump(mode="json"),
                    "plan": plan.model_dump(mode="json"),
                    "approval_origin": "governance",
                    "trace_id": getattr(trace_context, "trace_id", None),
                },
            )
            self._store_explainability(
                trace_context,
                step=step,
                decision=decision,
                policy_decision=policy_decision,
                approval_required=True,
                approval_id=approval_request.approval_id,
                created_agent=created_agent,
            )
            approval_span = start_child_span(
                trace_context,
                span_type="approval",
                name="approval_gate",
                parent_span_id=step_span,
                attributes={"step_id": step.step_id, "approval_origin": "governance"},
            )
            add_span_event(
                trace_context,
                approval_span,
                event_type="approval_requested",
                message="governance requested human approval",
                payload={"approval_id": approval_request.approval_id},
            )
            add_span_event(
                trace_context,
                approval_span,
                event_type="approval_pending",
                message="step paused awaiting approval",
                payload={"approval_id": approval_request.approval_id},
            )
            finish_span(
                trace_context,
                approval_span,
                status="paused",
                attributes={"approval_id": approval_request.approval_id},
            )
            finish_span(
                trace_context,
                policy_span,
                status="approval_required",
                attributes={"matched_rules": policy_decision.matched_rules},
            )
            finish_span(trace_context, step_span, status="paused")
            return _StepOutcome(
                approval_request=approval_request,
                approval_metadata={
                    "routing_decision": decision.model_dump(mode="json"),
                    "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
                    "selected_agent": selected_descriptor.model_dump(mode="json") if selected_descriptor else None,
                        "step_index": step_index,
                        "policy_decision": policy_decision.model_dump(mode="json"),
                        "trace_id": getattr(trace_context, "trace_id", None),
                    },
                )
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
                        "policy_decision": policy_decision.model_dump(mode="json"),
                        "approval_origin": "approval_policy",
                        "trace_id": getattr(trace_context, "trace_id", None),
                    },
                )
                self._store_explainability(
                    trace_context,
                    step=step,
                    decision=decision,
                    policy_decision=policy_decision,
                    approval_required=True,
                    approval_id=approval_request.approval_id,
                    created_agent=created_agent,
                )
                approval_span = start_child_span(
                    trace_context,
                    span_type="approval",
                    name="approval_gate",
                    parent_span_id=step_span,
                    attributes={"step_id": step.step_id, "approval_origin": "approval_policy"},
                )
                add_span_event(
                    trace_context,
                    approval_span,
                    event_type="approval_requested",
                    message="approval policy requested human approval",
                    payload={"approval_id": approval_request.approval_id},
                )
                add_span_event(
                    trace_context,
                    approval_span,
                    event_type="approval_pending",
                    message="step paused awaiting approval",
                    payload={"approval_id": approval_request.approval_id},
                )
                finish_span(
                    trace_context,
                    approval_span,
                    status="paused",
                    attributes={"approval_id": approval_request.approval_id},
                )
                finish_span(
                    trace_context,
                    policy_span,
                    status="approval_required",
                    attributes={"matched_rules": policy_decision.matched_rules},
                )
                finish_span(trace_context, step_span, status="paused")
                return _StepOutcome(
                    approval_request=approval_request,
                    approval_metadata={
                        "routing_decision": decision.model_dump(mode="json"),
                        "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
                        "selected_agent": selected_descriptor.model_dump(mode="json") if selected_descriptor else None,
                        "step_index": step_index,
                        "policy_decision": policy_decision.model_dump(mode="json"),
                        "trace_id": getattr(trace_context, "trace_id", None),
                    },
                )
        finish_span(
            trace_context,
            policy_span,
            status="completed",
            attributes={"matched_rules": policy_decision.matched_rules},
        )
        self._store_explainability(
            trace_context,
            step=step,
            decision=decision,
            policy_decision=policy_decision,
            approval_required=False,
            approval_id=None,
            created_agent=created_agent,
        )
        execution_span = start_child_span(
            trace_context,
            span_type="execution",
            name="adapter_execution",
            parent_span_id=step_span,
            attributes={"step_id": step.step_id, "selected_agent_id": decision.selected_agent_id},
        )
        execution = execution_engine.execute(step_task, decision, registry)
        if step.step_id in approved_step_ids and approved_step_rating is not None:
            execution.metadata["approval_decision"] = {"rating": approved_step_rating}
        finish_span(
            trace_context,
            execution_span,
            status="completed" if execution.success else "failed",
            attributes=canonical_execution_span_attributes(
                execution,
                task_type=str(step_task.get("task_type") if isinstance(step_task, Mapping) else ""),
                policy_effect=policy_decision.effect,
            ),
            error=execution.error.model_dump(mode="json") if execution.error is not None else None,
        )
        # S4: Controlled provider fallback — single bounded attempt on infrastructure errors
        _fallback: _FallbackAttemptResult | None = None
        if not execution.success and is_fallback_eligible(execution):
            _fallback = self._attempt_fallback_step(
                step=step,
                step_task=step_task,
                primary_decision=decision,
                primary_execution=execution,
                primary_policy_decision=policy_decision,
                registry=registry,
                routing_engine=routing_engine,
                execution_engine=execution_engine,
                feedback_loop=feedback_loop,
                policy_engine=policy_engine,
                approved_step_ids=approved_step_ids,
                approved_step_rating=approved_step_rating,
                trace_context=trace_context,
                step_span=step_span,
                plan=plan,
                created_agent=created_agent,
            )
            if _fallback.approval_request is not None:
                finish_span(trace_context, step_span, status="paused")
                return _StepOutcome(
                    approval_request=_fallback.approval_request,
                    approval_metadata=_fallback.approval_metadata,
                )
            if _fallback.fallback_execution is not None:
                execution = _fallback.fallback_execution
        feedback = None
        feedback_error: dict[str, Any] | None = None
        if _fallback is not None:
            # Primary feedback already recorded in _attempt_fallback_step
            feedback = (
                _fallback.fallback_feedback
                if _fallback.fallback_execution is not None
                else _fallback.primary_feedback
            )
            feedback_error = (
                _fallback.fallback_feedback_error
                if _fallback.fallback_execution is not None
                else _fallback.primary_feedback_error
            )
        elif execution.agent_id and isinstance(registry, AgentRegistry):
            feedback_span = start_child_span(
                trace_context,
                span_type="learning",
                name="feedback_update",
                parent_span_id=step_span,
                attributes={"step_id": step.step_id, "agent_id": execution.agent_id},
            )
            try:
                feedback = feedback_loop.update_performance(
                    execution.agent_id,
                    execution,
                    task=step_task,
                    agent_descriptor=registry.get(execution.agent_id),
                )
                finish_span(
                    trace_context,
                    feedback_span,
                    status="completed",
                    attributes={
                        "reward": feedback.reward,
                        "token_count": feedback.token_count,
                        "user_rating": feedback.user_rating,
                        "dataset_size": feedback.dataset_size,
                        "training_triggered": feedback.training_metrics is not None,
                        "warning_count": len(feedback.warnings),
                    },
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
                record_error(
                    trace_context,
                    feedback_span,
                    exc,
                    message="feedback_loop_failed",
                    payload={"step_id": step.step_id, "agent_id": execution.agent_id},
                )
        fallback_metadata: dict[str, Any] = {}
        if _fallback is not None:
            fallback_metadata = {
                "fallback_triggered": True,
                "primary_agent_id": _fallback.primary_agent_id,
                "primary_error_code": _fallback.primary_error_code,
                "fallback_agent_id": (
                    _fallback.fallback_execution.agent_id if _fallback.fallback_execution else None
                ),
                "fallback_routing_decision": (
                    _fallback.fallback_decision.model_dump(mode="json") if _fallback.fallback_decision else None
                ),
                "primary_feedback": (
                    _fallback.primary_feedback.model_dump(mode="json") if _fallback.primary_feedback else None
                ),
            }
        metadata = {
            "title": step.title,
            "policy_decision": policy_decision.model_dump(mode="json"),
            "routing_decision": decision.model_dump(mode="json"),
            "feedback": feedback.model_dump(mode="json") if feedback else None,
            "feedback_error": feedback_error,
            "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
            "dependencies": list(step.inputs_from_steps),
            **fallback_metadata,
        }
        if feedback:
            execution.warnings.extend(warning for warning in feedback.warnings if warning not in execution.warnings)
        finish_span(
            trace_context,
            step_span,
            status="completed" if execution.success else "failed",
            attributes={
                "step_id": step.step_id,
                "success": execution.success,
                **({"fallback_triggered": True} if _fallback else {}),
            },
        )
        return _StepOutcome(
            step_result=StepExecutionResult.from_execution_result(step.step_id, execution, metadata=metadata)
        )

    def _attempt_fallback_step(  # noqa: C901 — bounded by design; single fallback path
        self,
        *,
        step: PlanStep,
        step_task: dict[str, Any],
        primary_decision: RoutingDecision,
        primary_execution: Any,  # ExecutionResult
        primary_policy_decision: Any,
        registry: AgentRegistry | Sequence[AgentDescriptor] | Mapping[str, AgentDescriptor],
        routing_engine: RoutingEngine,
        execution_engine: ExecutionEngine,
        feedback_loop: FeedbackLoop,
        policy_engine: PolicyEngine,
        approved_step_ids: set[str],
        approved_step_rating: float | None,
        trace_context: Any | None,
        step_span: Any | None,
        plan: ExecutionPlan,
        created_agent: AgentDescriptor | None,
    ) -> _FallbackAttemptResult:
        """Attempt a single controlled provider fallback after an infrastructure-level failure.

        Always records primary failure feedback before attempting fallback routing.
        Returns a _FallbackAttemptResult that the caller uses to determine the final
        StepExecutionResult.  Invariants: max one fallback per call, governance always
        re-enforced, feedback never double-recorded.
        """
        primary_agent_id: str | None = primary_execution.agent_id or primary_decision.selected_agent_id
        primary_error_code: str | None = (
            primary_execution.error.error_code if primary_execution.error else None
        )

        # 1. Record primary failure feedback before fallback attempt
        primary_feedback = None
        primary_feedback_error = None
        if primary_agent_id and isinstance(registry, AgentRegistry):
            primary_feedback_span = start_child_span(
                trace_context,
                span_type="learning",
                name="feedback_update",
                parent_span_id=step_span,
                attributes={
                    "step_id": step.step_id,
                    "agent_id": primary_agent_id,
                    "fallback_role": "primary",
                },
            )
            try:
                primary_feedback = feedback_loop.update_performance(
                    primary_agent_id,
                    primary_execution,
                    task=step_task,
                    agent_descriptor=registry.get(primary_agent_id),
                )
                finish_span(
                    trace_context,
                    primary_feedback_span,
                    status="completed",
                    attributes={
                        "reward": primary_feedback.reward,
                        "token_count": primary_feedback.token_count,
                        "user_rating": primary_feedback.user_rating,
                        "dataset_size": primary_feedback.dataset_size,
                        "training_triggered": primary_feedback.training_metrics is not None,
                        "warning_count": len(primary_feedback.warnings),
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive containment
                warning = f"feedback_loop_failed:{exc.__class__.__name__}"
                primary_execution.warnings.append(warning)
                primary_feedback_error = {
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "warning": warning,
                }
                logger.warning(
                    json.dumps(
                        {
                            "event": "plan_feedback_loop_failed",
                            "agent_id": primary_agent_id,
                            "step_id": step.step_id,
                            "task_id": plan.task_id,
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                            "context": "primary_before_fallback",
                        },
                        sort_keys=True,
                    )
                )
                record_error(
                    trace_context,
                    primary_feedback_span,
                    exc,
                    message="feedback_loop_failed",
                    payload={"step_id": step.step_id, "agent_id": primary_agent_id},
                )

        # 2. Signal fallback trigger in trace
        add_span_event(
            trace_context,
            step_span,
            event_type="fallback_triggered",
            message="provider failure triggered controlled single-attempt fallback",
            payload={
                "primary_agent_id": primary_agent_id,
                "primary_error_code": primary_error_code,
            },
        )

        # 3. Re-route excluding the failed primary agent
        descriptors = registry.list_descriptors() if isinstance(registry, AgentRegistry) else registry
        exclude_ids: set[str] = {primary_agent_id} if primary_agent_id else set()
        fallback_routing_span = start_child_span(
            trace_context,
            span_type="decision",
            name="fallback_route_step",
            parent_span_id=step_span,
            attributes={"step_id": step.step_id, "excluded_agent_id": primary_agent_id},
        )
        try:
            fallback_decision = routing_engine.route_step(
                step, step_task, descriptors, exclude_agent_ids=exclude_ids
            )
            finish_span(
                trace_context,
                fallback_routing_span,
                status="completed",
                attributes={
                    "selected_agent_id": fallback_decision.selected_agent_id,
                    "selected_score": fallback_decision.selected_score,
                    "candidate_count": len(fallback_decision.ranked_candidates),
                },
            )
        except Exception as exc:
            record_error(
                trace_context,
                fallback_routing_span,
                exc,
                message="fallback_routing_failed",
                payload={"step_id": step.step_id},
            )
            finish_span(trace_context, fallback_routing_span, status="failed")
            return _FallbackAttemptResult(
                primary_agent_id=primary_agent_id,
                primary_error_code=primary_error_code,
                primary_feedback=primary_feedback,
                primary_feedback_error=primary_feedback_error,
            )

        if not fallback_decision.selected_agent_id:
            add_span_event(
                trace_context,
                step_span,
                event_type="fallback_no_candidate",
                message="no fallback candidate available after excluding primary agent",
                payload={"excluded_agent_id": primary_agent_id},
            )
            return _FallbackAttemptResult(
                primary_agent_id=primary_agent_id,
                primary_error_code=primary_error_code,
                primary_feedback=primary_feedback,
                primary_feedback_error=primary_feedback_error,
                fallback_decision=fallback_decision,
            )

        # 4. Re-enforce governance for the fallback agent (invariant: governance always runs)
        fallback_descriptor = self._resolve_descriptor(fallback_decision.selected_agent_id, registry)
        step_intent = self._build_step_intent(plan, step, step_task)
        fallback_policy_span = start_child_span(
            trace_context,
            span_type="governance",
            name="fallback_policy_check",
            parent_span_id=step_span,
            attributes={
                "step_id": step.step_id,
                "fallback_agent_id": fallback_decision.selected_agent_id,
            },
        )
        fallback_policy_decision = policy_engine.evaluate(
            step_intent,
            fallback_descriptor,
            policy_engine.build_execution_context(
                step_intent,
                fallback_descriptor,
                task=step_task,
                task_id=step_task["task_id"],
                plan_id=plan.task_id,
                step_id=step.step_id,
                metadata={
                    "external_side_effect": step.metadata.get("external_side_effect"),
                    "risky_operation": step.metadata.get("risky_operation"),
                    "requires_human_approval": step.metadata.get("requires_human_approval"),
                },
            ),
        )
        try:
            fallback_policy_result = enforce_policy(fallback_policy_decision)
        except PolicyViolationError:
            finish_span(
                trace_context,
                fallback_policy_span,
                status="denied",
                attributes={"matched_rules": fallback_policy_decision.matched_rules},
            )
            add_span_event(
                trace_context,
                step_span,
                event_type="fallback_governance_denied",
                message="fallback agent denied by policy",
                payload={"fallback_agent_id": fallback_decision.selected_agent_id},
            )
            return _FallbackAttemptResult(
                primary_agent_id=primary_agent_id,
                primary_error_code=primary_error_code,
                primary_feedback=primary_feedback,
                primary_feedback_error=primary_feedback_error,
                fallback_decision=fallback_decision,
            )

        # 5. Approval gate for fallback agent
        if fallback_policy_result == "approval_required" and step.step_id not in approved_step_ids:
            # Step not pre-approved; must pause — approval covers the step, not agent-specific
            approval_request = ApprovalRequest(
                plan_id=plan.task_id,
                step_id=step.step_id,
                task_summary=step.description,
                agent_id=fallback_decision.selected_agent_id,
                source_type=fallback_descriptor.source_type if fallback_descriptor else None,
                execution_kind=fallback_descriptor.execution_kind if fallback_descriptor else None,
                reason=fallback_policy_decision.reason,
                risk=step.risk,
                preview={
                    "task_type": step_task["task_type"],
                    "required_capabilities": list(step.required_capabilities),
                    "dependencies": list(step.inputs_from_steps),
                },
                proposed_action_summary=(
                    f"Fallback: governed step {step.step_id} ({step.title}) via "
                    f"{fallback_descriptor.display_name if fallback_descriptor else 'unselected-agent'}"
                ),
                metadata={
                    "policy_decision": fallback_policy_decision.model_dump(mode="json"),
                    "plan": plan.model_dump(mode="json"),
                    "approval_origin": "fallback_governance",
                    "trace_id": getattr(trace_context, "trace_id", None),
                    "fallback_context": {
                        "primary_agent_id": primary_agent_id,
                        "primary_error_code": primary_error_code,
                    },
                },
            )
            finish_span(
                trace_context,
                fallback_policy_span,
                status="approval_required",
                attributes={"matched_rules": fallback_policy_decision.matched_rules},
            )
            return _FallbackAttemptResult(
                primary_agent_id=primary_agent_id,
                primary_error_code=primary_error_code,
                primary_feedback=primary_feedback,
                primary_feedback_error=primary_feedback_error,
                fallback_decision=fallback_decision,
                approval_request=approval_request,
                approval_metadata={
                    "routing_decision": fallback_decision.model_dump(mode="json"),
                    "selected_agent": (
                        fallback_descriptor.model_dump(mode="json") if fallback_descriptor else None
                    ),
                    "policy_decision": fallback_policy_decision.model_dump(mode="json"),
                    "trace_id": getattr(trace_context, "trace_id", None),
                },
            )

        finish_span(
            trace_context,
            fallback_policy_span,
            status="completed",
            attributes={"matched_rules": fallback_policy_decision.matched_rules},
        )

        # 6. Execute fallback agent
        fallback_execution_span = start_child_span(
            trace_context,
            span_type="execution",
            name="fallback_adapter_execution",
            parent_span_id=step_span,
            attributes={
                "step_id": step.step_id,
                "fallback_agent_id": fallback_decision.selected_agent_id,
            },
        )
        fallback_execution = execution_engine.execute(step_task, fallback_decision, registry)
        if step.step_id in approved_step_ids and approved_step_rating is not None:
            fallback_execution.metadata["approval_decision"] = {"rating": approved_step_rating}
        finish_span(
            trace_context,
            fallback_execution_span,
            status="completed" if fallback_execution.success else "failed",
            attributes=canonical_execution_span_attributes(
                fallback_execution,
                task_type=str(step_task.get("task_type") if isinstance(step_task, Mapping) else ""),
                policy_effect=fallback_policy_decision.effect,
            ),
            error=(
                fallback_execution.error.model_dump(mode="json")
                if fallback_execution.error is not None
                else None
            ),
        )

        # 7. Record fallback feedback (separate from primary — never mixed)
        fallback_feedback = None
        fallback_feedback_error = None
        fallback_agent_id = fallback_execution.agent_id
        if fallback_agent_id and isinstance(registry, AgentRegistry):
            fallback_feedback_span = start_child_span(
                trace_context,
                span_type="learning",
                name="feedback_update",
                parent_span_id=step_span,
                attributes={
                    "step_id": step.step_id,
                    "agent_id": fallback_agent_id,
                    "fallback_role": "fallback",
                },
            )
            try:
                fallback_feedback = feedback_loop.update_performance(
                    fallback_agent_id,
                    fallback_execution,
                    task=step_task,
                    agent_descriptor=registry.get(fallback_agent_id),
                )
                finish_span(
                    trace_context,
                    fallback_feedback_span,
                    status="completed",
                    attributes={
                        "reward": fallback_feedback.reward,
                        "token_count": fallback_feedback.token_count,
                        "user_rating": fallback_feedback.user_rating,
                        "dataset_size": fallback_feedback.dataset_size,
                        "training_triggered": fallback_feedback.training_metrics is not None,
                        "warning_count": len(fallback_feedback.warnings),
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive containment
                warning = f"fallback_feedback_loop_failed:{exc.__class__.__name__}"
                fallback_execution.warnings.append(warning)
                fallback_feedback_error = {
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "warning": warning,
                }
                logger.warning(
                    json.dumps(
                        {
                            "event": "plan_feedback_loop_failed",
                            "agent_id": fallback_agent_id,
                            "step_id": step.step_id,
                            "task_id": plan.task_id,
                            "error_type": exc.__class__.__name__,
                            "error": str(exc),
                            "context": "fallback",
                        },
                        sort_keys=True,
                    )
                )
                record_error(
                    trace_context,
                    fallback_feedback_span,
                    exc,
                    message="fallback_feedback_loop_failed",
                    payload={"step_id": step.step_id, "agent_id": fallback_agent_id},
                )

        return _FallbackAttemptResult(
            primary_agent_id=primary_agent_id,
            primary_error_code=primary_error_code,
            primary_feedback=primary_feedback,
            primary_feedback_error=primary_feedback_error,
            fallback_decision=fallback_decision,
            fallback_execution=fallback_execution,
            fallback_feedback=fallback_feedback,
            fallback_feedback_error=fallback_feedback_error,
        )

    def _build_denied_result(
        self,
        plan: ExecutionPlan,
        ordered_results: list[StepExecutionResult],
        *,
        denied_step: PlanStep,
        trace_context: Any | None = None,
    ) -> PlanExecutionResult:
        return self.result_aggregator.aggregate(
            plan.task_id,
            ordered_results,
            status=OrchestrationStatus.DENIED,
            state=PlanExecutionState(
                status=OrchestrationStatus.DENIED,
                next_step_index=None,
                next_step_id=denied_step.step_id,
                pending_approval_id=None,
                step_results=ordered_results,
                metadata={"denied_step_id": denied_step.step_id},
            ),
            metadata={
                "strategy": plan.strategy.value,
                "plan_metadata": plan.metadata,
                "denied_step_id": denied_step.step_id,
            },
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
        trace_context: Any | None = None,
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
                "trace_id": getattr(trace_context, "trace_id", None),
            },
        )
        approval_request.metadata.update(
            {
                "plan_state": state.model_dump(mode="json"),
                "trace_id": getattr(trace_context, "trace_id", None),
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

    def _store_explainability(
        self,
        trace_context: Any | None,
        *,
        step: PlanStep,
        decision: RoutingDecision,
        policy_decision: Any,
        approval_required: bool,
        approval_id: str | None,
        created_agent: AgentDescriptor | None,
    ) -> None:
        if trace_context is None or not getattr(trace_context, "trace_id", None):
            return
        trace_context.store_explainability(
            ExplainabilityRecord(
                trace_id=trace_context.trace_id,
                step_id=step.step_id,
                selected_agent_id=decision.selected_agent_id,
                candidate_agent_ids=[candidate.agent_id for candidate in decision.ranked_candidates],
                selected_score=decision.selected_score,
                routing_reason_summary=_build_routing_reason_summary(decision),
                matched_policy_ids=list(policy_decision.matched_rules),
                approval_required=approval_required,
                approval_id=approval_id,
                metadata={
                    "routing_decision": decision.model_dump(mode="json"),
                    "rejected_agents": decision.diagnostics.get("rejected_agents") or [],
                    "candidate_filter": decision.diagnostics.get("candidate_filter") or {},
                    "created_agent": created_agent.model_dump(mode="json") if created_agent else None,
                    "winning_policy_rule": policy_decision.winning_rule_id,
                },
            )
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

    def _build_step_intent(
        self,
        plan: ExecutionPlan,
        step: PlanStep,
        step_task: Mapping[str, Any],
    ) -> TaskIntent:
        preferences = dict(step_task.get("preferences") or {})
        execution_hints = dict(preferences.get("execution_hints") or {})
        return TaskIntent(
            task_type=str(step.metadata.get("task_type") or step.step_id),
            domain=str(step.metadata.get("domain") or plan.metadata.get("intent_domain") or "analysis"),
            risk=step.risk,
            required_capabilities=list(step.required_capabilities),
            execution_hints=execution_hints,
            description=step.description,
        )

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


def _build_routing_reason_summary(decision: RoutingDecision) -> str:
    selected = decision.selected_agent_id or "unselected-agent"
    score = (
        f"{decision.selected_score:.3f}" if isinstance(decision.selected_score, (int, float)) else "n/a"
    )
    rejected_count = len(decision.diagnostics.get("rejected_agents") or [])
    candidate_count = len(decision.ranked_candidates or [])
    return (
        f"selected {selected} with score {score}; "
        f"{candidate_count} ranked candidates; {rejected_count} rejected by CandidateFilter"
    )


def _trace_status_for_plan(result: PlanExecutionResult) -> str:
    if result.status != OrchestrationStatus.COMPLETED:
        return result.status.value
    return "completed" if result.success else "failed"
