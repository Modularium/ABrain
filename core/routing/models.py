"""Canonical data models for the ABrain model-routing layer.

Phase 4 — "System-Level MoE und hybrides Modellrouting", Step M1.

This module defines the single source of truth for all model/provider
declarations in ABrain.  No routing logic lives here — only well-typed,
Pydantic-validated data contracts.

Design invariants
-----------------
- ``extra="forbid"`` on every model — governance fields must not drift silently.
- ``ModelPurpose`` is the canonical purpose taxonomy.  A model may serve
  multiple purposes but must declare at least one.
- ``ModelTier`` drives cost-sensitivity decisions — LOCAL is always preferred
  when quality requirements allow it.
- ``ModelDescriptor`` is the single declaration unit per model/provider
  variant.  No business logic — only declared facts.
- This layer is distinct from ``core/decision/routing_engine.py``, which
  routes tasks to *agents/adapters*.  This layer routes *AI reasoning steps*
  to *LLM models* — a different dimension of the dispatch problem.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelPurpose(StrEnum):
    """Intended purpose classification for a model.

    A model may be registered for multiple purposes.  The purpose list
    drives ``ModelRegistry.list_by_purpose()`` lookups and the routing
    layer's candidate selection.

    PLANNING
        Multi-step reasoning, plan generation, task decomposition.
        Typically requires a large context window and strong reasoning.
    CLASSIFICATION
        Mapping an input to a categorical output.  Speed and cost are
        more important than generation quality.
    RANKING
        Comparing and ordering candidates.  Often run locally with small
        embedding or cross-encoder models.
    RETRIEVAL_ASSIST
        Supporting retrieval operations: query rewriting, re-ranking,
        summary for RAG context.
    LOCAL_ASSIST
        Short, simple responses that can be handled by a local or small
        model — reducing cost and latency for routine tasks.
    SPECIALIST
        Domain-specific model with narrow but deep expertise.  Examples:
        code models, legal models, medical summarisers.
    """

    PLANNING = "planning"
    CLASSIFICATION = "classification"
    RANKING = "ranking"
    RETRIEVAL_ASSIST = "retrieval_assist"
    LOCAL_ASSIST = "local_assist"
    SPECIALIST = "specialist"


class ModelTier(StrEnum):
    """Cost/capability tier of a model.

    LOCAL
        Runs on-device or on local infrastructure.  Zero API cost.
        Typically lower quality for complex tasks.
    SMALL
        Small hosted model, low API cost, fast latency.
        Good for classification, ranking, simple assistance.
    MEDIUM
        Mid-sized hosted model.  Balanced cost and quality.
    LARGE
        Large hosted model.  Highest quality, highest cost and latency.
        Use only when task complexity demands it.
    """

    LOCAL = "local"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ModelProvider(StrEnum):
    """Provider of the model.

    ANTHROPIC   Anthropic (Claude family)
    OPENAI      OpenAI (GPT family)
    GOOGLE      Google (Gemini family)
    LOCAL       Local model (Ollama, llama.cpp, etc.)
    CUSTOM      Custom or third-party provider
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL = "local"
    CUSTOM = "custom"


class QuantizationMethod(StrEnum):
    """Declared quantization method of a local model artefact.

    These are declared facts about the artefact the operator placed on
    disk / in Ollama / in llama.cpp — ABrain does not run the conversion
    itself.  The enum covers the set of methods seen in practice for
    LOCAL-tier models; use ``CUSTOM`` for anything not covered.

    FP16 / INT8 / INT4
        Generic bitwidth labels (framework-agnostic).
    GGUF_Q4_K_M / GGUF_Q5_K_M / GGUF_Q8_0
        llama.cpp GGUF quantization schemes.
    AWQ / GPTQ
        Activation-aware / post-training weight quantization methods
        common in the vLLM/transformers ecosystem.
    CUSTOM
        Any other method; the ``notes`` field should describe it.
    """

    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"
    GGUF_Q4_K_M = "gguf_q4_k_m"
    GGUF_Q5_K_M = "gguf_q5_k_m"
    GGUF_Q8_0 = "gguf_q8_0"
    AWQ = "awq"
    GPTQ = "gptq"
    CUSTOM = "custom"


class DistillationMethod(StrEnum):
    """Declared distillation method used to produce a local model artefact.

    KD
        Standard knowledge distillation from a larger teacher.
    FITNETS
        FitNets-style intermediate-layer distillation.
    SELF_DISTILL
        Self-distillation (teacher and student share architecture).
    CUSTOM
        Any other method; the ``notes`` field should describe it.
    """

    KD = "kd"
    FITNETS = "fitnets"
    SELF_DISTILL = "self_distill"
    CUSTOM = "custom"


class QuantizationProfile(BaseModel):
    """Declared quantization lineage for a LOCAL-tier model artefact.

    Attached to ``ModelDescriptor.quantization``.  Pure declaration — no
    conversion or evaluation happens here.

    Attributes
    ----------
    method:
        Which quantization method produced this artefact.
    bits:
        Effective bitwidth (2–16).  For mixed-precision schemes declare
        the dominant weight bitwidth.
    baseline_model_id:
        Optional ``model_id`` of the unquantized baseline used as the
        quality-delta reference.  Does not have to be registered.
    quality_delta_vs_baseline:
        Observed quality change relative to ``baseline_model_id`` on
        ``evaluated_on``.  In [-1.0, 1.0]; negative values indicate a
        regression.  ``None`` means not yet evaluated.
    evaluated_on:
        Free-text slug identifying the eval set that produced the delta
        (e.g. ``"abrain-routing-eval-v3"``).
    notes:
        Free-text operator notes.  Not used for routing logic.
    """

    model_config = ConfigDict(extra="forbid")

    method: QuantizationMethod
    bits: int = Field(ge=2, le=16)
    baseline_model_id: str | None = Field(default=None, min_length=1, max_length=128)
    quality_delta_vs_baseline: float | None = Field(default=None, ge=-1.0, le=1.0)
    evaluated_on: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=1024)

    @field_validator("baseline_model_id", "evaluated_on")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty or whitespace-only")
        return stripped


class DistillationLineage(BaseModel):
    """Declared distillation lineage for a LOCAL-tier model artefact.

    Attached to ``ModelDescriptor.distillation``.  Pure declaration — no
    training happens here.

    Attributes
    ----------
    teacher_model_id:
        ``model_id`` of the teacher model used to distil this artefact.
        Required — a distillation lineage without a named teacher carries
        no provenance value.
    method:
        Which distillation method was used.
    quality_delta_vs_teacher:
        Observed quality change relative to the teacher on
        ``evaluated_on``.  In [-1.0, 1.0]; negative values indicate the
        student underperforms the teacher (usually expected).
    evaluated_on:
        Free-text slug identifying the eval set that produced the delta.
    notes:
        Free-text operator notes.  Not used for routing logic.
    """

    model_config = ConfigDict(extra="forbid")

    teacher_model_id: str = Field(min_length=1, max_length=128)
    method: DistillationMethod
    quality_delta_vs_teacher: float | None = Field(default=None, ge=-1.0, le=1.0)
    evaluated_on: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=1024)

    @field_validator("teacher_model_id")
    @classmethod
    def _strip_teacher(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("teacher_model_id must not be empty or whitespace-only")
        return stripped

    @field_validator("evaluated_on")
    @classmethod
    def _strip_evaluated_on(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("evaluated_on must not be empty or whitespace-only")
        return stripped


class ModelDescriptor(BaseModel):
    """Declared facts about a single model/provider variant.

    A ``ModelDescriptor`` is the canonical registration unit in
    ``ModelRegistry``.  It carries the purpose classification, cost and
    latency metadata, and capability flags needed for routing decisions.

    Attributes
    ----------
    model_id:
        Stable, unique slug for this model variant.
        Examples: ``"claude-opus-4-7"``, ``"gpt-4o"``, ``"llama-3-8b-local"``.
    display_name:
        Human-readable name for UI and audit display.
    provider:
        Which provider hosts/runs this model.
    purposes:
        Non-empty list of ``ModelPurpose`` values this model is suited for.
    tier:
        Cost/capability tier — used for cost-aware routing.
    context_window:
        Maximum context window in tokens.  None means unknown.
    cost_per_1k_tokens:
        Approximate cost in USD per 1,000 tokens (input + output averaged).
        None means unknown or free (always the case for LOCAL tier).
    p95_latency_ms:
        Observed 95th-percentile latency in milliseconds.  None means unknown.
    supports_tool_use:
        True if the model supports structured tool/function calls.
    supports_structured_output:
        True if the model supports constrained JSON / schema-guided output.
    is_available:
        Operator toggle — set to False to remove from routing without
        deregistering.
    quantization:
        Optional declared quantization profile.  Non-LOCAL tiers must not
        declare one (hosted models are not quantized by the operator).
    distillation:
        Optional declared distillation lineage.  Non-LOCAL tiers must not
        declare one.
    notes:
        Free-text operator notes.  Not used for routing logic.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    provider: ModelProvider
    purposes: list[ModelPurpose] = Field(min_length=1)
    tier: ModelTier
    context_window: int | None = Field(default=None, ge=1)
    cost_per_1k_tokens: float | None = Field(default=None, ge=0.0)
    p95_latency_ms: int | None = Field(default=None, ge=1)
    supports_tool_use: bool = False
    supports_structured_output: bool = False
    is_available: bool = True
    quantization: QuantizationProfile | None = None
    distillation: DistillationLineage | None = None
    notes: str | None = Field(default=None, max_length=1024)

    @field_validator("model_id", "display_name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty or whitespace-only")
        return stripped

    @field_validator("purposes")
    @classmethod
    def _deduplicate_purposes(cls, values: list[ModelPurpose]) -> list[ModelPurpose]:
        seen: set[ModelPurpose] = set()
        result: list[ModelPurpose] = []
        for v in values:
            if v not in seen:
                seen.add(v)
                result.append(v)
        return result

    @model_validator(mode="after")
    def _local_tier_no_cost(self) -> ModelDescriptor:
        if self.tier == ModelTier.LOCAL and self.cost_per_1k_tokens is not None:
            raise ValueError(
                "LOCAL tier models must not declare cost_per_1k_tokens "
                "(they run on local infrastructure with no API cost)."
            )
        return self

    @model_validator(mode="after")
    def _lineage_restricted_to_local_tier(self) -> ModelDescriptor:
        if self.tier != ModelTier.LOCAL:
            if self.quantization is not None:
                raise ValueError(
                    "quantization may only be declared on LOCAL tier models "
                    "(hosted models are not quantized by the operator)."
                )
            if self.distillation is not None:
                raise ValueError(
                    "distillation may only be declared on LOCAL tier models "
                    "(hosted models are not distilled by the operator)."
                )
        return self
