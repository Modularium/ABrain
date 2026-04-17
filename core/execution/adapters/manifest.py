"""Adapter manifest — the canonical governance declaration for each adapter.

``AdapterManifest`` is the single self-contained declaration of everything
statically known about an execution adapter from a governance perspective:

- what it does (description)
- how it executes (capabilities — same object as the adapter's ``capabilities``
  class attribute, embedded here for a single-stop reference)
- how risky it is (risk_tier)
- what metadata keys the operator must supply (required_metadata_keys)
- what metadata keys it recognises but does not require (optional_metadata_keys)
- what policy scope the operator should assign to agents using this adapter
  (recommended_policy_scope)

One ``AdapterManifest`` instance is declared as a ``manifest`` class attribute
on every ``BaseExecutionAdapter`` subclass.  The registry exposes it via
``ExecutionAdapterRegistry.get_manifest_for()``.

Design invariants
-----------------
- Static structural facts only — never runtime health or live availability.
- ``manifest.capabilities`` is the same ``ExecutionCapabilities`` object as
  the adapter's standalone ``capabilities`` class attribute.
- ``extra="forbid"`` prevents silent drift of unknown governance fields.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from core.execution.provider_capabilities import ExecutionCapabilities
from core.execution.adapters.budget import AdapterBudget, IsolationRequirements


class RiskTier(StrEnum):
    """Risk classification for an execution adapter.

    Tiers map to the level of operator oversight recommended before deploying
    agents that use the adapter in production.

    LOW
        Internal tool dispatch, no network, tightly scoped domain actions.
        Operator review optional; automated policy is sufficient.
    MEDIUM
        Network calls to controlled workflow engines (Flowise, n8n).
        Operator review recommended for first deployment; ongoing automated
        policy is sufficient for steady-state.
    HIGH
        Local process execution or code-execution services with broad
        filesystem / network access (ClaudeCode, Codex, OpenHands).
        Operator review and explicit policy approval required before use in
        production.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdapterManifest(BaseModel):
    """Static governance declaration for one execution adapter.

    Attributes
    ----------
    adapter_name:
        Canonical short name matching ``BaseExecutionAdapter.adapter_name``.
    description:
        Human-readable one-line description of what the adapter does.
    capabilities:
        ``ExecutionCapabilities`` instance — same object as the adapter's
        ``capabilities`` class attribute.
    risk_tier:
        Risk classification for governance and operator approval.
    required_metadata_keys:
        ``AgentDescriptor.metadata`` keys that *must* be present for the
        adapter to function.  The adapter's ``validate()`` method will raise
        when any of these are absent.
    optional_metadata_keys:
        ``AgentDescriptor.metadata`` keys that the adapter recognises and uses
        when present, but does not require.
    recommended_policy_scope:
        Suggested policy scope tag to assign to agents using this adapter.
        ``None`` means no specific scope recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    adapter_name: str
    description: str
    capabilities: ExecutionCapabilities
    risk_tier: RiskTier

    required_metadata_keys: list[str] = Field(default_factory=list)
    """Metadata keys the adapter requires at validate() time."""

    optional_metadata_keys: list[str] = Field(default_factory=list)
    """Metadata keys the adapter recognises but does not require."""

    required_result_metadata_keys: list[str] = Field(default_factory=list)
    """``result.metadata`` keys the adapter guarantees on a successful result.

    ``validate_result()`` raises ``ValueError`` when any of these are absent
    from a ``success=True`` ``ExecutionResult``.  Error results are exempt
    because error paths may short-circuit before populating metadata.
    """

    recommended_policy_scope: str | None = None
    """Policy scope tag recommended for agents using this adapter."""

    budget: AdapterBudget = Field(default_factory=AdapterBudget)
    """Per-adapter soft budget ceilings.

    Exceeding a limit emits a warning on the ``ExecutionResult``.  None fields
    mean unconstrained.  Operators may tighten limits via policy overrides.
    """

    isolation: IsolationRequirements = Field(default_factory=IsolationRequirements)
    """Static isolation requirements for this adapter's deployment environment.

    These are governance declarations for operator review and policy matching.
    Runtime enforcement is at the infrastructure level (containers, seccomp,
    network policies).
    """
