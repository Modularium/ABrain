"""Learning helpers for neural policy training and offline LearningOps."""

__all__ = [
    # Online neural-policy training (pre-Phase-5)
    "load_dataset",
    "load_model",
    "OnlineUpdater",
    "RewardModel",
    "save_dataset",
    "save_model",
    "TrainingDataset",
    "TrainingMetrics",
    "TrainingSample",
    "NeuralTrainer",
    # Phase 5 – LearningOps offline schema
    "DatasetBuilder",
    "DataQualityFilter",
    "DatasetExporter",
    "ExportManifest",
    "LearningRecord",
    "ModelRegistry",
    "ModelVersionEntry",
    "OfflineTrainer",
    "OfflineTrainingResult",
    "QualityViolation",
    "ShadowComparison",
    "ShadowEvaluator",
    "TrainingJobConfig",
]


def __getattr__(name: str):
    if name in {"TrainingDataset", "TrainingSample"}:
        from .dataset import TrainingDataset, TrainingSample

        return {"TrainingDataset": TrainingDataset, "TrainingSample": TrainingSample}[name]
    if name == "RewardModel":
        from .reward_model import RewardModel

        return RewardModel
    if name == "OnlineUpdater":
        from .online_updater import OnlineUpdater

        return OnlineUpdater
    if name in {"NeuralTrainer", "TrainingMetrics"}:
        from .trainer import NeuralTrainer, TrainingMetrics

        return {"NeuralTrainer": NeuralTrainer, "TrainingMetrics": TrainingMetrics}[name]
    if name in {"save_dataset", "load_dataset", "save_model", "load_model"}:
        from .persistence import load_dataset, load_model, save_dataset, save_model

        return {
            "save_dataset": save_dataset,
            "load_dataset": load_dataset,
            "save_model": save_model,
            "load_model": load_model,
        }[name]
    if name == "LearningRecord":
        from .record import LearningRecord

        return LearningRecord
    if name in {"DatasetBuilder"}:
        from .dataset_builder import DatasetBuilder

        return DatasetBuilder
    if name in {"DataQualityFilter", "QualityViolation"}:
        from .quality import DataQualityFilter, QualityViolation

        return {"DataQualityFilter": DataQualityFilter, "QualityViolation": QualityViolation}[name]
    if name in {"DatasetExporter", "ExportManifest"}:
        from .exporter import DatasetExporter, ExportManifest

        return {"DatasetExporter": DatasetExporter, "ExportManifest": ExportManifest}[name]
    if name in {"OfflineTrainer", "OfflineTrainingResult", "TrainingJobConfig"}:
        from .offline_trainer import OfflineTrainer, OfflineTrainingResult, TrainingJobConfig

        return {
            "OfflineTrainer": OfflineTrainer,
            "OfflineTrainingResult": OfflineTrainingResult,
            "TrainingJobConfig": TrainingJobConfig,
        }[name]
    if name in {"ModelRegistry", "ModelVersionEntry"}:
        from .model_registry import ModelRegistry, ModelVersionEntry

        return {"ModelRegistry": ModelRegistry, "ModelVersionEntry": ModelVersionEntry}[name]
    if name in {"ShadowComparison", "ShadowEvaluator"}:
        from .shadow_evaluator import ShadowComparison, ShadowEvaluator

        return {"ShadowComparison": ShadowComparison, "ShadowEvaluator": ShadowEvaluator}[name]
    raise AttributeError(name)
