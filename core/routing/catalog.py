"""Default model catalog for ABrain hybrid model routing.

Phase 4 — "System-Level MoE und hybrides Modellrouting", Step M3.

Provides a curated list of ``ModelDescriptor`` entries covering all four tiers
(LOCAL, SMALL, MEDIUM, LARGE) across the canonical ``ModelPurpose`` taxonomy.

Design intent
-------------
*   LOCAL-tier entries are registered with ``is_available=False`` by default.
    Operators must explicitly enable them after deploying an inference backend
    (Ollama, llama.cpp, vLLM, etc.) and confirming the model is reachable.

*   SMALL-tier entries cover fast, cheap tasks: classification, ranking,
    retrieval assist, and short local-assist responses — the primary targets
    of the "lokale/kleine Modelle für Klassifikation, Ranking und Guardrails"
    roadmap requirement.

*   MEDIUM/LARGE entries cover complex planning and specialist work.

*   ``build_default_registry`` creates a fresh ``ModelRegistry`` populated with
    this catalog.  Pass ``enable_local=True`` to mark LOCAL models available
    (useful for integration tests or single-host deployments).

Governance notes
----------------
*   All LOCAL entries declare ``cost_per_1k_tokens=None`` (zero API cost) as
    required by the LOCAL-tier invariant in ``ModelDescriptor``.
*   Latency figures are observed p95 estimates; operators should update them
    via ``registry.deregister`` + re-registration with measured values.
*   The catalog is purely advisory — it does not auto-register anything.
    Callers must explicitly call ``build_default_registry()`` or iterate
    ``DEFAULT_MODELS`` themselves.
"""

from __future__ import annotations

from .models import ModelDescriptor, ModelProvider, ModelPurpose, ModelTier
from .registry import ModelRegistry

# ---------------------------------------------------------------------------
# LOCAL tier — on-device, zero API cost
# ---------------------------------------------------------------------------
# These require a local inference backend (Ollama, llama.cpp, vLLM, etc.).
# Marked is_available=False until the operator enables them.

_LOCAL: list[ModelDescriptor] = [
    ModelDescriptor(
        model_id="llama-3.2-1b-local",
        display_name="Llama 3.2 1B (local)",
        provider=ModelProvider.LOCAL,
        purposes=[ModelPurpose.CLASSIFICATION, ModelPurpose.LOCAL_ASSIST],
        tier=ModelTier.LOCAL,
        context_window=131072,
        p95_latency_ms=60,
        supports_tool_use=False,
        supports_structured_output=False,
        is_available=False,
        notes=(
            "1B parameter Llama model.  Fast on-device classification and "
            "guardrail evaluation.  Not recommended for multi-step planning."
        ),
    ),
    ModelDescriptor(
        model_id="llama-3.2-3b-local",
        display_name="Llama 3.2 3B (local)",
        provider=ModelProvider.LOCAL,
        purposes=[
            ModelPurpose.CLASSIFICATION,
            ModelPurpose.RANKING,
            ModelPurpose.LOCAL_ASSIST,
        ],
        tier=ModelTier.LOCAL,
        context_window=131072,
        p95_latency_ms=180,
        supports_tool_use=False,
        supports_structured_output=True,
        is_available=False,
        notes=(
            "3B parameter Llama model.  Good balance of local speed and quality "
            "for classification, ranking, and guardrail checks."
        ),
    ),
    ModelDescriptor(
        model_id="phi-3-mini-local",
        display_name="Phi-3 Mini (local)",
        provider=ModelProvider.LOCAL,
        purposes=[ModelPurpose.CLASSIFICATION, ModelPurpose.LOCAL_ASSIST],
        tier=ModelTier.LOCAL,
        context_window=128000,
        p95_latency_ms=80,
        supports_tool_use=False,
        supports_structured_output=True,
        is_available=False,
        notes=(
            "Microsoft Phi-3 Mini (3.8B).  Efficient on-device model with strong "
            "instruction-following for classification and guardrails."
        ),
    ),
]

# ---------------------------------------------------------------------------
# SMALL tier — low-cost hosted models
# ---------------------------------------------------------------------------

_SMALL: list[ModelDescriptor] = [
    ModelDescriptor(
        model_id="claude-haiku-4-5",
        display_name="Claude Haiku 4.5",
        provider=ModelProvider.ANTHROPIC,
        purposes=[
            ModelPurpose.CLASSIFICATION,
            ModelPurpose.LOCAL_ASSIST,
            ModelPurpose.RETRIEVAL_ASSIST,
            ModelPurpose.RANKING,
        ],
        tier=ModelTier.SMALL,
        context_window=200000,
        cost_per_1k_tokens=0.001,
        p95_latency_ms=800,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes=(
            "Fastest Anthropic model.  Primary choice for classification, ranking, "
            "retrieval assist, and guardrail evaluation in budget-sensitive pipelines."
        ),
    ),
    ModelDescriptor(
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider=ModelProvider.OPENAI,
        purposes=[
            ModelPurpose.CLASSIFICATION,
            ModelPurpose.LOCAL_ASSIST,
            ModelPurpose.RETRIEVAL_ASSIST,
        ],
        tier=ModelTier.SMALL,
        context_window=128000,
        cost_per_1k_tokens=0.0004,
        p95_latency_ms=600,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes="Low-cost OpenAI model for classification and retrieval assist.",
    ),
    ModelDescriptor(
        model_id="gemini-1.5-flash",
        display_name="Gemini 1.5 Flash",
        provider=ModelProvider.GOOGLE,
        purposes=[
            ModelPurpose.CLASSIFICATION,
            ModelPurpose.RETRIEVAL_ASSIST,
            ModelPurpose.RANKING,
        ],
        tier=ModelTier.SMALL,
        context_window=1000000,
        cost_per_1k_tokens=0.0002,
        p95_latency_ms=500,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes=(
            "Google's fast and cheap model.  Very long context window makes it "
            "particularly effective for retrieval assist and document ranking."
        ),
    ),
]

# ---------------------------------------------------------------------------
# MEDIUM tier — balanced cost/quality
# ---------------------------------------------------------------------------

_MEDIUM: list[ModelDescriptor] = [
    ModelDescriptor(
        model_id="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6",
        provider=ModelProvider.ANTHROPIC,
        purposes=[ModelPurpose.PLANNING, ModelPurpose.SPECIALIST],
        tier=ModelTier.MEDIUM,
        context_window=200000,
        cost_per_1k_tokens=0.009,
        p95_latency_ms=2000,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes="Balanced Anthropic model for multi-step planning and specialist tasks.",
    ),
    ModelDescriptor(
        model_id="gpt-4o",
        display_name="GPT-4o",
        provider=ModelProvider.OPENAI,
        purposes=[ModelPurpose.PLANNING, ModelPurpose.SPECIALIST],
        tier=ModelTier.MEDIUM,
        context_window=128000,
        cost_per_1k_tokens=0.010,
        p95_latency_ms=3000,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes="OpenAI's flagship model for complex planning and specialist reasoning.",
    ),
    ModelDescriptor(
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        provider=ModelProvider.GOOGLE,
        purposes=[ModelPurpose.PLANNING, ModelPurpose.RETRIEVAL_ASSIST],
        tier=ModelTier.MEDIUM,
        context_window=2000000,
        cost_per_1k_tokens=0.007,
        p95_latency_ms=2500,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes=(
            "Google's pro model with enormous context window — preferred for "
            "retrieval-augmented planning over very long documents."
        ),
    ),
]

# ---------------------------------------------------------------------------
# LARGE tier — highest quality
# ---------------------------------------------------------------------------

_LARGE: list[ModelDescriptor] = [
    ModelDescriptor(
        model_id="claude-opus-4-7",
        display_name="Claude Opus 4.7",
        provider=ModelProvider.ANTHROPIC,
        purposes=[ModelPurpose.PLANNING, ModelPurpose.SPECIALIST],
        tier=ModelTier.LARGE,
        context_window=200000,
        cost_per_1k_tokens=0.045,
        p95_latency_ms=5000,
        supports_tool_use=True,
        supports_structured_output=True,
        is_available=True,
        notes=(
            "Highest-quality Anthropic model.  Use only when task complexity "
            "demands maximum reasoning — highest cost and latency in catalog."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Public catalog surface
# ---------------------------------------------------------------------------

#: Complete flat list of all known model descriptors, ordered LOCAL → LARGE.
DEFAULT_MODELS: list[ModelDescriptor] = _LOCAL + _SMALL + _MEDIUM + _LARGE


def build_default_registry(*, enable_local: bool = False) -> ModelRegistry:
    """Populate a fresh ``ModelRegistry`` with all entries in ``DEFAULT_MODELS``.

    Parameters
    ----------
    enable_local:
        When ``True``, LOCAL-tier entries are registered as-is (preserving
        their ``is_available`` flag, which may still be ``False`` per entry).
        When ``False`` (default), LOCAL-tier entries are *skipped entirely* —
        they are not registered at all, keeping the registry free of phantom
        models that have no running backend.

        Pass ``True`` in integration tests or on single-host deployments where
        a local inference backend is confirmed to be running.

    Returns
    -------
    ModelRegistry
        A new registry containing the requested entries.  Idempotent: calling
        this function multiple times always returns an independent registry.
    """
    registry = ModelRegistry()
    for descriptor in DEFAULT_MODELS:
        if descriptor.tier == ModelTier.LOCAL and not enable_local:
            continue
        registry.register(descriptor)
    return registry
