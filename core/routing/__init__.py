"""ABrain canonical model-routing layer — Phase 4.

Public surface:

    from core.routing import (
        ModelPurpose,
        ModelTier,
        ModelProvider,
        ModelDescriptor,
        ModelRegistry,
        RegistrationError,
        ModelRoutingRequest,
        ModelRoutingResult,
        ModelDispatcher,
        NoModelAvailableError,
        DEFAULT_MODELS,
        build_default_registry,
    )
"""

from .auditor import RoutingAuditor
from .catalog import DEFAULT_MODELS, build_default_registry
from .dispatcher import ModelDispatcher, ModelRoutingRequest, ModelRoutingResult, NoModelAvailableError
from .models import (
    DistillationLineage,
    DistillationMethod,
    ModelDescriptor,
    ModelProvider,
    ModelPurpose,
    ModelTier,
    QuantizationMethod,
    QuantizationProfile,
)
from .registry import ModelRegistry, RegistrationError

__all__ = [
    "ModelPurpose",
    "ModelTier",
    "ModelProvider",
    "ModelDescriptor",
    "QuantizationMethod",
    "QuantizationProfile",
    "DistillationMethod",
    "DistillationLineage",
    "ModelRegistry",
    "RegistrationError",
    "ModelRoutingRequest",
    "ModelRoutingResult",
    "ModelDispatcher",
    "NoModelAvailableError",
    "DEFAULT_MODELS",
    "build_default_registry",
    "RoutingAuditor",
]
