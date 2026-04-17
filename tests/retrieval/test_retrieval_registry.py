"""Tests for Phase 3 R2: KnowledgeSourceRegistry.

Coverage:
1. register — happy path, idempotent re-registration, conflict detection
2. register — governance: EXTERNAL/UNTRUSTED without provenance rejected
3. register — advisory: PII without retention_days, EXTERNAL/UNTRUSTED without license
4. deregister — removes source; raises KeyError for unknown id
5. get — returns source; raises KeyError for unknown id
6. is_registered — True/False logic
7. list_all — returns all in insertion order
8. list_by_trust — filters correctly
9. __len__ — counts sources
"""

from __future__ import annotations

import pytest

from core.retrieval.models import KnowledgeSource, SourceTrust
from core.retrieval.registry import KnowledgeSourceRegistry, RegistrationError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source(**kwargs) -> KnowledgeSource:
    defaults = {
        "source_id": "src-test",
        "display_name": "Test Source",
        "trust": SourceTrust.TRUSTED,
        "source_type": "document",
    }
    defaults.update(kwargs)
    return KnowledgeSource.model_validate(defaults)


def _registry() -> KnowledgeSourceRegistry:
    return KnowledgeSourceRegistry()


# ---------------------------------------------------------------------------
# 1. register — happy path and idempotency
# ---------------------------------------------------------------------------


class TestRegisterHappyPath:
    def test_register_trusted_source_succeeds(self):
        reg = _registry()
        src = _source()
        warnings = reg.register(src)
        assert isinstance(warnings, list)

    def test_register_returns_no_warnings_for_clean_trusted(self):
        reg = _registry()
        src = _source()
        assert reg.register(src) == []

    def test_idempotent_reregistration_returns_empty_list(self):
        reg = _registry()
        src = _source()
        reg.register(src)
        result = reg.register(src)
        assert result == []

    def test_idempotent_reregistration_does_not_double_count(self):
        reg = _registry()
        src = _source()
        reg.register(src)
        reg.register(src)
        assert len(reg) == 1

    def test_conflict_raises_registration_error(self):
        reg = _registry()
        src1 = _source(display_name="Original")
        src2 = _source(display_name="Different")
        reg.register(src1)
        with pytest.raises(RegistrationError):
            reg.register(src2)

    def test_registration_error_message_mentions_source_id(self):
        reg = _registry()
        src1 = _source(display_name="Original")
        src2 = _source(display_name="Different")
        reg.register(src1)
        with pytest.raises(RegistrationError, match="src-test"):
            reg.register(src2)

    def test_registration_error_is_value_error(self):
        reg = _registry()
        src1 = _source(display_name="Original")
        src2 = _source(display_name="Different")
        reg.register(src1)
        with pytest.raises(ValueError):
            reg.register(src2)


# ---------------------------------------------------------------------------
# 2. register — governance hard rules
# ---------------------------------------------------------------------------


class TestRegisterGovernance:
    def test_external_without_provenance_raises(self):
        reg = _registry()
        src = _source(trust=SourceTrust.EXTERNAL)
        with pytest.raises(RegistrationError):
            reg.register(src)

    def test_untrusted_without_provenance_raises(self):
        reg = _registry()
        src = _source(trust=SourceTrust.UNTRUSTED)
        with pytest.raises(RegistrationError):
            reg.register(src)

    def test_external_with_provenance_succeeds(self):
        reg = _registry()
        src = _source(trust=SourceTrust.EXTERNAL, provenance="https://example.com")
        reg.register(src)  # must not raise

    def test_untrusted_with_provenance_succeeds(self):
        reg = _registry()
        src = _source(trust=SourceTrust.UNTRUSTED, provenance="https://example.com")
        reg.register(src)  # must not raise

    def test_internal_without_provenance_succeeds(self):
        reg = _registry()
        src = _source(trust=SourceTrust.INTERNAL)
        reg.register(src)  # must not raise

    def test_trusted_without_provenance_succeeds(self):
        reg = _registry()
        src = _source(trust=SourceTrust.TRUSTED)
        reg.register(src)  # must not raise

    def test_governance_error_mentions_trust_level(self):
        reg = _registry()
        src = _source(trust=SourceTrust.EXTERNAL)
        with pytest.raises(RegistrationError, match="EXTERNAL"):
            reg.register(src)

    def test_governance_error_mentions_provenance(self):
        reg = _registry()
        src = _source(trust=SourceTrust.UNTRUSTED)
        with pytest.raises(RegistrationError, match="provenance"):
            reg.register(src)


# ---------------------------------------------------------------------------
# 3. register — advisory warnings
# ---------------------------------------------------------------------------


class TestRegisterAdvisoryWarnings:
    def test_pii_without_retention_days_warns(self):
        reg = _registry()
        src = _source(pii_risk=True)
        warnings = reg.register(src)
        assert len(warnings) == 1
        assert "pii" in warnings[0].lower() or "retention" in warnings[0].lower()

    def test_pii_with_retention_days_no_warning(self):
        reg = _registry()
        src = _source(pii_risk=True, retention_days=30)
        warnings = reg.register(src)
        assert warnings == []

    def test_external_without_license_warns(self):
        reg = _registry()
        src = _source(trust=SourceTrust.EXTERNAL, provenance="https://example.com")
        warnings = reg.register(src)
        assert any("license" in w.lower() for w in warnings)

    def test_external_with_license_no_license_warning(self):
        reg = _registry()
        src = _source(
            trust=SourceTrust.EXTERNAL,
            provenance="https://example.com",
            license="Apache-2.0",
        )
        warnings = reg.register(src)
        assert not any("license" in w.lower() for w in warnings)

    def test_untrusted_without_license_warns(self):
        reg = _registry()
        src = _source(trust=SourceTrust.UNTRUSTED, provenance="https://example.com")
        warnings = reg.register(src)
        assert any("license" in w.lower() for w in warnings)

    def test_pii_and_external_no_license_two_warnings(self):
        reg = _registry()
        src = _source(
            trust=SourceTrust.EXTERNAL,
            provenance="https://example.com",
            pii_risk=True,
        )
        warnings = reg.register(src)
        assert len(warnings) == 2

    def test_trusted_clean_source_zero_warnings(self):
        reg = _registry()
        src = _source(trust=SourceTrust.TRUSTED)
        assert reg.register(src) == []


# ---------------------------------------------------------------------------
# 4. deregister
# ---------------------------------------------------------------------------


class TestDeregister:
    def test_deregister_removes_source(self):
        reg = _registry()
        src = _source()
        reg.register(src)
        reg.deregister("src-test")
        assert not reg.is_registered("src-test")

    def test_deregister_decrements_length(self):
        reg = _registry()
        reg.register(_source(source_id="a", display_name="A", trust=SourceTrust.TRUSTED, source_type="doc"))
        reg.register(_source(source_id="b", display_name="B", trust=SourceTrust.TRUSTED, source_type="doc"))
        reg.deregister("a")
        assert len(reg) == 1

    def test_deregister_unknown_raises_key_error(self):
        reg = _registry()
        with pytest.raises(KeyError):
            reg.deregister("nonexistent")

    def test_deregister_then_reregister_succeeds(self):
        reg = _registry()
        src = _source()
        reg.register(src)
        reg.deregister("src-test")
        reg.register(src)  # must not raise
        assert reg.is_registered("src-test")


# ---------------------------------------------------------------------------
# 5. get
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_returns_registered_source(self):
        reg = _registry()
        src = _source()
        reg.register(src)
        assert reg.get("src-test") == src

    def test_get_unknown_raises_key_error(self):
        reg = _registry()
        with pytest.raises(KeyError, match="src-test"):
            reg.get("src-test")

    def test_get_error_message_includes_source_id(self):
        reg = _registry()
        with pytest.raises(KeyError, match="missing-id"):
            reg.get("missing-id")


# ---------------------------------------------------------------------------
# 6. is_registered
# ---------------------------------------------------------------------------


class TestIsRegistered:
    def test_returns_true_for_registered(self):
        reg = _registry()
        reg.register(_source())
        assert reg.is_registered("src-test") is True

    def test_returns_false_for_unregistered(self):
        reg = _registry()
        assert reg.is_registered("src-test") is False

    def test_returns_false_after_deregister(self):
        reg = _registry()
        reg.register(_source())
        reg.deregister("src-test")
        assert reg.is_registered("src-test") is False


# ---------------------------------------------------------------------------
# 7. list_all
# ---------------------------------------------------------------------------


class TestListAll:
    def test_empty_registry_returns_empty_list(self):
        reg = _registry()
        assert reg.list_all() == []

    def test_returns_all_registered_sources(self):
        reg = _registry()
        a = _source(source_id="a", display_name="A", trust=SourceTrust.TRUSTED, source_type="doc")
        b = _source(source_id="b", display_name="B", trust=SourceTrust.INTERNAL, source_type="doc")
        reg.register(a)
        reg.register(b)
        result = reg.list_all()
        assert len(result) == 2

    def test_preserves_insertion_order(self):
        reg = _registry()
        ids = ["c", "a", "b"]
        for sid in ids:
            reg.register(_source(source_id=sid, display_name=sid, trust=SourceTrust.TRUSTED, source_type="doc"))
        assert [s.source_id for s in reg.list_all()] == ids

    def test_returns_copy_not_internal_dict_values(self):
        reg = _registry()
        reg.register(_source())
        result1 = reg.list_all()
        result2 = reg.list_all()
        assert result1 is not result2


# ---------------------------------------------------------------------------
# 8. list_by_trust
# ---------------------------------------------------------------------------


class TestListByTrust:
    def test_filters_by_trust_level(self):
        reg = _registry()
        trusted = _source(source_id="t", display_name="T", trust=SourceTrust.TRUSTED, source_type="doc")
        internal = _source(source_id="i", display_name="I", trust=SourceTrust.INTERNAL, source_type="doc")
        reg.register(trusted)
        reg.register(internal)
        assert reg.list_by_trust(SourceTrust.TRUSTED) == [trusted]
        assert reg.list_by_trust(SourceTrust.INTERNAL) == [internal]

    def test_returns_empty_list_for_absent_trust_level(self):
        reg = _registry()
        reg.register(_source(trust=SourceTrust.TRUSTED))
        assert reg.list_by_trust(SourceTrust.EXTERNAL) == []

    def test_returns_multiple_matching_sources(self):
        reg = _registry()
        for i in range(3):
            reg.register(_source(source_id=f"t{i}", display_name=f"T{i}", trust=SourceTrust.TRUSTED, source_type="doc"))
        assert len(reg.list_by_trust(SourceTrust.TRUSTED)) == 3


# ---------------------------------------------------------------------------
# 9. __len__
# ---------------------------------------------------------------------------


class TestLen:
    def test_empty_registry_len_zero(self):
        assert len(_registry()) == 0

    def test_len_increments_on_register(self):
        reg = _registry()
        reg.register(_source(source_id="a", display_name="A", trust=SourceTrust.TRUSTED, source_type="doc"))
        reg.register(_source(source_id="b", display_name="B", trust=SourceTrust.TRUSTED, source_type="doc"))
        assert len(reg) == 2

    def test_len_decrements_on_deregister(self):
        reg = _registry()
        reg.register(_source())
        reg.deregister("src-test")
        assert len(reg) == 0

    def test_idempotent_registration_does_not_change_len(self):
        reg = _registry()
        src = _source()
        reg.register(src)
        reg.register(src)
        assert len(reg) == 1
