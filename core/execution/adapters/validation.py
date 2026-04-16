"""Manifest-driven input validation for execution adapters.

Phase 2 — "Eingabe-/Ausgabe-Schemas erzwingen".

``validate_required_metadata`` is a pure function that enforces the
``required_metadata_keys`` contract declared in an ``AdapterManifest``
against a specific ``AgentDescriptor``.

It is called automatically from ``BaseExecutionAdapter.validate()`` so
every adapter subclass benefits without reimplementing the check.

Design notes
------------
- Pure function: no side effects, no registry access, no singletons.
- Raises ``ValueError`` (same exception type as adapter-specific validate()
  checks) so callers see a uniform error surface.
- Error message names both the adapter and the descriptor, making log
  messages unambiguous in multi-agent executions.
- ``missing_metadata_keys`` is returned separately from the exception so
  the caller or a test can inspect the exact set of absent keys without
  parsing the message.
"""

from __future__ import annotations

from core.decision.agent_descriptor import AgentDescriptor
from core.execution.adapters.manifest import AdapterManifest


def missing_metadata_keys(
    manifest: AdapterManifest, descriptor: AgentDescriptor
) -> list[str]:
    """Return the required metadata keys absent from ``descriptor.metadata``.

    Returns an empty list when all required keys are present.

    Parameters
    ----------
    manifest:
        The adapter manifest declaring ``required_metadata_keys``.
    descriptor:
        The agent descriptor whose ``metadata`` dict is checked.
    """
    return [
        key
        for key in manifest.required_metadata_keys
        if key not in descriptor.metadata
    ]


def validate_required_metadata(
    manifest: AdapterManifest, descriptor: AgentDescriptor
) -> None:
    """Raise ``ValueError`` if any required metadata key is absent.

    Parameters
    ----------
    manifest:
        The adapter manifest declaring ``required_metadata_keys``.
    descriptor:
        The agent descriptor whose ``metadata`` dict is validated.

    Raises
    ------
    ValueError
        When one or more required keys are missing, with a message that
        names the adapter, the descriptor, and the absent keys.
    """
    absent = missing_metadata_keys(manifest, descriptor)
    if absent:
        raise ValueError(
            f"Adapter '{manifest.adapter_name}' requires metadata keys "
            f"{absent!r} but agent '{descriptor.agent_id}' is missing them."
        )
