"""Phase 6 – Brain v1: ABrain decision network layer."""

__all__ = [
    "BRAIN_FEATURE_NAMES",
    "BrainAgentSignal",
    "BrainBudget",
    "BrainOfflineTrainer",
    "BrainPolicySignals",
    "BrainRecord",
    "BrainRecordBuilder",
    "BrainShadowComparison",
    "BrainShadowRunner",
    "BrainState",
    "BrainStateEncoder",
    "BrainTarget",
    "BrainTrainingJobConfig",
    "BrainTrainingResult",
    "encode_brain_features",
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
                "load_brain_records", "save_brain_records",
                "BRAIN_FEATURE_NAMES", "encode_brain_features"}:
        from .trainer import (
            BRAIN_FEATURE_NAMES,
            BrainOfflineTrainer,
            BrainTrainingJobConfig,
            BrainTrainingResult,
            encode_brain_features,
            load_brain_records,
            save_brain_records,
        )

        return {
            "BRAIN_FEATURE_NAMES": BRAIN_FEATURE_NAMES,
            "BrainOfflineTrainer": BrainOfflineTrainer,
            "BrainTrainingJobConfig": BrainTrainingJobConfig,
            "BrainTrainingResult": BrainTrainingResult,
            "encode_brain_features": encode_brain_features,
            "load_brain_records": load_brain_records,
            "save_brain_records": save_brain_records,
        }[name]
    if name in {"BrainShadowRunner", "BrainShadowComparison"}:
        from .shadow_runner import BrainShadowComparison, BrainShadowRunner

        return {
            "BrainShadowComparison": BrainShadowComparison,
            "BrainShadowRunner": BrainShadowRunner,
        }[name]
    raise AttributeError(name)
