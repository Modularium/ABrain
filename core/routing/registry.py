"""Model/Provider registry — canonical authority for available models.

Phase 4 — "System-Level MoE und hybrides Modellrouting", Step M1.

``ModelRegistry`` is the single source of truth for which
``ModelDescriptor`` objects are available to the routing layer.  It
enforces governance invariants at registration time so that the router
only ever sees pre-validated, declared models.

Governance rules enforced at registration
-----------------------------------------
1. ``model_id`` must be unique — re-registering a different descriptor under
   the same id is rejected with ``RegistrationError``.  Idempotent
   re-registration of the *exact same* descriptor is a no-op.
2. Non-LOCAL models should declare ``cost_per_1k_tokens`` — without a cost
   signal, budget-aware routing cannot work correctly.
3. All models should declare ``p95_latency_ms`` — without a latency signal,
   latency-aware routing falls back to ordering by tier.

Both cost and latency gaps are advisory: registration succeeds, but warnings
are returned so operators can complete the metadata.

Design invariants
-----------------
- Pure in-process store, no persistence.  Persistence is a later concern.
- Thread-safety is *not* guaranteed; callers must synchronise if needed.
- ``extra="forbid"`` is on ``ModelDescriptor``, so invalid models are
  rejected before reaching this registry.
"""

from __future__ import annotations

from .models import ModelDescriptor, ModelProvider, ModelPurpose, ModelTier


class RegistrationError(ValueError):
    """Raised when a descriptor fails governance validation at registration time."""


class ModelRegistry:
    """Manage the set of available model/provider variants.

    Usage
    -----
    >>> registry = ModelRegistry()
    >>> registry.register(descriptor)          # raises RegistrationError on conflict
    >>> desc = registry.get("claude-opus-4-7") # raises KeyError if absent
    >>> all_models = registry.list_all()
    >>> planners = registry.list_by_purpose(ModelPurpose.PLANNING)
    >>> available = registry.list_available()
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelDescriptor] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, descriptor: ModelDescriptor) -> list[str]:
        """Register a model descriptor and return advisory warnings.

        Idempotent: registering the exact same ``ModelDescriptor`` object
        (same ``model_id`` AND same content) is a no-op and returns no warnings.

        Parameters
        ----------
        descriptor:
            The ``ModelDescriptor`` to register.

        Returns
        -------
        list[str]
            Advisory warnings (non-empty when metadata is incomplete).
            Registration succeeds even when warnings are returned.

        Raises
        ------
        RegistrationError
            When the ``model_id`` is already registered under a *different*
            descriptor.
        """
        existing = self._models.get(descriptor.model_id)
        if existing is not None:
            if existing == descriptor:
                return []
            raise RegistrationError(
                f"Model '{descriptor.model_id}' is already registered under a "
                f"different definition.  Deregister it first or use a new model_id."
            )

        self._models[descriptor.model_id] = descriptor
        return self._advisory_warnings(descriptor)

    def deregister(self, model_id: str) -> None:
        """Remove a descriptor from the registry.

        Raises
        ------
        KeyError
            When ``model_id`` is not registered.
        """
        if model_id not in self._models:
            raise KeyError(f"Model '{model_id}' is not registered.")
        del self._models[model_id]

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> ModelDescriptor:
        """Return the registered descriptor for ``model_id``.

        Raises
        ------
        KeyError
            When ``model_id`` is not registered.
        """
        try:
            return self._models[model_id]
        except KeyError:
            raise KeyError(f"Model '{model_id}' is not registered.")

    def is_registered(self, model_id: str) -> bool:
        """Return True if ``model_id`` is in the registry."""
        return model_id in self._models

    def list_all(self) -> list[ModelDescriptor]:
        """Return all registered descriptors in registration order."""
        return list(self._models.values())

    def list_available(self) -> list[ModelDescriptor]:
        """Return registered descriptors where ``is_available=True``."""
        return [d for d in self._models.values() if d.is_available]

    def list_by_purpose(self, purpose: ModelPurpose) -> list[ModelDescriptor]:
        """Return all registered descriptors that include *purpose*."""
        return [d for d in self._models.values() if purpose in d.purposes]

    def list_by_tier(self, tier: ModelTier) -> list[ModelDescriptor]:
        """Return all registered descriptors with the given *tier*."""
        return [d for d in self._models.values() if d.tier == tier]

    def list_by_provider(self, provider: ModelProvider) -> list[ModelDescriptor]:
        """Return all registered descriptors from the given *provider*."""
        return [d for d in self._models.values() if d.provider == provider]

    def __len__(self) -> int:
        return len(self._models)

    # ------------------------------------------------------------------
    # Internal governance checks
    # ------------------------------------------------------------------

    @staticmethod
    def _advisory_warnings(descriptor: ModelDescriptor) -> list[str]:
        """Return non-fatal advisory messages for the registered descriptor."""
        warnings: list[str] = []
        if descriptor.tier != ModelTier.LOCAL and descriptor.cost_per_1k_tokens is None:
            warnings.append(
                f"Model '{descriptor.model_id}' (tier={descriptor.tier!r}) has no "
                f"cost_per_1k_tokens declared.  Budget-aware routing will treat "
                f"this model as unknown cost."
            )
        if descriptor.p95_latency_ms is None:
            warnings.append(
                f"Model '{descriptor.model_id}' has no p95_latency_ms declared.  "
                f"Latency-aware routing will use tier ordering as a proxy."
            )
        return warnings
