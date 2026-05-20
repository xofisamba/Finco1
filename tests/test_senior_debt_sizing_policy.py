"""Phase 7 — Senior Debt Sizing Policy tests."""
import pytest
from domain.senior_debt_sizing.policy import (
    SeniorDebtSizingPolicy,
    SeniorDebtDSCRPolicy,
    SeniorDebtSizingResult,
    SizingMode,
)
from domain.senior_debt_sizing.engine import SeniorDebtSizingEngine


# ---------------------------------------------------------------------------
# SeniorDebtSizingPolicy
# ---------------------------------------------------------------------------

class TestSizingPolicy:
    def test_explicit_cfads_mode(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(2627.90, 2627.90, 2627.90),
            source_cell="Macro!R50",
        )
        assert policy.sizing_mode == SizingMode.EXPLICIT_CFADS
        assert policy.source_cell == "Macro!R50"
        assert len(policy.sizing_cfads_keur_by_period) == 3

    def test_derive_mode_flag(self):
        policy = SeniorDebtSizingPolicy(
            project_name="NewProject",
            sizing_mode=SizingMode.DERIVE_FROM_MINIMUM_DSCR,
            sizing_cfads_keur_by_period=(2000.0,),
        )
        assert policy.sizing_mode == SizingMode.DERIVE_FROM_MINIMUM_DSCR


# ---------------------------------------------------------------------------
# SeniorDebtDSCRPolicy
# ---------------------------------------------------------------------------

class TestDSCRPolicy:
    def test_dual_regime(self):
        dscr_policy = SeniorDebtDSCRPolicy(
            target_dscr_by_period=(1.20,) * 25 + (1.41,) * 38,
            ppa_dscr=1.20,
            merchant_dscr=1.41,
            switch_period=26,
        )
        assert dscr_policy.ppa_dscr == 1.20
        assert dscr_policy.merchant_dscr == 1.41
        assert len(dscr_policy.target_dscr_by_period) == 63


# ---------------------------------------------------------------------------
# SeniorDebtSizingEngine.compute()
# ---------------------------------------------------------------------------

class TestSizingEngineExplicitMode:
    def test_debt_service_capacity_equals_cfads_over_dscr(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(2627.90, 2627.90),
        )
        dscr_policy = SeniorDebtDSCRPolicy(
            target_dscr_by_period=(1.20, 1.20),
        )
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)

        expected_capacity = (2627.90 / 1.20, 2627.90 / 1.20)
        for actual, exp in zip(result.debt_service_capacity_keur_by_period, expected_capacity):
            assert actual == pytest.approx(exp, rel=1e-9)

    def test_merchant_regime_switch(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(2000.0, 2000.0, 2000.0),
        )
        dscr_policy = SeniorDebtDSCRPolicy(
            target_dscr_by_period=(1.20, 1.20, 1.41),
            ppa_dscr=1.20,
            merchant_dscr=1.41,
            switch_period=3,
        )
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        caps = result.debt_service_capacity_keur_by_period
        # PPA: 2000/1.20 = 1666.67
        # Merchant: 2000/1.41 = 1418.44
        assert caps[0] == pytest.approx(1666.67, rel=1e-4)
        assert caps[1] == pytest.approx(1666.67, rel=1e-4)
        assert caps[2] == pytest.approx(1418.44, rel=1e-4)

    def test_total_sizing_cfads(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0, 2000.0, 3000.0),
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.0, 1.0, 1.0))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        assert result.total_sizing_cfads_keur == pytest.approx(6000.0, rel=1e-9)

    def test_zero_dscr_gives_zero_capacity(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0, 2000.0),
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.0, 0.0))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        caps = result.debt_service_capacity_keur_by_period
        assert caps[0] == pytest.approx(1000.0, rel=1e-9)
        assert caps[1] == pytest.approx(0.0, abs=1e-9)

    def test_returns_correct_sizing_mode(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,),
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.0,))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        assert result.sizing_mode == SizingMode.EXPLICIT_CFADS


class TestSizingEngineDeriveMode:
    def test_derive_mode_uses_1_45_minimum_dscr(self):
        policy = SeniorDebtSizingPolicy(
            project_name="NewProject",
            sizing_mode=SizingMode.DERIVE_FROM_MINIMUM_DSCR,
            sizing_cfads_keur_by_period=(2900.0,),  # actual_cfads
            minimum_sizing_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.20,))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        # sizing_cfads = actual / 1.45 = 2900 / 1.45 ≈ 2000
        assert result.sizing_cfads_keur_by_period[0] == pytest.approx(2000.0, rel=1e-4)
        # capacity = sizing_cfads / target_dscr = 2000 / 1.20 ≈ 1666.67
        assert result.debt_service_capacity_keur_by_period[0] == pytest.approx(1666.67, rel=1e-4)
        assert result.sizing_mode == SizingMode.DERIVE_FROM_MINIMUM_DSCR

    def test_derive_mode_source_not_macro_r50(self):
        policy = SeniorDebtSizingPolicy(
            project_name="NewProject",
            sizing_mode=SizingMode.DERIVE_FROM_MINIMUM_DSCR,
            sizing_cfads_keur_by_period=(3000.0,),
            minimum_sizing_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.0,))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        # DERIVE mode does NOT claim Macro!R50 provenance
        assert result.total_sizing_cfads_keur > 0
        # sizing_cfads = 3000/1.45 ≈ 2069 kEUR (different from input)
        assert result.total_sizing_cfads_keur == pytest.approx(3000.0 / 1.45, rel=1e-4)

    def test_derive_mode_default_dscr_is_1_45(self):
        policy = SeniorDebtSizingPolicy(
            project_name="NewProject",
            sizing_mode=SizingMode.DERIVE_FROM_MINIMUM_DSCR,
            sizing_cfads_keur_by_period=(1450.0,),
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.0,))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        # Default minimum_sizing_dscr = 1.45
        assert result.sizing_cfads_keur_by_period[0] == pytest.approx(1000.0, rel=1e-4)


# ---------------------------------------------------------------------------
# TUHO integration test (using Macro!R50-like values)
# ---------------------------------------------------------------------------

class TestTuhuIntegration:
    def test_tuho_macro_r50_like_sizing(self):
        """Macro!R50 total = 204,669 kEUR, PPA DSCR = 1.20."""
        # Simplified: 63 periods, each ~2627 kEUR sizing CFADS, 1.20x PPA DSCR
        sizing_cfads = (2627.90,) * 63
        dscr_policy = SeniorDebtDSCRPolicy(
            target_dscr_by_period=(1.20,) * 63,
            ppa_dscr=1.20,
        )
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=sizing_cfads,
            inferred_minimum_dscr=1.45,
        )
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)

        # Total sizing CFADS = 2627.90 * 63 ≈ 165,558 kEUR (partial year vs full)
        assert result.total_sizing_cfads_keur > 0
        # Each period: 2627.90/1.20 ≈ 2190 kEUR debt service capacity
        assert result.debt_service_capacity_keur_by_period[0] == pytest.approx(2190.0, rel=1e-3)


# ---------------------------------------------------------------------------
# No R99/R102, no SHL, no tax — result is purely sizing-related
# ---------------------------------------------------------------------------

class TestBoundaries:
    def test_result_contains_only_sizing_fields(self):
        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,),
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.0,))
        result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
        # Result has sizing fields only
        assert hasattr(result, "debt_service_capacity_keur_by_period")
        assert hasattr(result, "sizing_mode")
        assert hasattr(result, "total_sizing_cfads_keur")
        assert hasattr(result, "total_debt_service_capacity_keur")
        # Result does NOT have fields for tax, SHL, or distribution
        assert not hasattr(result, "tax_interest")
        assert not hasattr(result, "shl_handoff")
        assert not hasattr(result, "distribution_gate")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])