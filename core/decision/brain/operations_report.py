"""Phase 6 – §6.3 Observability: compositional Brain operations report.

``BrainOperationsReport`` is a **read-only, compositional** surface that
bundles the two existing Phase 6 observational primitives into one operator
lagebericht:

- ``BrainBaselineAggregator`` (B6-S5) — Brain-vs-heuristic agreement /
  divergence metrics with a promote / observe / reject verdict.
- ``BrainSuggestionFeedBuilder`` (B6-S6) — the actionable disagreement feed,
  gated on the baseline verdict.

The reporter runs the aggregator first and passes its ``BrainBaselineReport``
into the feed builder as the gate, so a single ``generate()`` call produces a
coherent "what is Brain v1 currently telling us" snapshot.  Shared scan
parameters (``trace_limit``, ``workflow_filter``, ``version_filter``) are
applied identically to both so baseline and feed describe the same slice.

Strictly additive:

- no second TraceStore, no second model loader, no duplicate span scan
  implementation (both underlying primitives live on their own modules and
  are reused as-is);
- no writes to any store — all ``brain_shadow_eval`` reads are delegated to
  the two primitives;
- no ownership of the production ``RoutingDecision`` / policy / approval /
  execution path — suggestion-only contract of B6-S6 is preserved.

Stdlib only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.audit.trace_store import TraceStore

from .baseline_aggregator import BrainBaselineAggregator, BrainBaselineReport
from .suggestion_feed import BrainSuggestionFeed, BrainSuggestionFeedBuilder


class BrainOperationsReport(BaseModel):
    """Composed Brain operator lagebericht: baseline + gated suggestion feed."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    trace_limit: int = Field(ge=0)
    workflow_filter: str | None = None
    version_filter: str | None = None
    baseline: BrainBaselineReport
    suggestion_feed: BrainSuggestionFeed


class BrainOperationsReporter:
    """Compose ``BrainBaselineReport`` + gated ``BrainSuggestionFeed`` in one call.

    The reporter is a thin wiring layer over the two existing observational
    primitives.  It owns no span-scanning logic of its own.

    Parameters
    ----------
    trace_store:
        Canonical ``TraceStore``.  Handed to both underlying primitives;
        never written to.
    aggregator:
        Optional pre-configured ``BrainBaselineAggregator``.  When omitted a
        fresh one is constructed with its default promotion thresholds.  Pass
        an aggregator explicitly to use custom thresholds.
    feed_builder:
        Optional pre-configured ``BrainSuggestionFeedBuilder``.  When omitted
        a fresh builder is constructed with its default
        ``min_score_divergence = 0.0``.

    Notes
    -----
    Both injected components must have been constructed against the same
    ``trace_store`` as passed here — the reporter does not validate this to
    keep the wiring trivial.  Construct through the convenience defaults for
    the common case.
    """

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        aggregator: BrainBaselineAggregator | None = None,
        feed_builder: BrainSuggestionFeedBuilder | None = None,
    ) -> None:
        self.trace_store = trace_store
        self.aggregator = aggregator or BrainBaselineAggregator(trace_store=trace_store)
        self.feed_builder = feed_builder or BrainSuggestionFeedBuilder(trace_store=trace_store)

    def generate(
        self,
        *,
        trace_limit: int = 1000,
        workflow_filter: str | None = None,
        version_filter: str | None = None,
        max_feed_entries: int | None = None,
    ) -> BrainOperationsReport:
        """Run the aggregator, then the gated suggestion feed, and bundle both.

        Parameters
        ----------
        trace_limit:
            Applied identically to baseline and feed scans.
        workflow_filter / version_filter:
            Applied identically to both primitives.
        max_feed_entries:
            Optional cap passed to the feed builder's ``max_entries`` after
            the gate is evaluated.  Does not affect baseline metrics.
        """
        baseline = self.aggregator.aggregate(
            trace_limit=trace_limit,
            workflow_filter=workflow_filter,
            version_filter=version_filter,
        )
        suggestion_feed = self.feed_builder.build(
            trace_limit=trace_limit,
            workflow_filter=workflow_filter,
            version_filter=version_filter,
            baseline_report=baseline,
            max_entries=max_feed_entries,
        )
        return BrainOperationsReport(
            generated_at=datetime.now(UTC),
            trace_limit=trace_limit,
            workflow_filter=workflow_filter,
            version_filter=version_filter,
            baseline=baseline,
            suggestion_feed=suggestion_feed,
        )


__all__ = [
    "BrainOperationsReport",
    "BrainOperationsReporter",
]
