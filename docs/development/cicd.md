# CI/CD Pipeline

Diese Seite beschreibt den aktuell relevanten CI/CD-Zustand fuer den stabilisierten ABrain-Foundations-Stand.

## Relevante Workflows

Produktiv relevant fuer den neuen Kern sind derzeit vor allem:

- `.github/workflows/core-ci.yml`
- `.github/workflows/adminbot-security-gates.yml`
- `.github/workflows/docs.yml`

Weitere Workflows wie `ci-core.yml`, `ci-full.yml`, `deploy.yml`, `plugin-release.yml` oder `openhands-resolver.yml` bleiben im Repository, sind aber nicht die normative Referenz fuer den Foundations-Release.

## Foundations Gates

Der Foundations-Job prueft auf `push` und `pull_request` gegen `main` mindestens:

1. `tests/decision`
2. `tests/execution`
3. `tests/adapters`
4. `tests/core`
5. `tests/services`
6. `tests/integration/test_node_export.py`
7. `py_compile` fuer die neuen bzw. geaenderten Foundations-Dateien

Der AdminBot-Security-Workflow prueft weiterhin gezielt den gehaerteten AdminBot-/Core-Pfad.

## Ziel der Gates

Die CI soll Regressionen im neuen Kern frueh blockieren, ohne daraus eine zweite Architektur oder einen schweren Release-Prozess zu machen. Wichtig ist:

- Decision Layer regressiert nicht still
- Execution Layer regressiert nicht still
- Learning-Pfad regressiert nicht still
- der gehaertete Core bleibt bestehen

## Lokale Reproduktion

Die relevante Foundations-Suite laesst sich lokal mit denselben Gruppen starten:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/decision tests/execution tests/adapters tests/core tests/services \
  tests/integration/test_node_export.py
```

Die zugehoerige Syntaxpruefung:

```bash
.venv/bin/python -m py_compile \
  services/core.py \
  services/routing_agent/service.py \
  core/decision/__init__.py \
  core/decision/agent_creation.py \
  core/decision/agent_descriptor.py \
  core/decision/agent_registry.py \
  core/decision/candidate_filter.py \
  core/decision/capabilities.py \
  core/decision/feature_encoder.py \
  core/decision/feedback_loop.py \
  core/decision/neural_policy.py \
  core/decision/performance_history.py \
  core/decision/planner.py \
  core/decision/routing_engine.py \
  core/decision/scoring_models.py \
  core/decision/task_intent.py \
  core/decision/learning/dataset.py \
  core/decision/learning/online_updater.py \
  core/decision/learning/persistence.py \
  core/decision/learning/reward_model.py \
  core/decision/learning/trainer.py \
  core/execution/__init__.py \
  core/execution/execution_engine.py \
  core/execution/adapters/__init__.py \
  core/execution/adapters/base.py \
  core/execution/adapters/registry.py \
  core/execution/adapters/adminbot_adapter.py \
  core/execution/adapters/openhands_adapter.py \
  core/execution/adapters/claude_code_adapter.py \
  core/execution/adapters/codex_adapter.py \
  adapters/flowise/__init__.py \
  adapters/flowise/models.py \
  adapters/flowise/importer.py \
  adapters/flowise/exporter.py \
  adapters/adminbot/client.py \
  adapters/adminbot/service.py
```

## Grenzen

- Die aktuelle CI trainiert kein groesseres Modell offline.
- Es gibt noch keinen separaten Hintergrund-Worker fuer Learning.
- Legacy-Dokumente und historische Workflows koennen weiter im Repo liegen, sind aber fuer Release-Entscheidungen nicht massgeblich.
