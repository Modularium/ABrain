"""ABrain canonical retrieval layer — Phase 3.

Public surface:

    from core.retrieval import (
        SourceTrust,
        RetrievalScope,
        KnowledgeSource,
        RetrievalQuery,
        RetrievalResult,
        RetrievalBoundary,
        RetrievalPolicyViolation,
        KnowledgeSourceRegistry,
        RegistrationError,
        RetrievalPort,
        InMemoryRetriever,
    )
"""

from .boundaries import RetrievalBoundary, RetrievalPolicyViolation
from .models import (
    KnowledgeSource,
    RetrievalQuery,
    RetrievalResult,
    RetrievalScope,
    SourceTrust,
)
from .registry import KnowledgeSourceRegistry, RegistrationError
from .retriever import InMemoryRetriever, RetrievalPort

__all__ = [
    "SourceTrust",
    "RetrievalScope",
    "KnowledgeSource",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievalBoundary",
    "RetrievalPolicyViolation",
    "KnowledgeSourceRegistry",
    "RegistrationError",
    "RetrievalPort",
    "InMemoryRetriever",
]
