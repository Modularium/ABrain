## Phase D Learning System Review

### Scope

Phase D adds the trainable learning path on top of the canonical decision and execution pipeline.

New learning files:

- `core/decision/learning/dataset.py`
- `core/decision/learning/reward_model.py`
- `core/decision/learning/online_updater.py`
- `core/decision/learning/trainer.py`
- `core/decision/learning/persistence.py`

Extended files:

- `core/decision/neural_policy.py`
- `core/decision/feedback_loop.py`
- `services/core.py`

### How The Learning Components Work Together

1. `OnlineUpdater` derives a `TrainingSample` from a completed execution.
2. `RewardModel` deterministically maps the execution outcome to a scalar reward.
3. `TrainingDataset` stores the resulting samples in a typed append-only collection.
4. `NeuralTrainer` pulls batches from the dataset and calls `NeuralPolicyModel.train_step(...)`.
5. `persistence.py` provides explicit save/load helpers for datasets and learned weights.

### Neural Policy Training

`NeuralPolicyModel` stays mandatory in routing. The model is always present through deterministic initialization and can be updated incrementally through `train_step(...)`. Runtime training changes the model source from deterministic initialization to `trained_runtime`.

### What Is Active In The Live Path

The live `run_task(...)` pipeline in `services/core.py` performs:

1. routing
2. execution
3. performance history update
4. online sample creation
5. periodic trainer invocation

This means the system does actively learn during normal executions, not only in offline tests.

### What Is Not Fully Wired Yet

- automatic dataset persistence is not enabled in the default runtime path
- automatic model persistence/loading is still an explicit helper concern
- no background trainer worker exists yet; training is small and inline

### Release Positioning

The learning system is part of the ABrain foundations release, but not yet a full production ML platform. It improves routing quality incrementally and safely, while leaving security boundaries unchanged and persistence explicit.

### Best-Effort Safety For Learning

Learning and training are now explicitly best-effort:

- `FeedbackLoop` contains failures inside the learning path and returns structured warnings
- `services/core.run_task(...)` also guards the feedback call so successful executions are still returned even if learning fails afterwards

This keeps the execution pipeline stable while preserving visibility through warnings and structured logs.

### Test Coverage

Phase D is covered by:

- `tests/decision/test_learning_dataset.py`
- `tests/decision/test_reward_model.py`
- `tests/decision/test_online_updater.py`
- `tests/decision/test_trainer.py`
- `tests/decision/test_neural_training_integration.py`
- `tests/services/test_run_task_pipeline.py`

The service pipeline test now explicitly verifies that a failing updater does not break `run_task(...)`.

### Recommended Follow-Up

The next sensible phase is controlled persistence and scheduled training, followed by broader execution-adapter coverage. The security boundary should remain unchanged: deterministic policy filtering first, neural ranking second.
