"""Budget-aware model dispatcher with fallback cascades.

Phase 4 — "System-Level MoE und hybrides Modellrouting", Step M2.

``ModelDispatcher`` selects the best available model from ``ModelRegistry``
for a given ``ModelRoutingRequest``, respecting cost and latency budgets,
capability requirements, and a tier-ordered fallback cascade.

Dispatch algorithm
------------------
The dispatcher runs up to five selection passes, each relaxing constraints
further.  The first pass that yields at least one candidate wins.

Pass 1  strict     — purpose + availability + capabilities + cost + latency
Pass 2  no-latency — same as pass 1 but without the latency constraint
Pass 3  no-cost    — same as pass 1 but without the cost constraint
Pass 4  no-budget  — purpose + availability + capabilities only
Pass 5  no-caps    — purpose + availability only (last resort)

Within each pass, candidates are sorted:

1. LOCAL tier first when ``prefer_local=True``
2. Cost ascending (None = unknown, sorted last)
3. Latency ascending (None = unknown, sorted last)

The top candidate from the first winning pass is returned.
If no pass yields any candidate, ``NoModelAvailableError`` is raised.

Design invariants
-----------------
- Pure stateless function (``dispatch``) + thin class wrapper.
- No LLM calls, no network I/O, no side effects.
- Does NOT modify the registry or any descriptor.
- Distinct from ``core/decision/routing_engine.py`` (agent routing).
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ModelDescriptor, ModelProvider, ModelPurpose, ModelTier
from .registry import ModelRegistry


class NoModelAvailableError(RuntimeError):
    """Raised when no model in the registry satisfies the routing request.

    Analogous to ``RetrievalPolicyViolation`` in the retrieval layer.
    Callers should catch this explicitly rather than relying on a generic
    exception to distinguish a routing failure from a programming error.
    """

    def __init__(self, reason: str, request: ModelRoutingRequest) -> None:
        self.reason = reason
        self.request = request
        super().__init__(reason)


class ModelRoutingRequest(BaseModel):
    """Governance-aware model routing request.

    Attributes
    ----------
    purpose:
        The intended use of the selected model.
    max_cost_per_1k_tokens:
        Hard cost budget in USD per 1,000 tokens.  None = no budget limit.
    max_p95_latency_ms:
        Hard latency budget in milliseconds (p95).  None = no latency limit.
    require_tool_use:
        If True, only models with ``supports_tool_use=True`` are eligible.
    require_structured_output:
        If True, only models with ``supports_structured_output=True`` are eligible.
    prefer_local:
        Hint: prefer LOCAL-tier models when they satisfy all other constraints.
        Does not override hard budget or capability requirements.
    task_id:
        Optional task identifier for audit attribution.
    """

    model_config = ConfigDict(extra="forbid")

    purpose: ModelPurpose
    max_cost_per_1k_tokens: float | None = Field(default=None, ge=0.0)
    max_p95_latency_ms: int | None = Field(default=None, ge=1)
    require_tool_use: bool = False
    require_structured_output: bool = False
    prefer_local: bool = False
    task_id: str | None = Field(default=None, max_length=128)


class ModelRoutingResult(BaseModel):
    """Result of a completed model routing decision.

    Attributes
    ----------
    model_id:
        The selected model's stable identifier.
    provider:
        The provider of the selected model.
    tier:
        The cost/capability tier of the selected model.
    purposes:
        The purpose list of the selected model.
    fallback_used:
        True when one or more constraints were relaxed to find a candidate.
    fallback_reason:
        Description of which constraints were relaxed.  None when no fallback.
    selected_reason:
        Human-readable explanation of why this model was chosen.
    task_id:
        Echoed from the request for audit attribution.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str
    provider: ModelProvider
    tier: ModelTier
    purposes: list[ModelPurpose]
    fallback_used: bool = False
    fallback_reason: str | None = None
    selected_reason: str
    task_id: str | None = None


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class ModelDispatcher:
    """Select the best available model for a routing request.

    Usage
    -----
    >>> dispatcher = ModelDispatcher(registry)
    >>> result = dispatcher.dispatch(request)
    >>> result.model_id
    'claude-haiku-4-5'
    >>> result.fallback_used
    False
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def dispatch(self, request: ModelRoutingRequest) -> ModelRoutingResult:
        """Select the best model for *request* using the fallback cascade.

        Parameters
        ----------
        request:
            The validated ``ModelRoutingRequest``.

        Returns
        -------
        ModelRoutingResult
            The selected model with routing metadata.

        Raises
        ------
        NoModelAvailableError
            When no model in the registry satisfies any pass of the cascade.
        """
        return _dispatch(request, self._registry)


# ---------------------------------------------------------------------------
# Core dispatch logic (module-level for testability)
# ---------------------------------------------------------------------------

# Tier cost ordering for sort (lower = cheaper/preferred).
_TIER_ORDER: dict[ModelTier, int] = {
    ModelTier.LOCAL: 0,
    ModelTier.SMALL: 1,
    ModelTier.MEDIUM: 2,
    ModelTier.LARGE: 3,
}

# Sentinel for unknown cost/latency — sorts after known values.
_UNKNOWN_COST = math.inf
_UNKNOWN_LATENCY = math.inf


def _dispatch(request: ModelRoutingRequest, registry: ModelRegistry) -> ModelRoutingResult:
    """Execute the five-pass fallback cascade and return the best candidate."""
    # Base pool: purpose-matching, available models.
    base = [
        d for d in registry.list_by_purpose(request.purpose)
        if d.is_available
    ]

    passes: list[tuple[str, list[ModelDescriptor]]] = [
        ("strict", _apply_all(base, request)),
        ("relaxed latency constraint", _apply_no_latency(base, request)),
        ("relaxed cost constraint", _apply_no_cost(base, request)),
        ("relaxed budget constraints", _apply_no_budget(base, request)),
        ("relaxed capability requirements", _apply_no_caps(base, request)),
    ]

    for pass_name, candidates in passes:
        if candidates:
            best = _rank(candidates, request)[0]
            fallback = pass_name != "strict"
            return _make_result(
                best,
                request,
                fallback_used=fallback,
                fallback_reason=pass_name if fallback else None,
            )

    raise NoModelAvailableError(
        reason=(
            f"No model available for purpose='{request.purpose}' after all "
            f"fallback passes.  Register a suitable model in ModelRegistry."
        ),
        request=request,
    )


def _apply_caps(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    """Filter by tool-use and structured-output requirements."""
    result = candidates
    if request.require_tool_use:
        result = [d for d in result if d.supports_tool_use]
    if request.require_structured_output:
        result = [d for d in result if d.supports_structured_output]
    return result


def _apply_cost(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    """Filter by cost budget.  Models with unknown cost pass when no budget set."""
    if request.max_cost_per_1k_tokens is None:
        return candidates
    return [
        d for d in candidates
        if d.cost_per_1k_tokens is None  # unknown cost passes (LOCAL tier, etc.)
        or d.cost_per_1k_tokens <= request.max_cost_per_1k_tokens
    ]


def _apply_latency(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    """Filter by latency budget.  Models with unknown latency pass when no budget set."""
    if request.max_p95_latency_ms is None:
        return candidates
    return [
        d for d in candidates
        if d.p95_latency_ms is None  # unknown latency passes
        or d.p95_latency_ms <= request.max_p95_latency_ms
    ]


def _apply_all(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    return _apply_latency(_apply_cost(_apply_caps(candidates, request), request), request)


def _apply_no_latency(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    return _apply_cost(_apply_caps(candidates, request), request)


def _apply_no_cost(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    return _apply_latency(_apply_caps(candidates, request), request)


def _apply_no_budget(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    return _apply_caps(candidates, request)


def _apply_no_caps(
    candidates: list[ModelDescriptor], _request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    return list(candidates)


def _sort_key(
    descriptor: ModelDescriptor, prefer_local: bool
) -> tuple[int, int, float, float]:
    """Sort key: (local_penalty, tier, cost, latency) — lower is preferred."""
    local_bonus = 0 if (prefer_local and descriptor.tier == ModelTier.LOCAL) else 1
    tier = _TIER_ORDER[descriptor.tier]
    cost = descriptor.cost_per_1k_tokens if descriptor.cost_per_1k_tokens is not None else _UNKNOWN_COST
    latency = descriptor.p95_latency_ms if descriptor.p95_latency_ms is not None else _UNKNOWN_LATENCY
    return (local_bonus, tier, cost, latency)


def _rank(
    candidates: list[ModelDescriptor], request: ModelRoutingRequest
) -> list[ModelDescriptor]:
    """Sort candidates: prefer_local → tier → cost → latency."""
    return sorted(candidates, key=lambda d: _sort_key(d, request.prefer_local))


def _make_result(
    descriptor: ModelDescriptor,
    request: ModelRoutingRequest,
    *,
    fallback_used: bool,
    fallback_reason: str | None,
) -> ModelRoutingResult:
    parts: list[str] = [f"purpose={request.purpose!r}", f"tier={descriptor.tier!r}"]
    if fallback_used and fallback_reason:
        reason = f"Selected via fallback ({fallback_reason}): {', '.join(parts)}"
    else:
        reason = f"Best match: {', '.join(parts)}"
    return ModelRoutingResult(
        model_id=descriptor.model_id,
        provider=descriptor.provider,
        tier=descriptor.tier,
        purposes=list(descriptor.purposes),
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        selected_reason=reason,
        task_id=request.task_id,
    )
