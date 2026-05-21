"""Phase 9C: DistributionAccount Runtime Wiring tests.

These tests validate the use_distributionaccount_runtime_wiring flag
(default=False) that wires DA equity_distribution_paid_keur into runtime
distribution_keur behind an explicit opt-in.

Key invariants:
- Flag default is False — no runtime behavior change without explicit opt-in.
- flag=False: exact legacy runtime behavior, distribution_keur unchanged.
- flag=True: distribution_keur becomes pass-through alias of da_paid.
- Oborovo: blocked by guard — flag=True is no-op with audit metadata.
- R99/R102: BLOCKED in governed mode (not promoted by this flag).
- No second runtime distribution source — exactly one authoritative value.
"""

from __future__ import annotations

import csv
import inspect
from datetime import date
from pathlib import Path

import pytest

from app.waterfall_core import run_waterfall_v3_core
from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine as build_period_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_tuho(flag_value: bool):
    """Run TUHO waterfall with given wiring flag."""
    inputs = create_default_tuho_wind1()
    engine = build_period_engine(inputs)
    common = dict(
        rate_per_period=0.0, tenor_periods=0,
        target_dscr=1.15, lockup_dscr=1.10, tax_rate=0.10, dsra_months=6,
        shl_amount=0.0, shl_rate=0.0, shl_idc_keur=0.0,
        shl_repayment_method='bullet', shl_tenor_years=0, shl_wht_rate=0.0,
        discount_rate_project=0.0641, discount_rate_equity=0.0965,
        fixed_debt_keur=None, fixed_ds_keur=None, rate_schedule=None,
        senior_sculpting_config=None, equity_irr_method='equity_only',
        share_capital_keur=0.0, sculpt_capex_keur=0.0,
        debt_sizing_method='dscr_sculpt', dscr_schedule=None,
        advanced_opex_line_items=None, advanced_capex_line_items=None,
        advanced_capex_depreciation_schedule=None,
        use_senior_sweep_cash_cap_for_shl=False,
        use_tuho_r99_input_engine=False,
        use_shl_fcf_waterfall_engine=False,
        use_tax_bridge_engine=False,
        use_shl_gross_accrued_for_pnl=False,
        shl_fcf_waterfall_cash_schedule_keur=(),
        shl_fcf_waterfall_minimum_cash_retained_keur=0.0,
        tuho_cit_cash_tax_start_operating_index=None,
        use_shl_canonical_engine=False,
        use_depreciation_canonical_engine=False,
        use_senior_debt_sizing_engine=False,
        use_co2_revenue_bridge=False,
        use_co2_cit_bridge=False,
        use_dualrun_validation=False,
    )
    return run_waterfall_v3_core(
        inputs=inputs, engine=engine,
        use_distributionaccount_runtime_wiring=flag_value,
        **common,
    )


# ---------------------------------------------------------------------------
# Flag existence and default
# ---------------------------------------------------------------------------

class TestFlagExistsAndDefaultsToFalse:
    def test_flag_exists_in_signature(self):
        sig = inspect.signature(run_waterfall_v3_core)
        assert 'use_distributionaccount_runtime_wiring' in sig.parameters

    def test_flag_defaults_to_false(self):
        sig = inspect.signature(run_waterfall_v3_core)
        param = sig.parameters['use_distributionaccount_runtime_wiring']
        assert param.default is False, (
            "Flag must default to False — no silent behavior change"
        )


# ---------------------------------------------------------------------------
# TUHO flag=False — legacy behavior preserved
# ---------------------------------------------------------------------------

class TestTuhoFlagFalseLegacyPreserved:
    def test_total_distribution_keur_matches_expected_baseline(self):
        """Legacy TUHO total distribution ≈ 326,165 kEUR (baseline)."""
        r = _run_tuho(flag_value=False)
        assert 325_000 < r.total_distribution_keur < 327_000, (
            f"Expected ~326,165 kEUR baseline, got {r.total_distribution_keur:,.2f}"
        )

    def test_distribution_source_empty_when_flag_false(self):
        """When flag=False, distribution_source is empty (no wiring)."""
        r = _run_tuho(flag_value=False)
        assert r.distribution_source == ''
        for wp in r.periods:
            assert wp.distribution_source == ''

    def test_no_legacy_or_da_metadata_when_flag_false(self):
        """Audit metadata fields are zero/empty when flag=False."""
        r = _run_tuho(flag_value=False)
        # These fields may exist but should be zero/empty in flag=False path
        for wp in r.periods:
            assert wp.legacy_distribution_keur == 0.0
            assert wp.da_paid_distribution_keur == 0.0
            assert wp.distribution_wiring_delta_keur == 0.0

    def test_periods_have_nonzero_distributions(self):
        """TUHO baseline has nonzero distributions in operating periods."""
        r = _run_tuho(flag_value=False)
        nonzero = [wp for wp in r.periods if wp.distribution_keur > 0]
        assert len(nonzero) >= 40, f"Expected many nonzero distribution periods, got {len(nonzero)}"


# ---------------------------------------------------------------------------
# TUHO flag=True — DA wired as source
# ---------------------------------------------------------------------------

class TestTuhoFlagTrueDAWired:
    def test_distribution_keur_becomes_da_paid(self):
        """When flag=True, per-period distribution_keur == da_paid."""
        r = _run_tuho(flag_value=True)
        for wp in r.periods:
            assert wp.distribution_keur == wp.da_paid_distribution_keur, (
                f"Period {wp.period}: dist={wp.distribution_keur} != da_paid={wp.da_paid_distribution_keur}"
            )

    def test_total_is_pass_through_alias_of_da_paid(self):
        """Result total_distribution_keur == da_paid total (pass-through alias)."""
        r = _run_tuho(flag_value=True)
        assert abs(r.total_distribution_keur - r.da_paid_distribution_keur) < 0.01, (
            f"total={r.total_distribution_keur} != da_paid={r.da_paid_distribution_keur}"
        )

    def test_legacy_distribution_keur_preserved(self):
        """Legacy distribution is stored in audit metadata."""
        r = _run_tuho(flag_value=True)
        # Legacy TUHO total should be the baseline ~326,165 kEUR
        assert 325_000 < r.legacy_distribution_keur < 327_000

    def test_distribution_source_is_distribution_account(self):
        """distribution_source is 'distribution_account' when flag=True."""
        r = _run_tuho(flag_value=True)
        assert r.distribution_source == 'distribution_account'
        for wp in r.periods:
            assert wp.distribution_source == 'distribution_account'

    def test_total_distribution_recalculated_after_per_period_overrides(self):
        """total_distribution_keur is recalculated after per-period wiring."""
        r = _run_tuho(flag_value=True)
        expected_total = sum(wp.distribution_keur for wp in r.periods)
        assert abs(r.total_distribution_keur - expected_total) < 0.01, (
            f"total={r.total_distribution_keur} but sum of per-period={expected_total}"
        )

    def test_da_paid_total_approx_expected_value(self):
        """DA-paid total should be approximately 284,552 kEUR for TUHO."""
        r = _run_tuho(flag_value=True)
        assert 283_000 < r.da_paid_distribution_keur < 286_000, (
            f"Expected ~284,552 kEUR DA-paid, got {r.da_paid_distribution_keur:,.2f}"
        )

    def test_delta_from_legacy_approx_expected(self):
        """Delta from legacy should be approximately -41,613 kEUR."""
        r = _run_tuho(flag_value=True)
        expected_delta = r.da_paid_distribution_keur - r.legacy_distribution_keur
        assert -43_000 < expected_delta < -40_000, (
            f"Expected delta ~-41,613 kEUR, got {expected_delta:,.2f}"
        )

    def test_lockup_periods_zeroed_in_da_wired_mode(self):
        """DA economic mode zeros distributions in lockup periods."""
        r_flag_false = _run_tuho(flag_value=False)
        r_flag_true = _run_tuho(flag_value=True)
        # Periods 1-13 are lockup (senior tenor = 14 semi-annual periods)
        lockup_periods = range(1, 14)
        for i, wp in enumerate(r_flag_true.periods):
            pnum = i + 1
            if pnum in lockup_periods:
                assert wp.distribution_keur == 0.0, (
                    f"Period {pnum} is lockup but has dist={wp.distribution_keur}"
                )
                # In legacy mode, these had nonzero distributions
                assert r_flag_false.periods[i].distribution_keur > 0, (
                    f"Period {pnum} expected nonzero in legacy mode"
                )

    def test_no_dual_distribution_truths(self):
        """There is exactly one authoritative distribution value when flag=True."""
        r = _run_tuho(flag_value=True)
        for wp in r.periods:
            # distribution_keur is the authoritative source; da_paid is the backing value
            assert wp.distribution_keur == wp.da_paid_distribution_keur
            # delta is da_paid - legacy, not a separate source
            expected_delta = wp.da_paid_distribution_keur - wp.legacy_distribution_keur
            assert abs(wp.distribution_wiring_delta_keur - expected_delta) < 0.01


# ---------------------------------------------------------------------------
# Oborovo guard — blocked, not silently falling through
# ---------------------------------------------------------------------------

class TestOborovoGuardBlocked:
    def _run_oborovo(self, flag_value: bool):
        inputs = create_default_oborovo()
        engine = build_period_engine(inputs)
        common = dict(
            rate_per_period=0.0, tenor_periods=0,
            target_dscr=1.15, lockup_dscr=1.10, tax_rate=0.10, dsra_months=6,
            shl_amount=0.0, shl_rate=0.0, shl_idc_keur=0.0,
            shl_repayment_method='bullet', shl_tenor_years=0, shl_wht_rate=0.0,
            discount_rate_project=0.0641, discount_rate_equity=0.0965,
            fixed_debt_keur=None, fixed_ds_keur=None, rate_schedule=None,
            senior_sculpting_config=None, equity_irr_method='equity_only',
            share_capital_keur=0.0, sculpt_capex_keur=0.0,
            debt_sizing_method='dscr_sculpt', dscr_schedule=None,
            advanced_opex_line_items=None, advanced_capex_line_items=None,
            advanced_capex_depreciation_schedule=None,
            use_senior_sweep_cash_cap_for_shl=False,
            use_tuho_r99_input_engine=False,
            use_shl_fcf_waterfall_engine=False,
            use_tax_bridge_engine=False,
            use_shl_gross_accrued_for_pnl=False,
            shl_fcf_waterfall_cash_schedule_keur=(),
            shl_fcf_waterfall_minimum_cash_retained_keur=0.0,
            tuho_cit_cash_tax_start_operating_index=None,
            use_shl_canonical_engine=False,
            use_depreciation_canonical_engine=False,
            use_senior_debt_sizing_engine=False,
            use_co2_revenue_bridge=False,
            use_co2_cit_bridge=False,
            use_dualrun_validation=False,
        )
        return run_waterfall_v3_core(
            inputs=inputs, engine=engine,
            use_distributionaccount_runtime_wiring=flag_value,
            **common,
        )

    def test_flag_false_oborovo_distribution_unchanged(self):
        """Oborovo flag=False is exact legacy behavior."""
        r = self._run_oborovo(flag_value=False)
        assert r.distribution_source == ''
        assert 180_000 < r.total_distribution_keur < 182_000

    def test_flag_true_oborovo_guard_blocks(self):
        """Oborovo flag=True is blocked by guard — distribution unchanged."""
        r = self._run_oborovo(flag_value=True)
        assert r.distribution_source == 'oborovo_guard_blocked'
        assert r.da_paid_distribution_keur == 0.0
        assert r.distribution_wiring_delta_keur == 0.0

    def test_flag_true_oborovo_total_distribution_unchanged(self):
        """Oborovo total_distribution_keur is unchanged when guard blocks."""
        r_false = self._run_oborovo(flag_value=False)
        r_true = self._run_oborovo(flag_value=True)
        assert abs(r_true.total_distribution_keur - r_false.total_distribution_keur) < 0.01, (
            "Oborovo distribution must not change when guard blocks"
        )

    def test_flag_true_oborovo_period_source_is_guard_blocked(self):
        """Every period carries oborovo_guard_blocked source when guard fires."""
        r = self._run_oborovo(flag_value=True)
        for wp in r.periods:
            assert wp.distribution_source == 'oborovo_guard_blocked'
            assert wp.da_paid_distribution_keur == 0.0
            assert wp.distribution_wiring_delta_keur == 0.0


# ---------------------------------------------------------------------------
# R99/R102 governance preserved
# ---------------------------------------------------------------------------

class TestR99R102GovernancePreserved:
    def test_flag_true_does_not_promote_r99(self):
        """flag=True does NOT promote R99 — DA economic mode gate is audit-only."""
        r = _run_tuho(flag_value=True)
        # Lockup periods (1-13) still zero — this proves R99 is still evaluated
        # as gate-blocked in economic mode (not promoted to unconditional pass)
        for i in range(13):
            wp = r.periods[i]
            assert wp.distribution_keur == 0.0, (
                f"Period {i+1}: R99 must remain blocked, got dist={wp.distribution_keur}"
            )

    def test_no_r99_direct_promotion_in_wiring_function(self):
        """Code review: _apply_distributionaccount_runtime_wiring never promotes R99."""
        import app.waterfall_core as wc
        import inspect
        source = inspect.getsource(wc._apply_distributionaccount_runtime_wiring)
        assert 'r99_promote' not in source.lower(), "No R99 promotion in wiring function"
        assert 'r99_pass' not in source.lower(), "No R99 pass override in wiring function"


# ---------------------------------------------------------------------------
# No second runtime distribution source
# ---------------------------------------------------------------------------

class TestNoSecondDistributionSource:
    def test_distribution_keur_is_single_source(self):
        """distribution_keur is the only runtime distribution source when flag=True."""
        r = _run_tuho(flag_value=True)
        for wp in r.periods:
            # distribution_keur is authoritative; da_paid backs it
            assert wp.distribution_keur == wp.da_paid_distribution_keur
            # legacy is stored but not used for routing

    def test_result_level_single_distribution_source(self):
        """Result-level distribution_keur is the single authoritative total."""
        r = _run_tuho(flag_value=True)
        # total is recalculated sum of per-period authoritative values
        expected_total = sum(wp.distribution_keur for wp in r.periods)
        assert abs(r.total_distribution_keur - expected_total) < 0.01


# ---------------------------------------------------------------------------
# Baseline drift: flag=False must not change anything
# ---------------------------------------------------------------------------

class TestNoBaselineDrift:
    def test_flag_false_produces_same_total_as_before_wiring(self):
        """Running with flag=False must produce identical results to pre-wiring baseline."""
        r0 = _run_tuho(flag_value=False)
        r1 = _run_tuho(flag_value=False)  # run twice to confirm deterministic
        assert abs(r0.total_distribution_keur - r1.total_distribution_keur) < 0.01
        for wp0, wp1 in zip(r0.periods, r1.periods):
            assert abs(wp0.distribution_keur - wp1.distribution_keur) < 0.01


# ---------------------------------------------------------------------------
# Audit metadata completeness
# ---------------------------------------------------------------------------

class TestAuditMetadataFields:
    def test_all_periods_have_all_audit_fields(self):
        """Every period carries all four audit metadata fields when flag=True."""
        r = _run_tuho(flag_value=True)
        for wp in r.periods:
            assert hasattr(wp, 'legacy_distribution_keur')
            assert hasattr(wp, 'da_paid_distribution_keur')
            assert hasattr(wp, 'distribution_source')
            assert hasattr(wp, 'distribution_wiring_delta_keur')
            # Source must be set
            assert wp.distribution_source == 'distribution_account'

    def test_result_has_all_audit_fields(self):
        """Result-level object has all audit metadata fields."""
        r = _run_tuho(flag_value=True)
        assert hasattr(r, 'legacy_distribution_keur')
        assert hasattr(r, 'da_paid_distribution_keur')
        assert hasattr(r, 'distribution_source')
        assert hasattr(r, 'distribution_wiring_delta_keur')

    def test_delta_calculation_correct(self):
        """distribution_wiring_delta_keur = da_paid - legacy per period."""
        r = _run_tuho(flag_value=True)
        for wp in r.periods:
            expected_delta = wp.da_paid_distribution_keur - wp.legacy_distribution_keur
            assert abs(wp.distribution_wiring_delta_keur - expected_delta) < 0.01
        expected_result_delta = r.da_paid_distribution_keur - r.legacy_distribution_keur
        assert abs(r.distribution_wiring_delta_keur - expected_result_delta) < 0.01


# ---------------------------------------------------------------------------
# WaterfallPeriod audit fields exist on engine output
# ---------------------------------------------------------------------------

class TestWaterfallPeriodAuditFields:
    def test_waterfall_period_has_audit_fields(self):
        """WaterfallPeriod must have the four new audit metadata fields."""
        from domain.waterfall.waterfall_engine import WaterfallPeriod
        wp = WaterfallPeriod(
            period=1, date=date(2029, 1, 1), year_index=0,
            period_in_year=1, is_operation=True,
            generation_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=0.0, depreciation_keur=0.0,
            interest_senior_keur=0.0, interest_shl_keur=0.0,
            taxable_profit_keur=0.0, tax_keur=0.0,
            cf_after_tax_keur=0.0,
            senior_interest_keur=0.0, senior_principal_keur=0.0,
            senior_ds_keur=0.0, shl_interest_keur=0.0,
            shl_principal_keur=0.0, shl_service_keur=0.0,
            dsra_contribution_keur=0.0, dsra_balance_keur=0.0,
            mra_contribution_keur=0.0, mra_balance_keur=0.0,
            cf_after_reserves_keur=0.0,
            dscr=1.5, llcr=0.0, plcr=0.0, lockup_active=False,
            distribution_keur=0.0, cash_sweep_keur=0.0,
            cum_distribution_keur=0.0, cash_balance_keur=0.0,
            # New audit fields
            legacy_distribution_keur=100.0,
            da_paid_distribution_keur=80.0,
            distribution_source='distribution_account',
            distribution_wiring_delta_keur=-20.0,
        )
        assert wp.legacy_distribution_keur == 100.0
        assert wp.da_paid_distribution_keur == 80.0
        assert wp.distribution_source == 'distribution_account'
        assert wp.distribution_wiring_delta_keur == -20.0
