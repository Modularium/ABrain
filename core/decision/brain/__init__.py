"""Phase 6 – Brain v1: ABrain decision network layer."""

__all__ = [
    "BrainAgentSignal",
    "BrainBudget",
    "BrainPolicySignals",
    "BrainRecord",
    "BrainRecordBuilder",
    "BrainState",
    "BrainStateEncoder",
    "BrainTarget",
]


def __getattr__(name: str):
    if name in {
        "BrainAgentSignal",
        "BrainBudget",
        "BrainPolicySignals",
        "BrainRecord",
        "BrainState",
        "BrainTarget",
    }:
        from .state import (
            BrainAgentSignal,
            BrainBudget,
            BrainPolicySignals,
            BrainRecord,
            BrainState,
            BrainTarget,
        )

        return {
            "BrainAgentSignal": BrainAgentSignal,
            "BrainBudget": BrainBudget,
            "BrainPolicySignals": BrainPolicySignals,
            "BrainRecord": BrainRecord,
            "BrainState": BrainState,
            "BrainTarget": BrainTarget,
        }[name]
    if name == "BrainStateEncoder":
        from .encoder import BrainStateEncoder

        return BrainStateEncoder
    if name == "BrainRecordBuilder":
        from .record_builder import BrainRecordBuilder

        return BrainRecordBuilder
    raise AttributeError(name)
