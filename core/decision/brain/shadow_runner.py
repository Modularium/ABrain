"""Phase 6 – Brain v1 B6-S4: Brain shadow runner.

Runs the active Brain v1 model from ``ModelRegistry`` *alongside* the
production routing path, ranks the same candidate set with the Brain
network, and writes a structured comparison span to ``TraceStore``.

Why a separate runner instead of reusing ``ShadowEvaluator``?

The Brain model uses a fixed 13-dim feature schema
(``BRAIN_FEATURE_NAMES``) that is fundamentally different from the
production ``FeatureEncoder`` schema embedded in ``NeuralPolicyModel``.
A Brain artefact loaded into a production ``RoutingEngine`` would fail
``NeuralPolicyModel._ensure_model``'s schema check.  The Brain runner
therefore feeds the loaded ``MLPScoringModel`` pre-encoded Brain feature
vectors directly — no production router involvement.

Like ``ShadowEvaluator``:
- best-effort: never modifies the production ``RoutingDecision``;
- silent on missing model: returns ``None`` when no active Brain entry;
- failure-tolerant: any exception is swallowed (shadow is observability,
  not a critical path).

Span written to TraceStore::

    span_type = "brain_shadow_eval"
    name      = "brain.shadow_evaluation"
    attributes = {
        "brain_shadow.version_id":       str,
        "brain_shadow.production_agent": str | None,
        "brain_shadow.brain_agent":      str | None,
        "brain_shadow.agreement":        bool,
        "brain_shadow.score_divergence": float,
        "brain_shadow.top_k_overlap":    float,
        "brain_shadow.k":                int,
        "brain_shadow.num_candidates":   int,
    }
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from core.audit.trace_store import TraceStore

from ..agent_descriptor import AgentDescriptor
from ..performance_history import PerformanceHistoryStore
from ..routing_engine import RoutingDecision
from ..task_intent import TaskIntent
from .encoder import BrainStateEncoder
from .state import BrainPolicySignals, BrainState
from .trainer import BRAIN_FEATURE_NAMES, encode_brain_features

from ..learning.model_registry import (
    MODEL_KIND_BRAIN_V1,
    ModelRegistry,
)
from ..scoring_models import MLPScoringModel


class BrainShadowComparison(BaseModel):
    """Structured result of one Brain shadow evaluation pass."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    version_id: str = Field(description="ModelRegistry version_id of the Brain model")

    # Production decision (referenced for comparison only)
    production_agent_id: str | None = None
    production_score: float | None = None

    # Brain shadow decision
    brain_agent_id: str | None = None
    brain_score: float | None = None

    # Comparison metrics
    agreement: bool = Field(description="True when Brain top-1 == production top-1")
    score_divergence: float = Field(
        ge=0.0, le=1.0,
        description="|production_score - brain_score| clamped to [0,1]; 1.0 when either is absent",
    )
    top_k_overlap: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of top-k agent IDs shared between production and Brain rankings",
    )
    k: int = Field(ge=1)
    num_candidates: int = Field(ge=0)


class BrainShadowRunner:
    """Run the active Brain v1 model in shadow mode and record metrics.

    Parameters
    ----------
    registry:
        Canonical ``ModelRegistry``.  The active ``brain_v1`` entry is loaded
        on each ``evaluate()`` call.
    trace_store:
        Canonical ``TraceStore``.  The shadow span is written here.
    encoder:
        Optional ``BrainStateEncoder``.  Falls back to a default-configured
        instance.
    latency_scale_s / cost_scale_usd:
        Normalisation scales used when encoding feature vectors — must match
        the values used to train the artefact (default
        ``BrainTrainingJobConfig`` values).
    k:
        Number of top candidates considered for overlap calculation.
    """

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        trace_store: TraceStore,
        encoder: BrainStateEncoder | None = None,
        latency_scale_s: float = 10.0,
        cost_scale_usd: float = 0.01,
        k: int = 3,
    ) -> None:
        self.registry = registry
        self.trace_store = trace_store
        self.encoder = encoder or BrainStateEncoder(
            latency_scale_s=latency_scale_s,
            cost_scale_usd=cost_scale_usd,
        )
        self.latency_scale_s = latency_scale_s
        self.cost_scale_usd = cost_scale_usd
        self.k = max(1, k)

    def evaluate(
        self,
        intent: TaskIntent,
        descriptors: Sequence[AgentDescriptor],
        production_decision: RoutingDecision,
        *,
        trace_id: str,
        performance_history: PerformanceHistoryStore | None = None,
        policy: BrainPolicySignals | None = None,
    ) -> BrainShadowComparison | None:
        """Score *descriptors* with the active Brain model and record a span.

        Returns ``None`` when no active Brain entry exists, when the artefact
        cannot be loaded, or when the loaded model's feature schema does not
        match :data:`BRAIN_FEATURE_NAMES`.
        """
        entry = self.registry.get_active(model_kind=MODEL_KIND_BRAIN_V1)
        if entry is None:
            return None

        scorer = self.registry.get_active_brain_mlp()
        if scorer is None:
            return None

        if tuple(scorer.weights.feature_names) != BRAIN_FEATURE_NAMES:
            # Schema drift — refuse to score rather than emit garbage metrics.
            return None

        try:
            comparison = self._run(
                intent=intent,
                descriptors=descriptors,
                production_decision=production_decision,
                trace_id=trace_id,
                version_id=entry.version_id,
                scorer=scorer,
                performance_history=performance_history or PerformanceHistoryStore(),
                policy=policy,
            )
            self._write_span(comparison)
        except Exception:
            return None

        return comparison

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(
        self,
        *,
        intent: TaskIntent,
        descriptors: Sequence[AgentDescriptor],
        production_decision: RoutingDecision,
        trace_id: str,
        version_id: str,
        scorer: MLPScoringModel,
        performance_history: PerformanceHistoryStore,
        policy: BrainPolicySignals | None,
    ) -> BrainShadowComparison:
        state: BrainState = self.encoder.encode(
            intent,
            descriptors,
            performance_history,
            routing_decision=production_decision,
            policy=policy,
        )

        ranked = self._score_candidates(state, scorer)

        prod_agent = production_decision.selected_agent_id
        prod_score = production_decision.selected_score
        brain_agent, brain_score = (ranked[0] if ranked else (None, None))

        agreement = prod_agent is not None and prod_agent == brain_agent

        if prod_score is not None and brain_score is not None:
            score_divergence = min(abs(prod_score - brain_score), 1.0)
        else:
            score_divergence = 1.0

        k = self.k
        prod_top_k = {c.agent_id for c in production_decision.ranked_candidates[:k]}
        brain_top_k = {agent_id for agent_id, _ in ranked[:k]}
        if prod_top_k or brain_top_k:
            top_k_overlap = len(prod_top_k & brain_top_k) / max(
                len(prod_top_k | brain_top_k), 1
            )
        else:
            top_k_overlap = 1.0

        return BrainShadowComparison(
            trace_id=trace_id,
            version_id=version_id,
            production_agent_id=prod_agent,
            production_score=prod_score,
            brain_agent_id=brain_agent,
            brain_score=brain_score,
            agreement=agreement,
            score_divergence=score_divergence,
            top_k_overlap=top_k_overlap,
            k=k,
            num_candidates=len(state.candidates),
        )

    def _score_candidates(
        self,
        state: BrainState,
        scorer: MLPScoringModel,
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for candidate in state.candidates:
            vector = encode_brain_features(
                state,
                candidate,
                latency_scale_s=self.latency_scale_s,
                cost_scale_usd=self.cost_scale_usd,
            )
            scored.append((candidate.agent_id, scorer.forward(vector)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def _write_span(self, comparison: BrainShadowComparison) -> None:
        span = self.trace_store.start_span(
            comparison.trace_id,
            span_type="brain_shadow_eval",
            name="brain.shadow_evaluation",
            attributes={
                "brain_shadow.version_id": comparison.version_id,
                "brain_shadow.production_agent": comparison.production_agent_id,
                "brain_shadow.brain_agent": comparison.brain_agent_id,
                "brain_shadow.agreement": comparison.agreement,
                "brain_shadow.score_divergence": comparison.score_divergence,
                "brain_shadow.top_k_overlap": comparison.top_k_overlap,
                "brain_shadow.k": comparison.k,
                "brain_shadow.num_candidates": comparison.num_candidates,
            },
        )
        self.trace_store.add_event(
            span.span_id,
            event_type="brain_shadow_comparison",
            message=(
                f"brain={'match' if comparison.agreement else 'diverge'} "
                f"prod={comparison.production_agent_id!r} "
                f"brain={comparison.brain_agent_id!r} "
                f"divergence={comparison.score_divergence:.3f} "
                f"overlap={comparison.top_k_overlap:.3f}"
            ),
            payload=comparison.model_dump(mode="json"),
        )
        self.trace_store.finish_span(span.span_id, status="ok")


__all__ = [
    "BrainShadowComparison",
    "BrainShadowRunner",
]
