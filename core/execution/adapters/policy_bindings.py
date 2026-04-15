"""Canonical default policy rules derived from adapter manifests.

Phase 2 — "jedem Tool/Adapter Policy-Regeln zuordnen".

Each execution adapter carries a governance-relevant ``AdapterManifest``
(S15).  ``policy_bindings`` derives canonical ``PolicyRule`` entries from
those manifests so that operators have a correct, ready-to-load starting
point for governance.

Design
------
- Pure derivation: ``build_default_rules_for_manifest()`` is a pure
  function.  No side effects, no registry mutation, no singleton.
- Based on risk tier:

  LOW (AdminBot)
      One allow rule scoped to the adapter's ``source_type``.

  MEDIUM (Flowise, n8n)
      Two rules: ``require_approval`` when ``external_side_effect=True``
      (priority 10) plus a baseline ``allow`` (priority 0).

  HIGH (ClaudeCode, Codex, OpenHands)
      One ``require_approval`` rule for all executions.

- ``get_all_adapter_default_rules()`` aggregates rules for the six
  canonical adapters.  The result is ready to pass directly to
  ``PolicyRegistry(rules=...)``.

- ``adapter_name`` from the manifest is used as ``source_type`` in the
  ``PolicyRule`` — these match the ``AgentSourceType`` string values.

Invariants
----------
- No ``PolicyRule`` ids are hard-coded across modules; callers must not
  depend on specific id strings.  Use the returned list as a unit.
- No production code (``PolicyEngine``, ``PolicyRegistry``) is modified.
  This module is a pure builder — callers decide how to load the rules.
"""

from __future__ import annotations

from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.governance.policy_models import PolicyRule


def build_default_rules_for_manifest(manifest: AdapterManifest) -> list[PolicyRule]:
    """Return the canonical default ``PolicyRule`` list for one adapter manifest.

    Rules are keyed by ``source_type = manifest.adapter_name``.

    Parameters
    ----------
    manifest:
        The ``AdapterManifest`` to derive rules from.

    Returns
    -------
    list[PolicyRule]
        One or two canonical rules; never empty.
    """
    src = manifest.adapter_name  # matches AgentSourceType string values
    scope = manifest.recommended_policy_scope or "general"

    if manifest.risk_tier == RiskTier.LOW:
        return [
            PolicyRule(
                id=f"default_{src}_allow",
                description=(
                    f"Default allow for {manifest.adapter_name} "
                    f"({scope}; risk: {manifest.risk_tier.value})."
                ),
                source_type=src,
                effect="allow",
                priority=0,
            )
        ]

    if manifest.risk_tier == RiskTier.MEDIUM:
        return [
            PolicyRule(
                id=f"default_{src}_external_require_approval",
                description=(
                    f"Require approval for {manifest.adapter_name} tasks "
                    f"with external side effects "
                    f"({scope}; risk: {manifest.risk_tier.value})."
                ),
                source_type=src,
                external_side_effect=True,
                effect="require_approval",
                priority=10,
            ),
            PolicyRule(
                id=f"default_{src}_allow",
                description=(
                    f"Default allow for {manifest.adapter_name} "
                    f"({scope}; risk: {manifest.risk_tier.value})."
                ),
                source_type=src,
                effect="allow",
                priority=0,
            ),
        ]

    # HIGH — require approval for all executions
    return [
        PolicyRule(
            id=f"default_{src}_require_approval",
            description=(
                f"Require approval for all {manifest.adapter_name} executions "
                f"({scope}; risk: {manifest.risk_tier.value})."
            ),
            source_type=src,
            effect="require_approval",
            priority=0,
        )
    ]


def get_all_adapter_default_rules() -> list[PolicyRule]:
    """Return the combined canonical default rules for all six adapters.

    Import-order is stable: adminbot → openhands → claude_code → codex →
    flowise → n8n.  The combined list is ready to pass to
    ``PolicyRegistry(rules=get_all_adapter_default_rules())``.
    """
    from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
    from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
    from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
    from core.execution.adapters.codex_adapter import CodexExecutionAdapter
    from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
    from core.execution.adapters.n8n_adapter import N8NExecutionAdapter

    rules: list[PolicyRule] = []
    for cls in (
        AdminBotExecutionAdapter,
        OpenHandsExecutionAdapter,
        ClaudeCodeExecutionAdapter,
        CodexExecutionAdapter,
        FlowiseExecutionAdapter,
        N8NExecutionAdapter,
    ):
        rules.extend(build_default_rules_for_manifest(cls.manifest))
    return rules
