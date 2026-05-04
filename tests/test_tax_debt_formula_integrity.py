"""Tests for core financial formula integrity — DSCR, taxable income, depreciation."""
import pytest
from dataclasses import replace

from app.project_factories import create_default_solar_project
from app.ui_runner import _run_waterfall, _build_period_engine
from domain.waterfall.tax_engine import compute_period_tax


class TestDSCRUsesCFADSNotEBITDA:
    """DSCR must be computed as CFADS / debt_service, NOT EBITDA / debt_service.

    CFADS = EBITDA - Tax
    Using EBITDA would overstate available cash and inflate DSCR.
    """

    def test_dscr_uses_cfads_not_ebitda(self):
        """DSCR denominator uses CFADS (after-tax cashflow), not raw EBITDA."""
        solar = create_default_solar_project()
        engine = _build_period_engine(solar)
        result = _run_waterfall(solar, engine)

        # Get a period where there's actual debt service
        op_periods = [p for p in result.periods if p.is_operation and p.senior_ds_keur > 0]
        assert op_periods, "Need at least one operating period with senior debt service"

        period = op_periods[0]

        # Verify DSCR is defined as CFADS / senior_ds
        # CFADS = EBITDA - Tax
        # We can't directly observe CFADS on the period object if it's not exposed,
        # but we can verify by checking that DSCR changes when tax changes
        # (EBITDA-based DSCR would NOT change when tax changes)
        from domain.waterfall.tax_engine import compute_period_tax

        # Get components
        ebitda = period.ebitda_keur
        tax = period.tax_keur
        cfads = ebitda - tax
        senior_ds = period.senior_ds_keur

        assert cfads >= 0, f"CFADS must be >= 0, got {cfads}"
        assert senior_ds > 0, f"senior_ds must be > 0, got {senior_ds}"

        # DSCR reported by the model
        model_dscr = period.dscr
        expected_dscr = cfads / senior_ds

        assert abs(model_dscr - expected_dscr) < 0.001, (
            f"DSCR should be CFADS/senior_ds = {expected_dscr:.4f}, "
            f"got {model_dscr:.4f} (model may be using EBITDA instead of CFADS)"
        )


class TestTaxableIncomeIncludesDepreciation:
    """Taxable income must deduct depreciation (not just EBITDA - interest).

    Formula: taxable_income = EBITDA - depreciation - interest + ATAD + reintegration - losses
    Higher depreciation → lower taxable income → lower tax.
    """

    def test_taxable_income_decreases_when_depreciation_increases(self):
        """Increasing depreciation must decrease taxable income."""
        # Use compute_period_tax directly with two depreciation values
        ebitda = 10_000.0
        dep_low = 2_000.0
        dep_high = 4_000.0
        interest = 1_000.0
        tax_rate = 0.10

        result_low = compute_period_tax(
            ebitda_keur=ebitda,
            depreciation_keur=dep_low,
            senior_interest_keur=interest,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=tax_rate,
            fiscal_reintegration_keur=0.0,
            atad_applies=False,
        )
        result_high = compute_period_tax(
            ebitda_keur=ebitda,
            depreciation_keur=dep_high,
            senior_interest_keur=interest,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=tax_rate,
            fiscal_reintegration_keur=0.0,
            atad_applies=False,
        )

        # Higher depreciation → lower taxable income
        assert result_high.taxable_income_keur < result_low.taxable_income_keur, (
            f"Higher depreciation should reduce taxable income: "
            f"dep={dep_high} → taxable={result_high.taxable_income_keur:.2f} vs "
            f"dep={dep_low} → taxable={result_low.taxable_income_keur:.2f}"
        )

        # Higher depreciation → lower tax
        assert result_high.tax_keur < result_low.tax_keur, (
            f"Higher depreciation should reduce tax: "
            f"dep={dep_high} → tax={result_high.tax_keur:.2f} vs "
            f"dep={dep_low} → tax={result_low.tax_keur:.2f}"
        )

    def test_depreciation_affects_tax(self):
        """Depreciation must actually reduce tax paid (not just reduce taxable income)."""
        tax_rate = 0.25
        ebitda = 50_000.0

        # Zero depreciation case
        no_dep = compute_period_tax(
            ebitda_keur=ebitda,
            depreciation_keur=0.0,
            senior_interest_keur=2_000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=tax_rate,
            fiscal_reintegration_keur=0.0,
            atad_applies=False,
        )

        # With meaningful depreciation
        with_dep = compute_period_tax(
            ebitda_keur=ebitda,
            depreciation_keur=5_000.0,
            senior_interest_keur=2_000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=tax_rate,
            fiscal_reintegration_keur=0.0,
            atad_applies=False,
        )

        # Tax with depreciation must be lower
        assert with_dep.tax_keur < no_dep.tax_keur, (
            f"Depreciation should reduce tax: with dep={with_dep.tax_keur:.2f}, "
            f"without={no_dep.tax_keur:.2f}"
        )

    def test_depreciation_non_zero_in_operating_periods(self):
        """Depreciation must be non-zero in operating periods that have a depreciation schedule.

        Most (≥80%) operating periods must have non-zero depreciation.
        The final partial period may have zero.
        """
        solar = create_default_solar_project()
        engine = _build_period_engine(solar)
        result = _run_waterfall(solar, engine)

        op_periods = [p for p in result.periods if p.is_operation]
        assert op_periods, "Need at least one operating period"

        # First operating period must have depreciation
        first = op_periods[0]
        assert hasattr(first, 'depreciation_keur')
        assert first.depreciation_keur > 0, (
            f"First operating period {first.period} must have non-zero depreciation, "
            f"got {first.depreciation_keur}"
        )

        # Most operating periods must have non-zero depreciation
        non_zero = [p for p in op_periods if p.depreciation_keur > 0]
        ratio = len(non_zero) / len(op_periods)
        assert ratio >= 0.8, (
            f"At least 80% of operating periods must have non-zero depreciation. "
            f"Got {len(non_zero)}/{len(op_periods)} ({ratio:.0%})"
        )
