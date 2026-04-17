"""ABrain canonical model-routing layer — Phase 4.

Public surface:

    from core.routing import (
        ModelPurpose,
        ModelTier,
        ModelProvider,
        ModelDescriptor,
        ModelRegistry,
        RegistrationError,
    )
"""

from .models import ModelDescriptor, ModelProvider, ModelPurpose, ModelTier
from .registry import ModelRegistry, RegistrationError

__all__ = [
    "ModelPurpose",
    "ModelTier",
    "ModelProvider",
    "ModelDescriptor",
    "ModelRegistry",
    "RegistrationError",
]
