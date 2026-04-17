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

__all__ = [
    "SourceTrust",
    "RetrievalScope",
    "KnowledgeSource",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievalBoundary",
    "RetrievalPolicyViolation",
]
