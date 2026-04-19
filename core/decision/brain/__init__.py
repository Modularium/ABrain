"""Phase 6 – Brain v1: ABrain decision network layer."""

__all__ = [
    "BrainAgentSignal",
    "BrainBudget",
    "BrainOfflineTrainer",
    "BrainPolicySignals",
    "BrainRecord",
    "BrainRecordBuilder",
    "BrainState",
    "BrainStateEncoder",
    "BrainTarget",
    "BrainTrainingJobConfig",
    "BrainTrainingResult",
    "load_brain_records",
    "save_brain_records",
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
    if name in {"BrainOfflineTrainer", "BrainTrainingJobConfig", "BrainTrainingResult",
                "load_brain_records", "save_brain_records"}:
        from .trainer import (
            BrainOfflineTrainer,
            BrainTrainingJobConfig,
            BrainTrainingResult,
            load_brain_records,
            save_brain_records,
        )

        return {
            "BrainOfflineTrainer": BrainOfflineTrainer,
            "BrainTrainingJobConfig": BrainTrainingJobConfig,
            "BrainTrainingResult": BrainTrainingResult,
            "load_brain_records": load_brain_records,
            "save_brain_records": save_brain_records,
        }[name]
    raise AttributeError(name)
