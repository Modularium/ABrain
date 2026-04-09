"""Learning helpers for neural policy training."""

__all__ = [
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
    raise AttributeError(name)
