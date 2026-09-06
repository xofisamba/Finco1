"""Phase C3 Correction F — accounting policy persistence, round-trip, cache-key tests."""
import pytest
from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.project_factories import create_default_solar_project, create_default_wind_project
from finco_core.inputs import project_inputs_to_dict, project_inputs_from_dict
from finco_core.inputs._models import hash_inputs_for_cache
from finco_core.inputs.accounting import (
    AccountingPolicyAuthority, AccountingPolicyConfig, LegalReservePolicy,
    BookCapitalizationTreatment,
)


def _round_trip(factory_fn):
    pi = factory_fn()
    d = project_inputs_to_dict(pi)
    return pi, d, project_inputs_from_dict(d)


class TestAccountingPersistence:
    def test_oborovo_serializes_accounting_policy(self):
        """Correction K/L: legal reserve authority SOURCE_PROVEN (kernel activated)."""
        _, d, _ = _round_trip(create_default_oborovo)
        apc_d = d.get("accounting_policy_config")
        assert apc_d is not None
        assert apc_d["book_capitalization_authority"] == "SOURCE_PROVEN"
        assert apc_d["legal_reserve_policy"]["enabled"] is True
        assert apc_d["legal_reserve_policy"]["cap_fraction"] == 0.10
        assert apc_d["legal_reserve_policy"]["authority"] == "SOURCE_PROVEN"
        assert apc_d["legal_reserve_authority"] == "SOURCE_PROVEN"
        assert apc_d["opening_re_authority"] == "SOURCE_PROVEN"

    def test_tuho_serializes_accounting_policy(self):
        """Correction K/L: TUHO legal reserve authority SOURCE_PROVEN (kernel activated)."""
        _, d, _ = _round_trip(create_default_tuho_wind1)
        apc_d = d.get("accounting_policy_config")
        assert apc_d is not None
        assert apc_d["book_capitalization_authority"] == "SOURCE_PROVEN"
        assert apc_d["legal_reserve_policy"]["enabled"] is True
        assert apc_d["legal_reserve_authority"] == "SOURCE_PROVEN"

    def test_solar_serializes_generic_accounting_policy(self):
        """Correction H: Solar now has explicit _GENERIC_CLEAN_ACCOUNTING_POLICY."""
        _, d, _ = _round_trip(create_default_solar_project)
        apc_d = d.get("accounting_policy_config")
        assert apc_d is not None
        assert apc_d["book_capitalization_authority"] == "UNRESOLVED"
        assert apc_d["preconstruction_retained_earnings_authority"] == "GENERIC_FINCO_POLICY"
        assert apc_d["preconstruction_retained_earnings_keur"] == 0.0
        assert apc_d["opening_re_authority"] == "GENERIC_FINCO_POLICY"
        assert apc_d["legal_reserve_authority"] == "UNRESOLVED"

    def test_wind_serializes_generic_accounting_policy(self):
        """Correction H: Wind now has explicit _GENERIC_CLEAN_ACCOUNTING_POLICY."""
        _, d, _ = _round_trip(create_default_wind_project)
        apc_d = d.get("accounting_policy_config")
        assert apc_d is not None
        assert apc_d["book_capitalization_authority"] == "UNRESOLVED"
        assert apc_d["preconstruction_retained_earnings_authority"] == "GENERIC_FINCO_POLICY"
        assert apc_d["preconstruction_retained_earnings_keur"] == 0.0
        assert apc_d["legal_reserve_authority"] == "UNRESOLVED"

    def test_oborovo_round_trip_preserves_source_proven_book_cap(self):
        pi, _, pi2 = _round_trip(create_default_oborovo)
        assert pi2.accounting_policy_config is not None
        assert pi2.accounting_policy_config.book_capitalization_authority == AccountingPolicyAuthority.SOURCE_PROVEN
        assert pi2.accounting_policy_config.legal_reserve_policy is not None
        assert pi2.accounting_policy_config.legal_reserve_policy.enabled is True
        assert pi2.accounting_policy_config.legal_reserve_policy.cap_fraction == 0.10
        assert pi2.accounting_policy_config.legal_reserve_policy.authority == AccountingPolicyAuthority.SOURCE_PROVEN

    def test_tuho_round_trip_preserves_source_proven_lr(self):
        pi, _, pi2 = _round_trip(create_default_tuho_wind1)
        assert pi2.accounting_policy_config is not None
        assert pi2.accounting_policy_config.legal_reserve_policy.enabled is True
        assert pi2.accounting_policy_config.legal_reserve_authority == AccountingPolicyAuthority.SOURCE_PROVEN

    def test_solar_round_trip_preserves_generic_policy(self):
        """Correction H: Solar round-trip preserves explicit generic policy."""
        _, _, pi2 = _round_trip(create_default_solar_project)
        assert pi2.accounting_policy_config is not None
        assert pi2.accounting_policy_config.book_capitalization_authority == AccountingPolicyAuthority.UNRESOLVED
        assert pi2.accounting_policy_config.preconstruction_retained_earnings_keur == 0.0
        assert pi2.accounting_policy_config.preconstruction_retained_earnings_authority == AccountingPolicyAuthority.GENERIC_FINCO_POLICY

    def test_backward_compat_old_payload_missing_field(self):
        """Old payloads without accounting_policy_config must deserialize to None."""
        pi = create_default_oborovo()
        d = project_inputs_to_dict(pi)
        # Simulate old payload
        d.pop("accounting_policy_config", None)
        pi2 = project_inputs_from_dict(d)
        assert pi2.accounting_policy_config is None

    def test_backward_compat_never_upgrades_to_source_proven(self):
        """A missing accounting_policy_config must NEVER become SOURCE_PROVEN."""
        pi = create_default_oborovo()
        d = project_inputs_to_dict(pi)
        d.pop("accounting_policy_config", None)
        pi2 = project_inputs_from_dict(d)
        # Must be None (not SOURCE_PROVEN)
        if pi2.accounting_policy_config is not None:
            assert pi2.accounting_policy_config.book_capitalization_authority != AccountingPolicyAuthority.SOURCE_PROVEN


class TestCacheKey:
    def test_different_accounting_policy_different_cache_key(self):
        import dataclasses
        pi = create_default_oborovo()
        pi_no_policy = dataclasses.replace(pi, accounting_policy_config=None)
        key1 = hash_inputs_for_cache(pi)
        key2 = hash_inputs_for_cache(pi_no_policy)
        assert key1 != key2, "Different accounting policy must produce different cache key"

    def test_same_inputs_same_cache_key(self):
        pi = create_default_oborovo()
        assert hash_inputs_for_cache(pi) == hash_inputs_for_cache(pi)

    def test_generic_policy_different_from_source_proven(self):
        import dataclasses
        pi = create_default_oborovo()
        generic_apc = AccountingPolicyConfig()  # all defaults = GENERIC_FINCO_POLICY
        pi_generic = dataclasses.replace(pi, accounting_policy_config=generic_apc)
        key1 = hash_inputs_for_cache(pi)
        key2 = hash_inputs_for_cache(pi_generic)
        assert key1 != key2


class TestCanonicalImports:
    def test_can_import_from_finco_core(self):
        from finco_core.inputs.accounting import (
            AccountingPolicyAuthority, BookCapitalizationTreatment,
            LegalReservePolicy, AccountingPolicyConfig,
        )
        assert AccountingPolicyAuthority.SOURCE_PROVEN.value == "SOURCE_PROVEN"
        assert BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value == "CAPITALIZE_FIXED_ASSET"

    def test_contracts_re_exports_same_classes(self):
        from finco_core.inputs.accounting import AccountingPolicyConfig as APC1
        from financial_engine.financial_statements.contracts import AccountingPolicyConfig as APC2
        assert APC1 is APC2, "Must be ONE class definition, not two"
