"""TraceEvaluator — canonical dry-run replay and compliance harness.

Reads stored traces from :class:`TraceStore`, re-runs routing and policy
decisions with the *current* engines, and surfaces regressions.

Design invariants
-----------------
- Read-only: does not write to TraceStore, ApprovalStore, or any other store.
- No execution: never calls ExecutionEngine, adapters, or external services.
- No side effects: creating a TraceEvaluator is safe at any time.
- Single canonical TraceStore: reuses the store passed in; never opens a second.
- Single canonical routing / policy engine: reuses instances passed in; never
  builds hidden parallel instances.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.audit.trace_store import TraceStore
from core.decision.capabilities import CapabilityRisk
from core.decision.task_intent import TaskIntent
from core.governance.policy_engine import PolicyEngine
from core.governance.policy_models import PolicyEvaluationContext

from .models import (
    BatchEvaluationReport,
    PolicyReplayResult,
    PolicyReplayVerdict,
    RoutingReplayResult,
    RoutingReplayVerdict,
    StepEvaluationResult,
    TraceEvaluationResult,
    classify_policy_delta,
)

if TYPE_CHECKING:
    from core.audit.trace_models import ExplainabilityRecord, ReplayDescriptor, TraceSnapshot
    from core.decision.agent_descriptor import AgentDescriptor
    from core.decision.routing_engine import RoutingDecision, RoutingEngine

logger = logging.getLogger(__name__)

# Confidence delta threshold above which a routing change is classified as
# REGRESSION rather than ACCEPTABLE_VARIATION.
_CONFIDENCE_REGRESSION_THRESHOLD = 0.15


class TraceEvaluator:
    """Evaluate stored traces against the current routing and governance logic.

    Parameters
    ----------
    trace_store:
        The canonical :class:`TraceStore` to read from.
    routing_engine:
        A :class:`RoutingEngine` instance — used for dry-run routing only.
    policy_engine:
        A :class:`PolicyEngine` instance — used for dry-run policy evaluation.
    agent_descriptors:
        Current agent catalog.  If ``None`` or empty, routing dry-runs return
        ``NON_REPLAYABLE`` (no candidates to route against).
    """

    def __init__(
        self,
        trace_store: TraceStore,
        routing_engine: RoutingEngine,
        policy_engine: PolicyEngine,
        *,
        agent_descriptors: list[AgentDescriptor] | None = None,
    ) -> None:
        self._trace_store = trace_store
        self._routing_engine = routing_engine
        self._policy_engine = policy_engine
        self._agent_descriptors: list[AgentDescriptor] = list(agent_descriptors or [])
        self._agent_by_id: dict[str, AgentDescriptor] = {
            d.agent_id: d for d in self._agent_descriptors
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_trace(self, trace_id: str) -> TraceEvaluationResult | None:
        """Evaluate a single stored trace.

        Returns ``None`` if the trace does not exist in the store.
        Each explainability step is replayed against the current routing and
        policy engines without triggering any execution.
        """
        snapshot = self._trace_store.get_trace(trace_id)
        if snapshot is None:
            return None
        return self._evaluate_snapshot(snapshot)

    def compute_baselines(self, *, limit: int = 100) -> BatchEvaluationReport:
        """Compute baseline metrics across the *limit* most recent traces.

        This is a read-only batch operation — it evaluates each trace but
        writes no results back to any store.
        """
        traces = self._trace_store.list_recent_traces(limit=limit)
        report = BatchEvaluationReport(
            baseline_metadata={"limit": limit, "found": len(traces)},
        )

        confidences: list[float] = []
        durations_ms: list[float] = []

        for trace_record in traces:
            snapshot = self._trace_store.get_trace(trace_record.trace_id)
            if snapshot is None:
                continue
            result = self._evaluate_snapshot(snapshot)

            report.trace_count += 1

            # ── Routing KPIs: success rate + latency ──────────────────────
            trace_status = snapshot.trace.status.lower() if snapshot.trace.status else ""
            if trace_status == "completed":
                report.trace_success_count += 1
            elif trace_status == "failed":
                report.trace_failed_count += 1

            if (
                snapshot.trace.ended_at is not None
                and snapshot.trace.started_at is not None
                and trace_status == "completed"
            ):
                delta = (
                    snapshot.trace.ended_at - snapshot.trace.started_at
                ).total_seconds() * 1000.0
                if delta >= 0.0:
                    durations_ms.append(delta)

            # ── Safety metrics: approval bypass ───────────────────────────
            for exp in snapshot.explainability:
                if exp.approval_required and not exp.approval_id:
                    report.approval_bypass_count += 1

            if result.can_replay:
                report.replayable_count += 1
            if result.has_any_regression:
                report.traces_with_regression += 1

            for step in result.step_results:
                report.evaluated_step_count += 1

                r = step.routing
                if r.verdict is RoutingReplayVerdict.NON_REPLAYABLE:
                    report.non_replayable_step_count += 1
                elif r.verdict is RoutingReplayVerdict.EXACT_MATCH:
                    report.routing_exact_match_count += 1
                elif r.verdict is RoutingReplayVerdict.ACCEPTABLE_VARIATION:
                    report.routing_acceptable_variation_count += 1
                elif r.verdict is RoutingReplayVerdict.REGRESSION:
                    report.routing_regression_count += 1

                if r.stored_confidence is not None:
                    confidences.append(r.stored_confidence)

                if r.stored_confidence_band:
                    band = r.stored_confidence_band
                    report.confidence_band_distribution[band] = (
                        report.confidence_band_distribution.get(band, 0) + 1
                    )

                p = step.policy
                if p is not None:
                    if p.verdict is PolicyReplayVerdict.COMPLIANT:
                        report.policy_compliant_count += 1
                    elif p.verdict is PolicyReplayVerdict.TIGHTENED:
                        report.policy_tightened_count += 1
                    elif p.verdict is PolicyReplayVerdict.REGRESSION:
                        report.policy_regression_count += 1

                    if p.verdict is not PolicyReplayVerdict.NON_EVALUABLE:
                        if p.approval_consistency:
                            report.approval_consistent_count += 1
                        else:
                            report.approval_inconsistent_count += 1

        # Derived rates
        routable = (
            report.routing_exact_match_count
            + report.routing_acceptable_variation_count
            + report.routing_regression_count
        )
        if routable > 0:
            report.routing_match_rate = report.routing_exact_match_count / routable

        policy_total = (
            report.policy_compliant_count
            + report.policy_tightened_count
            + report.policy_regression_count
        )
        if policy_total > 0:
            report.policy_compliance_rate = report.policy_compliant_count / policy_total

        approval_total = report.approval_consistent_count + report.approval_inconsistent_count
        if approval_total > 0:
            report.approval_consistency_rate = report.approval_consistent_count / approval_total

        if confidences:
            report.avg_routing_confidence = sum(confidences) / len(confidences)

        # ── Routing KPIs: derived rates ────────────────────────────────────
        terminal_count = report.trace_success_count + report.trace_failed_count
        if terminal_count > 0:
            report.trace_success_rate = report.trace_success_count / terminal_count

        if durations_ms:
            report.avg_duration_ms = sum(durations_ms) / len(durations_ms)
            sorted_d = sorted(durations_ms)
            # 95th percentile: index = min(floor(0.95 * N), N-1)
            p95_idx = min(int(0.95 * len(sorted_d)), len(sorted_d) - 1)
            report.p95_duration_ms = sorted_d[p95_idx]

        return report

    # ------------------------------------------------------------------
    # Internal evaluation logic
    # ------------------------------------------------------------------

    def _evaluate_snapshot(self, snapshot: TraceSnapshot) -> TraceEvaluationResult:
        """Evaluate all explainability steps in a snapshot."""
        replay_descriptor = snapshot.replay_descriptor
        can_replay = bool(replay_descriptor and replay_descriptor.can_replay)

        step_results: list[StepEvaluationResult] = []

        for exp in snapshot.explainability:
            step_id = exp.step_id or "task"
            routing_result = self._evaluate_routing_step(exp, replay_descriptor)
            policy_result = self._evaluate_policy_step(exp)
            has_regression = (
                routing_result.verdict is RoutingReplayVerdict.REGRESSION
                or (
                    policy_result is not None
                    and policy_result.verdict is PolicyReplayVerdict.REGRESSION
                )
            )
            step_results.append(
                StepEvaluationResult(
                    step_id=step_id,
                    routing=routing_result,
                    policy=policy_result,
                    has_regression=has_regression,
                )
            )

        routing_match_count = sum(
            1 for s in step_results
            if s.routing.verdict is RoutingReplayVerdict.EXACT_MATCH
        )
        routing_regression_count = sum(
            1 for s in step_results
            if s.routing.verdict is RoutingReplayVerdict.REGRESSION
        )
        policy_compliant_count = sum(
            1 for s in step_results
            if s.policy is not None and s.policy.verdict is PolicyReplayVerdict.COMPLIANT
        )
        policy_regression_count = sum(
            1 for s in step_results
            if s.policy is not None and s.policy.verdict is PolicyReplayVerdict.REGRESSION
        )
        non_replayable_count = sum(
            1 for s in step_results
            if s.routing.verdict is RoutingReplayVerdict.NON_REPLAYABLE
        )

        has_routing_regression = routing_regression_count > 0
        has_policy_regression = policy_regression_count > 0
        has_any_regression = has_routing_regression or has_policy_regression

        return TraceEvaluationResult(
            trace_id=snapshot.trace.trace_id,
            workflow_name=snapshot.trace.workflow_name,
            can_replay=can_replay,
            step_results=step_results,
            has_routing_regression=has_routing_regression,
            has_policy_regression=has_policy_regression,
            has_any_regression=has_any_regression,
            routing_match_count=routing_match_count,
            routing_regression_count=routing_regression_count,
            policy_compliant_count=policy_compliant_count,
            policy_regression_count=policy_regression_count,
            non_replayable_count=non_replayable_count,
            summary={
                "step_count": len(step_results),
                "can_replay": can_replay,
                "has_any_regression": has_any_regression,
            },
        )

    def _evaluate_routing_step(
        self,
        exp: ExplainabilityRecord,
        replay_descriptor: ReplayDescriptor | None,
    ) -> RoutingReplayResult:
        """Dry-run routing for one stored explainability record."""
        step_id = exp.step_id or "task"

        # Non-replayable fast path: no agent catalog
        if not self._agent_descriptors:
            return RoutingReplayResult(
                step_id=step_id,
                verdict=RoutingReplayVerdict.NON_REPLAYABLE,
                stored_agent_id=exp.selected_agent_id,
                stored_confidence=exp.routing_confidence,
                stored_confidence_band=exp.confidence_band,
                stored_score_gap=exp.score_gap,
                non_replayable_reason="no agent descriptors available for routing dry-run",
            )

        # Extract task_type and required_capabilities from stored metadata.
        # Current format (post-S10): flat keys at metadata top level.
        # Legacy format: nested under metadata["routing_decision"].
        routing_meta: dict[str, Any] = {}
        if isinstance(exp.metadata.get("routing_decision"), dict):
            routing_meta = exp.metadata["routing_decision"]

        task_type = (
            exp.metadata.get("task_type")                            # current flat format
            or routing_meta.get("task_type")                         # legacy nested format
            or (replay_descriptor.task_type if replay_descriptor else None)  # from descriptor
        )
        if not task_type:
            return RoutingReplayResult(
                step_id=step_id,
                verdict=RoutingReplayVerdict.NON_REPLAYABLE,
                stored_agent_id=exp.selected_agent_id,
                stored_confidence=exp.routing_confidence,
                stored_confidence_band=exp.confidence_band,
                stored_score_gap=exp.score_gap,
                non_replayable_reason="task_type missing from stored trace",
            )

        required_capabilities: list[str] = list(
            exp.metadata.get("required_capabilities")           # current flat format
            or routing_meta.get("required_capabilities")        # legacy nested format
            or []
        )

        # Build a minimal TaskIntent for the dry-run
        try:
            intent = TaskIntent(
                task_type=task_type,
                domain="analysis",  # not stored; safe default for replay
                risk=CapabilityRisk.MEDIUM,  # not stored; safe default
                required_capabilities=required_capabilities,
            )
        except Exception as exc:
            return RoutingReplayResult(
                step_id=step_id,
                verdict=RoutingReplayVerdict.NON_REPLAYABLE,
                stored_agent_id=exp.selected_agent_id,
                stored_confidence=exp.routing_confidence,
                stored_confidence_band=exp.confidence_band,
                stored_score_gap=exp.score_gap,
                non_replayable_reason=f"could not build TaskIntent: {exc}",
            )

        # Dry-run: call route_intent with current agent catalog (no execution)
        try:
            decision: RoutingDecision = self._routing_engine.route_intent(
                intent,
                self._agent_descriptors,
            )
        except Exception as exc:
            logger.debug("routing dry-run failed for step %s: %s", step_id, exc)
            return RoutingReplayResult(
                step_id=step_id,
                verdict=RoutingReplayVerdict.NON_REPLAYABLE,
                stored_agent_id=exp.selected_agent_id,
                stored_confidence=exp.routing_confidence,
                stored_confidence_band=exp.confidence_band,
                stored_score_gap=exp.score_gap,
                non_replayable_reason=f"routing dry-run raised exception: {exc}",
            )

        current_agent_id = decision.selected_agent_id
        current_confidence = decision.routing_confidence
        current_band = decision.confidence_band
        current_gap = decision.score_gap
        top_candidates = [c.agent_id for c in decision.ranked_candidates[:5]]

        stored_agent_id = exp.selected_agent_id
        stored_confidence = exp.routing_confidence
        stored_band = exp.confidence_band

        # Classify verdict
        verdict, reason = _classify_routing_verdict(
            stored_agent_id=stored_agent_id,
            current_agent_id=current_agent_id,
            stored_band=stored_band,
            current_band=current_band,
            stored_confidence=stored_confidence,
            current_confidence=current_confidence,
        )

        return RoutingReplayResult(
            step_id=step_id,
            verdict=verdict,
            stored_agent_id=stored_agent_id,
            current_agent_id=current_agent_id,
            stored_confidence=stored_confidence,
            stored_confidence_band=stored_band,
            stored_score_gap=exp.score_gap,
            current_confidence=current_confidence,
            current_confidence_band=current_band,
            current_score_gap=current_gap,
            current_top_candidates=top_candidates,
            reason=reason,
        )

    def _evaluate_policy_step(
        self,
        exp: ExplainabilityRecord,
    ) -> PolicyReplayResult | None:
        """Dry-run policy evaluation for one stored explainability record.

        Returns ``None`` when the stored record has no policy signal to compare
        (policy_effect is None and no matched_policy_ids).
        """
        step_id = exp.step_id or "task"
        stored_effect = exp.policy_effect
        stored_approval = exp.approval_required

        # No stored policy signal — nothing to compare
        if stored_effect is None and not exp.matched_policy_ids:
            return None

        # Build a minimal PolicyEvaluationContext for the dry-run.
        # Current format: task_type and required_capabilities are flat top-level keys.
        # Legacy format: nested under metadata["routing_decision"].
        routing_meta: dict[str, Any] = {}
        if isinstance(exp.metadata.get("routing_decision"), dict):
            routing_meta = exp.metadata["routing_decision"]

        task_type = (
            exp.metadata.get("task_type")   # current flat format
            or routing_meta.get("task_type")  # legacy nested format
            or ""
        )
        if not task_type:
            return PolicyReplayResult(
                step_id=step_id,
                verdict=PolicyReplayVerdict.NON_EVALUABLE,
                stored_effect=stored_effect,
                stored_matched_policy_ids=list(exp.matched_policy_ids),
                stored_approval_required=stored_approval,
                current_approval_required=stored_approval,
                approval_consistency=True,
                reason="task_type missing — cannot reconstruct evaluation context",
            )

        required_capabilities: list[str] = list(
            exp.metadata.get("required_capabilities")   # current flat format
            or routing_meta.get("required_capabilities")  # legacy nested format
            or []
        )

        # Reconstruct agent descriptor from live catalog if available
        agent_descriptor = self._agent_by_id.get(exp.selected_agent_id or "")

        try:
            context = self._policy_engine.build_execution_context(
                TaskIntent(
                    task_type=task_type,
                    domain="analysis",
                    risk=CapabilityRisk.MEDIUM,
                    required_capabilities=required_capabilities,
                ),
                agent_descriptor,
            )
            policy_decision = self._policy_engine.evaluate(
                TaskIntent(
                    task_type=task_type,
                    domain="analysis",
                    risk=CapabilityRisk.MEDIUM,
                    required_capabilities=required_capabilities,
                ),
                agent_descriptor,
                context,
            )
        except Exception as exc:
            logger.debug("policy dry-run failed for step %s: %s", step_id, exc)
            return PolicyReplayResult(
                step_id=step_id,
                verdict=PolicyReplayVerdict.NON_EVALUABLE,
                stored_effect=stored_effect,
                stored_matched_policy_ids=list(exp.matched_policy_ids),
                stored_approval_required=stored_approval,
                current_approval_required=stored_approval,
                approval_consistency=True,
                reason=f"policy dry-run raised exception: {exc}",
            )

        current_effect = policy_decision.effect
        current_matched = list(policy_decision.matched_rules)
        current_approval = current_effect == "require_approval"

        verdict = classify_policy_delta(stored_effect, current_effect)

        approval_consistency = stored_approval == current_approval

        reason = _build_policy_reason(
            verdict=verdict,
            stored_effect=stored_effect,
            current_effect=current_effect,
            approval_consistency=approval_consistency,
        )

        return PolicyReplayResult(
            step_id=step_id,
            verdict=verdict,
            stored_effect=stored_effect,
            current_effect=current_effect,
            stored_matched_policy_ids=list(exp.matched_policy_ids),
            current_matched_policy_ids=current_matched,
            stored_approval_required=stored_approval,
            current_approval_required=current_approval,
            approval_consistency=approval_consistency,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Verdict helpers (module-level, pure functions)
# ---------------------------------------------------------------------------


def _classify_routing_verdict(
    *,
    stored_agent_id: str | None,
    current_agent_id: str | None,
    stored_band: str | None,
    current_band: str | None,
    stored_confidence: float | None,
    current_confidence: float | None,
) -> tuple[RoutingReplayVerdict, str]:
    """Return (verdict, reason) for a routing comparison.

    Pure function — no I/O, no side effects.
    """
    if stored_agent_id == current_agent_id:
        return (
            RoutingReplayVerdict.EXACT_MATCH,
            f"same agent selected: {current_agent_id or 'none'}",
        )

    # Different agent — check whether the confidence metrics indicate regression
    if stored_band is not None and current_band is not None and stored_band == current_band:
        return (
            RoutingReplayVerdict.ACCEPTABLE_VARIATION,
            (
                f"different agent ({stored_agent_id!r} → {current_agent_id!r}) "
                f"but same confidence band: {current_band}"
            ),
        )

    if (
        stored_confidence is not None
        and current_confidence is not None
        and abs(stored_confidence - current_confidence) <= _CONFIDENCE_REGRESSION_THRESHOLD
    ):
        return (
            RoutingReplayVerdict.ACCEPTABLE_VARIATION,
            (
                f"different agent ({stored_agent_id!r} → {current_agent_id!r}), "
                f"confidence delta within threshold "
                f"({stored_confidence:.3f} → {current_confidence:.3f})"
            ),
        )

    # Band changed or confidence diverged significantly
    band_desc = (
        f"band {stored_band!r} → {current_band!r}"
        if stored_band != current_band
        else f"confidence {stored_confidence} → {current_confidence}"
    )
    return (
        RoutingReplayVerdict.REGRESSION,
        (
            f"different agent ({stored_agent_id!r} → {current_agent_id!r}), "
            f"{band_desc}"
        ),
    )


def _build_policy_reason(
    *,
    verdict: PolicyReplayVerdict,
    stored_effect: str | None,
    current_effect: str | None,
    approval_consistency: bool,
) -> str:
    """Build a human-readable policy comparison reason string."""
    if verdict is PolicyReplayVerdict.COMPLIANT:
        parts = [f"policy effect unchanged: {current_effect!r}"]
    elif verdict is PolicyReplayVerdict.TIGHTENED:
        parts = [f"policy tightened: {stored_effect!r} → {current_effect!r}"]
    elif verdict is PolicyReplayVerdict.REGRESSION:
        parts = [f"policy regression: {stored_effect!r} → {current_effect!r} (more permissive)"]
    else:
        parts = [f"non-evaluable: stored={stored_effect!r} current={current_effect!r}"]

    if not approval_consistency:
        parts.append("approval_required changed")

    return "; ".join(parts)
