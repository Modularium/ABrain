"""Phase 5 – LearningOps L5: Shadow / Canary evaluation of trained models.

``ShadowEvaluator`` runs the model loaded from the active ``ModelRegistry``
entry *alongside* the production routing path, compares decisions, and writes
structured comparison metrics to ``TraceStore``.

It **never** touches the production ``RoutingDecision`` — the shadow run is
best-effort and fires after production routing completes.  If no active model
is registered, ``evaluate()`` returns ``None`` without side effects.

Shadow span written to TraceStore::

    span_type = "shadow_eval"
    name      = "learningops.shadow_evaluation"
    attributes = {
        "shadow.version_id":         str,
        "shadow.production_agent":   str | None,
        "shadow.shadow_agent":       str | None,
        "shadow.agreement":          bool,
        "shadow.score_divergence":   float,
        "shadow.top_k_overlap":      float,
        "shadow.k":                  int,
    }

No heavy dependencies — uses only existing canonical components.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.audit.trace_store import TraceStore
from core.model_context import ModelContext, TaskContext

from ..agent_descriptor import AgentDescriptor
from ..neural_policy import NeuralPolicyModel
from ..performance_history import PerformanceHistoryStore
from ..routing_engine import RoutingDecision, RoutingEngine
from .model_registry import ModelRegistry


class ShadowComparison(BaseModel):
    """Structured result of one shadow evaluation pass."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    version_id: str = Field(description="ModelRegistry version_id of the shadow model")

    # Production decision (unchanged, just referenced for comparison)
    production_agent_id: str | None = None
    production_score: float | None = None

    # Shadow decision
    shadow_agent_id: str | None = None
    shadow_score: float | None = None

    # Comparison metrics
    agreement: bool = Field(
        description="True when shadow top-1 == production top-1"
    )
    score_divergence: float = Field(
        ge=0.0, le=1.0,
        description="|production_score - shadow_score| clamped to [0,1]",
    )
    top_k_overlap: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of top-k agent IDs shared between production and shadow",
    )
    k: int = Field(ge=1, description="k used for overlap calculation")


class ShadowEvaluator:
    """Run a trained model in shadow mode and record comparison metrics.

    Parameters
    ----------
    registry:
        The canonical ``ModelRegistry`` instance.  The currently active entry
        is loaded on each ``evaluate()`` call.
    trace_store:
        The canonical ``TraceStore`` instance.  The shadow span is written here.
    k:
        Number of top candidates considered for overlap calculation.
        Default: 3.
    """

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        trace_store: TraceStore,
        k: int = 3,
    ) -> None:
        self.registry = registry
        self.trace_store = trace_store
        self.k = max(1, k)

    def evaluate(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        descriptors: Sequence[AgentDescriptor],
        production_decision: RoutingDecision,
        *,
        trace_id: str,
        performance_history: PerformanceHistoryStore | None = None,
    ) -> ShadowComparison | None:
        """Run the shadow model and record a comparison span.

        Parameters
        ----------
        task:
            The same task object that was passed to the production router.
        descriptors:
            The same agent descriptor list used in production.
        production_decision:
            The already-computed production ``RoutingDecision``.  **Not
            modified in any way.**
        trace_id:
            The trace_id of the active production trace.  The shadow span is
            attached to this trace.
        performance_history:
            Optional shared ``PerformanceHistoryStore``.  Uses a fresh empty
            store if not provided — safe because the shadow model does not
            update production state.

        Returns
        -------
        ``ShadowComparison`` when a shadow evaluation ran, ``None`` when no
        active model exists in the registry.
        """
        entry = self.registry.get_active()
        if entry is None:
            return None

        shadow_model = self.registry.get_active_model()
        if shadow_model is None:
            return None

        try:
            comparison = self._run_shadow(
                task=task,
                descriptors=descriptors,
                production_decision=production_decision,
                trace_id=trace_id,
                shadow_model=shadow_model,
                version_id=entry.version_id,
                performance_history=performance_history or PerformanceHistoryStore(),
            )
            self._write_span(comparison)
        except Exception:
            # Shadow evaluation is best-effort — never affects the production path.
            return None

        return comparison

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_shadow(
        self,
        *,
        task: TaskContext | ModelContext | Mapping[str, Any],
        descriptors: Sequence[AgentDescriptor],
        production_decision: RoutingDecision,
        trace_id: str,
        shadow_model: NeuralPolicyModel,
        version_id: str,
        performance_history: PerformanceHistoryStore,
    ) -> ShadowComparison:
        shadow_engine = RoutingEngine(
            neural_policy=shadow_model,
            performance_history=performance_history,
        )
        shadow_decision: RoutingDecision = shadow_engine.route(task, list(descriptors))

        prod_agent = production_decision.selected_agent_id
        prod_score = production_decision.selected_score
        shad_agent = shadow_decision.selected_agent_id
        shad_score = shadow_decision.selected_score

        agreement = prod_agent is not None and prod_agent == shad_agent

        # Score divergence: |prod_score - shadow_score| clamped to [0, 1].
        # When either score is absent divergence is set to 1.0.
        if prod_score is not None and shad_score is not None:
            score_divergence = min(abs(prod_score - shad_score), 1.0)
        else:
            score_divergence = 1.0

        # Top-k overlap: fraction of agent IDs in common between both ranked lists.
        k = self.k
        prod_top_k = {c.agent_id for c in production_decision.ranked_candidates[:k]}
        shad_top_k = {c.agent_id for c in shadow_decision.ranked_candidates[:k]}
        if prod_top_k or shad_top_k:
            top_k_overlap = len(prod_top_k & shad_top_k) / max(len(prod_top_k | shad_top_k), 1)
        else:
            top_k_overlap = 1.0  # both empty → trivially agree

        return ShadowComparison(
            trace_id=trace_id,
            version_id=version_id,
            production_agent_id=prod_agent,
            production_score=prod_score,
            shadow_agent_id=shad_agent,
            shadow_score=shad_score,
            agreement=agreement,
            score_divergence=score_divergence,
            top_k_overlap=top_k_overlap,
            k=k,
        )

    def _write_span(self, comparison: ShadowComparison) -> None:
        """Append a shadow_eval span to the canonical TraceStore."""
        span = self.trace_store.start_span(
            comparison.trace_id,
            span_type="shadow_eval",
            name="learningops.shadow_evaluation",
            attributes={
                "shadow.version_id": comparison.version_id,
                "shadow.production_agent": comparison.production_agent_id,
                "shadow.shadow_agent": comparison.shadow_agent_id,
                "shadow.agreement": comparison.agreement,
                "shadow.score_divergence": comparison.score_divergence,
                "shadow.top_k_overlap": comparison.top_k_overlap,
                "shadow.k": comparison.k,
            },
        )
        self.trace_store.add_event(
            span.span_id,
            event_type="shadow_comparison",
            message=(
                f"shadow={'match' if comparison.agreement else 'diverge'} "
                f"prod={comparison.production_agent_id!r} "
                f"shadow={comparison.shadow_agent_id!r} "
                f"divergence={comparison.score_divergence:.3f} "
                f"overlap={comparison.top_k_overlap:.3f}"
            ),
            payload=comparison.model_dump(mode="json"),
        )
        self.trace_store.finish_span(span.span_id, status="ok")
