"""Registry and file loading helpers for runtime governance rules."""

from __future__ import annotations

import json
from pathlib import Path

from .policy_models import PolicyEvaluationContext, PolicyRule

_EFFECT_WEIGHT = {
    "allow": 0,
    "require_approval": 1,
    "deny": 2,
}


class PolicyRegistry:
    """Hold deterministic runtime governance rules."""

    def __init__(
        self,
        rules: list[PolicyRule] | None = None,
        *,
        path: str | Path | None = None,
    ) -> None:
        self.path = Path(path) if path else None
        self._rules: list[PolicyRule] = list(rules or [])
        if self.path is not None and self.path.exists() and not rules:
            self.load_policies(self.path)

    def load_policies(self, path: str | Path | None = None) -> list[PolicyRule]:
        """Load policy rules from JSON or YAML."""
        source = Path(path) if path else self.path
        if source is None:
            raise ValueError("load_policies requires a path")
        if not source.exists():
            self._rules = []
            self.path = source
            return []
        suffix = source.suffix.lower()
        if suffix == ".json":
            payload = json.loads(source.read_text(encoding="utf-8"))
        elif suffix in {".yml", ".yaml"}:
            try:
                import yaml
            except ModuleNotFoundError as exc:  # pragma: no cover - depends on env
                raise RuntimeError("YAML policy loading requires PyYAML") from exc
            payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"unsupported policy format: {source.suffix}")
        records = payload.get("policies") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            raise ValueError("policy file must contain a list or a {policies: [...]} object")
        self._rules = [PolicyRule.model_validate(item) for item in records]
        self.path = source
        return list(self._rules)

    def get_applicable_policies(self, context: PolicyEvaluationContext) -> list[PolicyRule]:
        """Return rules that match the flattened evaluation context."""
        applicable = [rule for rule in self._rules if self._matches(rule, context)]
        return sorted(
            applicable,
            key=lambda rule: (-rule.priority, -_EFFECT_WEIGHT[rule.effect], rule.id),
        )

    def list_rules(self) -> list[PolicyRule]:
        """Return the currently loaded rules."""
        return list(self._rules)

    def _matches(self, rule: PolicyRule, context: PolicyEvaluationContext) -> bool:
        if rule.capability is not None and rule.capability not in context.required_capabilities:
            return False
        if rule.agent_id is not None and rule.agent_id != context.agent_id:
            return False
        if rule.source_type is not None and rule.source_type != context.source_type:
            return False
        if rule.execution_kind is not None and rule.execution_kind != context.execution_kind:
            return False
        if rule.risk_level is not None and rule.risk_level != context.risk_level:
            return False
        if (
            rule.external_side_effect is not None
            and rule.external_side_effect != context.external_side_effect
        ):
            return False
        if rule.max_cost is not None:
            if context.estimated_cost is None or context.estimated_cost <= rule.max_cost:
                return False
        if rule.max_latency is not None:
            if context.estimated_latency is None or context.estimated_latency <= rule.max_latency:
                return False
        if rule.requires_local is not None:
            if context.is_local is None or context.is_local == rule.requires_local:
                return False
        return True
