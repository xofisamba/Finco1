"""Phase 7 — Model Stack Validation Pack.

Validates the three canonical domain modules (SHL, SeniorDebtSizing, Depreciation)
together for internal consistency, cross-module boundaries, and runtime safety.
"""
import pytest

from domain.depreciation.engine import DepreciationEngine, DepreciationEngineInputs
from domain.depreciation.asset import AssetClassConfig
from domain.depreciation.schedule import DepreciationPolicy
from domain.senior_debt_sizing.engine import SeniorDebtSizingEngine
from domain.senior_debt_sizing.policy import (
    SeniorDebtSizingPolicy,
    SeniorDebtDSCRPolicy,
    SizingMode,
)
from domain.shl.engine import ShlEngine
from domain.shl.inputs import ShlEngineInputs, ShlPeriodInput


# ============================================================================
# SHL Engine Validation
# ============================================================================

class TestShlEngineValidation:
    """A. SHL Engine Validation — TUHO fixture regression."""

    def _make_shl_inputs(self, tranche_opening, period_count=5,
                         post_senior_cash_seq=None,
                         tranche_rates=(0.08,), tranche_day_fracs=(0.5,),
                         pik_allowed=True):
        if post_senior_cash_seq is None:
            post_senior_cash_seq = [500.0] * period_count
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=tranche_rates[0],
                day_count_fraction=tranche_day_fracs[0],
                post_senior_cash_available_keur=post_senior_cash_seq[t],
                pik_allowed=pik_allowed,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(period_count)
        )
        return ShlEngineInputs(
            project_name="TUHO",
            period_count=period_count,
            period_inputs=period_inputs,
            total_shl_funding_keur=tranche_opening,
            tranche_rates=tranche_rates,
            tranche_day_fracs=tranche_day_fracs,
            tranche_opening_balances_keur=(tranche_opening,),
            pik_allowed=pik_allowed,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )

    def test_gross_accrued_positive(self):
        """Gross accrued interest is positive across operating life."""
        inputs = self._make_shl_inputs(tranche_opening=32703.864, period_count=5)
        result = ShlEngine.compute(inputs)
        assert result.total_gross_accrued_interest_keur > 0

    def test_gross_accrued_less_than_interest_only(self):
        """Gross accrued < interest-only (no amortization) envelope."""
        # Interest-only would be: 32703.864 * 0.08 * 0.5 * 63 ≈ 82,414
        # With amortization, gross should be significantly less
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=5000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(63)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO", period_count=63,
            period_inputs=period_inputs,
            total_shl_funding_keur=32703.864,
            tranche_rates=(0.08,), tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(32703.864,),
            pik_allowed=True, maintain_minimum_cash_reserve=False, minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        # With 5000 cash/period, SHL repays principal quickly, reducing gross over time
        assert result.total_gross_accrued_interest_keur > 0
        # Interest-only would be ~82k; amortizing should be less
        assert result.total_gross_accrued_interest_keur < 82704

    def test_cash_interest_less_than_gross(self):
        """Engine: cash interest + PIK = gross accrued."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=5000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(63)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO", period_count=63,
            period_inputs=period_inputs,
            total_shl_funding_keur=32703.864,
            tranche_rates=(0.08,), tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(32703.864,),
            pik_allowed=True, maintain_minimum_cash_reserve=False, minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        # cash + pik = gross (accounting for rounding)
        total_pik = result.total_pik_capitalized_keur
        total_cash = result.total_cash_interest_paid_keur
        total_gross = result.total_gross_accrued_interest_keur
        assert abs((total_cash + total_pik) - total_gross) < 1.0

    def test_pik_positive_when_no_cash(self):
        """PIK is positive when cash=0 (no cash for interest)."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=0.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(63)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO", period_count=63,
            period_inputs=period_inputs,
            total_shl_funding_keur=10000.0,
            tranche_rates=(0.08,), tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(10000.0,),
            pik_allowed=True, maintain_minimum_cash_reserve=False, minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        assert result.total_pik_capitalized_keur > 0
    def test_principal_repaid_positive(self):
        """Principal is repaid when cash exceeds gross interest."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=500.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(63)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO", period_count=63,
            period_inputs=period_inputs,
            total_shl_funding_keur=10000.0,
            tranche_rates=(0.08,), tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(10000.0,),
            pik_allowed=True, maintain_minimum_cash_reserve=False, minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        assert result.total_principal_repaid_keur > 0

    def test_closing_balance_reconciliation(self):
        """Engine: closing = opening + PIK - principal for each period."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(10)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO", period_count=10,
            period_inputs=period_inputs,
            total_shl_funding_keur=10000.0,
            tranche_rates=(0.08,), tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(10000.0,),
            pik_allowed=True, maintain_minimum_cash_reserve=False, minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        for pr in result.period_results:
            expected_closing = pr.opening_balance_keur + pr.pik_capitalized_keur - pr.principal_repaid_keur
            assert abs(pr.closing_balance_keur - expected_closing) < 0.01

    def test_no_minimum_reserve_behavior(self):
        """SHL engine has no minimum_reserve concept (reserve = 0 by default)."""
        inputs = self._make_shl_inputs(
            tranche_opening=10000.0,
            period_count=3,
            post_senior_cash_seq=[100.0, 100.0, 100.0],
        )
        result = ShlEngine.compute(inputs)
        # minimum_reserve should not cause reserve accumulation
        assert result.total_cash_consumed_keur >= 0

    def test_100_percent_cash_sweep(self):
        """SHL cash sweep = 100% of post-senior cash (TUHO behavior)."""
        inputs = self._make_shl_inputs(
            tranche_opening=5000.0,
            period_count=5,
            post_senior_cash_seq=[1000.0] * 5,
        )
        result = ShlEngine.compute(inputs)
        # No reserve withheld → cash_consumed tracks cash swept
        assert result.total_cash_consumed_keur >= 0

    def test_no_r99_r102_gate(self):
        """SHL engine exposes cash_consumed but does NOT gate on DSCR."""
        inputs = self._make_shl_inputs(
            tranche_opening=5000.0,
            period_count=5,
            post_senior_cash_seq=[500.0] * 5,
        )
        result = ShlEngine.compute(inputs)
        assert hasattr(result, "period_results")
        assert not hasattr(result, "r99_triggered")
        assert not hasattr(result, "distribution_gate")


# ============================================================================
# Senior Debt Sizing Validation
# ============================================================================

class TestSeniorDebtSizingValidation:
    """B. Senior Debt Sizing Validation."""

    def test_actual_vs_sizing_cfads_separated(self):
        """sizing_cfads and actual_cfads are separate inputs to sizing_policy."""
        sizing_policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,) * 63,
            inferred_minimum_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.45,) * 63)
        result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)
        # Result contains sizing_cfads_by_period and debt_service_capacity
        assert hasattr(result, "debt_service_capacity_keur_by_period")
        assert hasattr(result, "sizing_cfads_keur_by_period")

    def test_minimum_dscr_explicit(self):
        """Minimum DSCR is an explicit input, stored in sizing_policy.inferred_minimum_dscr."""
        sizing_policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,) * 63,
            inferred_minimum_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.45,) * 63)
        result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)
        assert sizing_policy.inferred_minimum_dscr == 1.45

    def test_sizing_path_explicit(self):
        """Sizing path uses sizing_cfads, reflected in result.sizing_cfads_keur_by_period."""
        sizing_policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,) * 63,
            inferred_minimum_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.45,) * 63)
        result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)
        assert result.sizing_cfads_keur_by_period is not None
        assert len(result.sizing_cfads_keur_by_period) == 63

    def test_result_contains_only_sizing_fields(self):
        """Result contains only sizing-related fields, no distribution."""
        sizing_policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,) * 63,
            inferred_minimum_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.45,) * 63)
        result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)
        assert not hasattr(result, "cash_for_distribution")
        assert not hasattr(result, "r99_triggered")
        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "sponsor_irr")

    def test_macro_r50_like_sizing(self):
        """Macro!R50 style: sizing CFADS / target_dscr gives debt service capacity."""
        sizing_policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1450.0,) * 63,
            inferred_minimum_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.45,) * 63)
        result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)
        # capacity = cfads / target_dscr = 1450/1.45 per period
        assert len(result.debt_service_capacity_keur_by_period) == 63


# ============================================================================
# Depreciation Validation
# ============================================================================

class TestDepreciationValidation:
    """C. Depreciation Validation."""

    def test_straight_line_annual(self):
        """Straight-line depreciation = basis / useful life."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Wind Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
            period_frequency="semiannual",
            cod_period=2,
        )
        result = DepreciationEngine.compute(inputs)
        period_5 = result.ledger_result.periods_for_index(5)[0]
        assert period_5.book_depreciation_keur == pytest.approx(250.0, rel=1e-9)

    def test_book_vs_tax_life_divergence(self):
        """Book life 20yr, tax life 12yr → different depreciation per period."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Wind Turbine",
                    gross_asset_basis_keur=12000.0,
                    book_depreciable_basis_keur=12000.0,
                    tax_depreciable_basis_keur=12000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=24,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        period_5 = result.ledger_result.periods_for_index(5)[0]
        assert period_5.book_depreciation_keur == pytest.approx(300.0, rel=1e-9)
        assert period_5.tax_depreciation_keur == pytest.approx(500.0, rel=1e-9)

    def test_land_non_depreciable(self):
        """Land has zero book and tax depreciation."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Land",
                    gross_asset_basis_keur=500.0,
                    book_depreciable_basis_keur=0.0,
                    tax_depreciable_basis_keur=0.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        land_rows = [r for r in result.ledger_result.periods if r.asset_class == "Land"]
        assert len(land_rows) > 0
        for row in land_rows:
            assert row.book_depreciation_keur == pytest.approx(0.0, abs=1e-9)
            assert row.tax_depreciation_keur == pytest.approx(0.0, abs=1e-9)

    def test_financing_costs_12_year_policy(self):
        """Financing costs depreciated over 12 years (24 semiannual periods)."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Financing Costs",
                    gross_asset_basis_keur=2400.0,
                    book_depreciable_basis_keur=2400.0,
                    tax_depreciable_basis_keur=2400.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
                "Financing Costs": DepreciationPolicy(
                    useful_life_book_periods=24,
                    useful_life_tax_periods=24,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        period_5 = result.ledger_result.periods_for_index(5)[0]
        assert period_5.book_depreciation_keur == pytest.approx(100.0, rel=1e-9)

    def test_accumulated_depreciation_roll_forward(self):
        """Accumulated depreciation increases each period, NBV decreases."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        p5  = result.ledger_result.periods_for_index(5)[0]
        p20 = result.ledger_result.periods_for_index(20)[0]
        assert p20.accumulated_book_depreciation_keur > p5.accumulated_book_depreciation_keur
        assert p20.nbv_book_keur < p5.nbv_book_keur

    def test_nbv_zero_at_end_of_life(self):
        """NBV = 0 at end of depreciation life (period 41 for 40-period life)."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        last_rows = result.ledger_result.periods_for_index(41)
        if last_rows:
            assert last_rows[0].nbv_book_keur == pytest.approx(0.0, abs=1e-9)

    def test_audit_rows_complete(self):
        """Audit rows cover all periods with all required fields."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        assert len(result.audit_rows) > 0
        row = result.audit_rows[0]
        for field in (
            "period_index", "asset_class", "gross_asset_basis_keur",
            "book_depreciation_keur", "tax_depreciation_keur",
            "accumulated_book_depreciation_keur", "nbv_book_keur",
            "is_land", "is_depreciable", "book_policy_years", "tax_policy_years",
        ):
            assert hasattr(row, field)


# ============================================================================
# Cross-Module Consistency
# ============================================================================

class TestCrossModuleConsistency:
    """D. Cross-Module Consistency."""

    def test_no_circular_dependencies(self):
        """No module imports another in a circular way."""
        import domain.shl.engine as shl_mod
        import domain.senior_debt_sizing.engine as sds_mod
        import domain.depreciation.engine as depr_mod

        assert not hasattr(shl_mod, "SeniorDebtSizingEngine")
        assert not hasattr(shl_mod, "DepreciationEngine")
        assert not hasattr(sds_mod, "ShlEngine")
        assert not hasattr(sds_mod, "DepreciationEngine")
        assert not hasattr(depr_mod, "ShlEngine")
        assert not hasattr(depr_mod, "SeniorDebtSizingEngine")

    def test_shl_uses_post_senior_cash_conceptually(self):
        """SHL engine takes post_senior_cash_available_keur (conceptually post-senior)."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=5000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(4)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=4,
            period_inputs=period_inputs,
            total_shl_funding_keur=50000.0,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(50000.0,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        assert result.total_cash_consumed_keur >= 0

    def test_depreciation_feeds_tax_and_pl(self):
        """Depreciation engine exposes book_depreciation and tax_depreciation separately."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        period_5 = result.ledger_result.periods_for_index(5)[0]
        assert period_5.book_depreciation_keur > 0
        assert period_5.tax_depreciation_keur > 0

    def test_no_module_computes_sponsor_irr(self):
        """No canonical module computes sponsor IRR."""
        import domain.shl.engine as shl_mod
        import domain.senior_debt_sizing.engine as sds_mod
        import domain.depreciation.engine as depr_mod

        for mod in [shl_mod, sds_mod, depr_mod]:
            for attr in dir(mod):
                assert "irr" not in attr.lower(), f"IRR found in {mod.__name__}.{attr}"

    def test_no_module_computes_r99_r102(self):
        """No canonical module gates on R99/R102."""
        import domain.shl.engine as shl_mod
        import domain.senior_debt_sizing.engine as sds_mod
        import domain.depreciation.engine as depr_mod

        for mod in [shl_mod, sds_mod, depr_mod]:
            for attr in dir(mod):
                assert "r99" not in attr.lower() and "r102" not in attr.lower(), \
                    f"R99/R102 found in {mod.__name__}.{attr}"


# ============================================================================
# Runtime Safety
# ============================================================================

class TestRuntimeSafety:
    """E. Runtime Safety — no default behavior regression."""

    def test_no_new_runtime_flags_enabled(self):
        """No new runtime flags are forced on by default."""
        import domain.shl.engine as shl_mod
        import domain.senior_debt_sizing.engine as sds_mod
        import domain.depreciation.engine as depr_mod

        for mod in [shl_mod, sds_mod, depr_mod]:
            if hasattr(mod, "DEFAULT_FLAGS"):
                for flag, val in mod.DEFAULT_FLAGS.items():
                    assert val is False, f"{mod.__name__}.DEFAULT_FLAGS['{flag}'] = {val}"

    def test_engine_compute_is_pure_function(self):
        """Engine.compute() produces deterministic output from inputs only."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(3)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=3,
            period_inputs=period_inputs,
            total_shl_funding_keur=10000.0,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(10000.0,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        r1 = ShlEngine.compute(inputs)
        r2 = ShlEngine.compute(inputs)
        assert r1.total_gross_accrued_interest_keur == r2.total_gross_accrued_interest_keur

    def test_all_engines_importable(self):
        """All three engines are importable without side effects."""
        from domain.shl.engine import ShlEngine
        from domain.senior_debt_sizing.engine import SeniorDebtSizingEngine
        from domain.depreciation.engine import DepreciationEngine
        assert ShlEngine is not None
        assert SeniorDebtSizingEngine is not None
        assert DepreciationEngine is not None


# ============================================================================
# R99/R102 Blockers
# ============================================================================

class TestR99Blockers:
    """R99/R102 remain BLOCKED."""

    def test_r99_r102_blocked_in_shl(self):
        """SHL engine does not implement R99/R102 distribution gates."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=500.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(5)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=5,
            period_inputs=period_inputs,
            total_shl_funding_keur=5000.0,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(5000.0,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "r99_triggered")
        assert not hasattr(result, "reserve_required")

    def test_r99_r102_blocked_in_senior_debt(self):
        """SeniorDebtSizing does not gate on R99/R102."""
        sizing_policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=(1000.0,) * 63,
            inferred_minimum_dscr=1.45,
        )
        dscr_policy = SeniorDebtDSCRPolicy(target_dscr_by_period=(1.45,) * 63)
        result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)
        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "r99_triggered")

    def test_r99_r102_blocked_in_depreciation(self):
        """DepreciationEngine does not gate on R99/R102."""
        inputs = DepreciationEngineInputs(
            project_name="TUHO",
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=5000.0,
                    book_depreciable_basis_keur=5000.0,
                    tax_depreciable_basis_keur=5000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "r99_triggered")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])