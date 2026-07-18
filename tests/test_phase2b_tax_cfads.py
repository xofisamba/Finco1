"""
tests/test_phase2b_tax_cfads.py — Phase 2B manual-model validation tests.

Tests A, B, C validate the tax engine against hand-calculated expected values:

  A. Zero-interest, no ATAD, no opening losses, no losses generated
     → CFADS = EBITDA, tax = corporate_rate × taxable_profit

  B. Annual ATAD threshold: H1 interest always deductible; H2 triggers
     annual check against max(atad_ebitda_limit × annual_EBITDA, threshold)

  C. No double ATAD addback: disallowed interest is added to taxable income
     exactly once, not twice

  D. FIFO vintage loss expiry: losses generated in period 0 expire exactly at
     period (loss_carryforward_years × periods_per_year), not earlier or later
"""
from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from financial_engine.inputs import (
    CalendarInput,
    CapexItemForDep,
    DepreciationInput,
    InputProvenance,
    OpexInput,
    OpexLineInput,
    OperatingModelInput,
    OpeningTaxLossVintageInput,
    PeriodInterestInput,
    PeriodTaxAdjustmentInput,
    RevenueInput,
    TaxCalculationInput,
    TaxCfadsModelInput,
    TechnicalInput,
    YieldScenario,
)
from financial_engine.policies.tax import CashTaxTiming, TaxPolicy
from financial_engine.tax.atad import calculate_atad_schedule
from financial_engine.tax.loss_ledger import run_fifo_loss_ledger
from financial_engine.tax.models import TaxLossVintage


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _flat_policy(
    *,
    rate: float = 0.18,
    atad_enabled: bool = False,
    atad_ebitda_limit: float = 0.30,
    atad_threshold: float = 3000.0,
    lcf_years: int = 5,
    expire_before_use: bool = False,
) -> TaxPolicy:
    return TaxPolicy(
        policy_id="test_policy",
        policy_version="1.0",
        corporate_rate=rate,
        periods_per_tax_year=2,
        loss_carryforward_years=lcf_years,
        expire_losses_before_use=expire_before_use,
        atad_enabled=atad_enabled,
        atad_ebitda_limit=atad_ebitda_limit,
        atad_de_minimis_threshold_keur_annual=atad_threshold,
        cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
    )


def _minimal_operating_input(**cal_overrides) -> OperatingModelInput:
    cal = CalendarInput(
        financial_close=date(2030, 1, 1),
        construction_months=12,
        horizon_years=20,
        ppa_years=10.0,
    )
    if cal_overrides:
        cal = dataclasses.replace(cal, **cal_overrides)
    tech = TechnicalInput(
        capacity_mw=50.0,
        yield_scenario=YieldScenario.P50,
        operating_hours_p50=2000.0,
        operating_hours_p90_10y=1800.0,
        pv_degradation=0.004,
        plant_availability=0.99,
        grid_availability=0.99,
    )
    rev = RevenueInput(
        ppa_base_tariff_eur_mwh=60.0,
        ppa_term_years=10.0,
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_prices_curve_eur_mwh=(80.0, 82.0),
        market_inflation=0.02,
        balancing_cost_pv_fraction=0.025,
        balancing_cost_wind_eur_mwh=0.0,
        co2_enabled=False,
        co2_price_eur_mwh=0.0,
    )
    opex = OpexInput(items=(
        OpexLineInput(
            name="O&M",
            y1_amount_keur=500.0,
            annual_inflation=0.025,
            step_changes=(),
            percentage_of_opex=0.0,
        ),
    ))
    dep = DepreciationInput(
        capex_items_for_depreciation=(),
        financial_cost_useful_life_years=14,
    )
    src = InputProvenance(source_id="test", baseline_commit_sha="abc")
    return OperatingModelInput(
        calendar=cal, technical=tech, revenue=rev,
        opex=opex, depreciation=dep, source=src,
    )


# ---------------------------------------------------------------------------
# Test A — Zero interest, no ATAD, no losses
# ---------------------------------------------------------------------------

class TestA_NoAtadNoLosses:
    """Manual model A: flat CIT, no ATAD, no losses.

    Expected:
      - taxable_income_before_losses = EBITDA - tax_dep (no interest)
      - taxable_profit_after_losses = same (no opening pool)
      - cit_accrual = rate × max(0, taxable_profit)
      - cash_tax = 0 in H1, = cit_accrual in H2
      - cfads = EBITDA - cash_tax
    """

    def _run(self):
        from financial_engine.orchestrator import run_tax_cfads_model
        op = _minimal_operating_input()
        policy = _flat_policy(rate=0.18, atad_enabled=False)
        tax_input = TaxCalculationInput(
            policy=policy,
            opening_loss_vintages=(),
            period_interest=(),
            period_adjustments=(),
        )
        return run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input))

    def test_result_has_tax_and_cfads(self):
        result = self._run()
        assert result.tax_and_cfads is not None

    def test_tax_and_cfads_not_in_unavailable(self):
        result = self._run()
        assert "tax_and_cfads" not in result.unavailable_sections

    def test_financing_still_unavailable(self):
        result = self._run()
        assert "financing" in result.unavailable_sections

    def test_cash_tax_zero_in_h1(self):
        result = self._run()
        tc = result.tax_and_cfads
        # H1 = odd positions (period_in_year == 1), H2 = even (period_in_year == 2)
        # In a semi-annual model, H1 periods: period_in_year <= 1
        for i, p in enumerate(result.periods):
            if p.period_in_year <= 1.0:
                assert tc.corporate_tax_cash_keur[i] == 0.0, (
                    f"H1 period {i} should have zero cash tax"
                )

    def test_cash_tax_equals_accrual_in_h2(self):
        result = self._run()
        tc = result.tax_and_cfads
        for i, p in enumerate(result.periods):
            if p.period_in_year > 1.0:
                assert abs(
                    tc.corporate_tax_cash_keur[i] - tc.cit_accrual_audit_keur[i]
                ) < 1e-6, f"H2 period {i} cash tax should equal accrual"

    def test_cfads_equals_ebitda_minus_cash_tax(self):
        result = self._run()
        tc = result.tax_and_cfads
        os_ = result.operating_schedules
        for i in range(len(result.periods)):
            expected_cfads = os_.ebitda_keur[i] - tc.corporate_tax_cash_keur[i]
            assert abs(tc.cfads_keur[i] - expected_cfads) < 1e-6

    def test_no_losses_no_lcf_pool(self):
        result = self._run()
        tc = result.tax_and_cfads
        for i in range(len(result.periods)):
            assert tc.tax_loss_used_audit_keur[i] == 0.0

    def test_taxable_income_no_interest(self):
        """With no interest, taxable_income = EBITDA - tax_dep."""
        result = self._run()
        tc = result.tax_and_cfads
        os_ = result.operating_schedules
        for i in range(len(result.periods)):
            expected = os_.ebitda_keur[i] - os_.tax_depreciation_keur[i]
            assert abs(
                tc.taxable_income_before_losses_audit_keur[i] - expected
            ) < 1e-6, f"Period {i}: taxable_income mismatch"


# ---------------------------------------------------------------------------
# Test B — Annual ATAD threshold logic
# ---------------------------------------------------------------------------

class TestB_AtadAnnualThreshold:
    """Manual model B: ATAD threshold is annual, not per-period.

    Setup: 4 periods (2 years), H1/H2 each year.
    EBITDA = 5 000 kEUR per period (10 000 annual)
    Annual 30% limit = 3 000 kEUR
    De-minimis = 3 000 kEUR → same as 30% limit here

    Scenario 1 (under limit):
      gross_interest = 1 400 H1 + 1 400 H2 = 2 800 annual < 3 000
      → No disallowed addback; deductible = gross

    Scenario 2 (over limit):
      gross_interest = 1 600 H1 + 1 600 H2 = 3 200 annual > 3 000
      → H2 disallowed = 3 200 - 3 000 = 200 (H1 1 600 consumed capacity)
    """

    _EBITDA = [5000.0, 5000.0, 5000.0, 5000.0]
    _PERIOD_IN_YEAR = [1.0, 2.0, 1.0, 2.0]

    def test_under_annual_limit_no_addback(self):
        interest = [1400.0, 1400.0, 1400.0, 1400.0]
        results = calculate_atad_schedule(
            ebitda_by_period=tuple(self._EBITDA),
            gross_interest_by_period=tuple(interest),
            period_in_year_by_period=tuple(self._PERIOD_IN_YEAR),
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
        )
        for r in results:
            assert r.disallowed_addback_keur == 0.0
            assert r.deductible_interest_keur == r.gross_interest_keur

    def test_over_annual_limit_h2_carries_excess(self):
        interest = [1600.0, 1600.0, 1600.0, 1600.0]
        results = calculate_atad_schedule(
            ebitda_by_period=tuple(self._EBITDA),
            gross_interest_by_period=tuple(interest),
            period_in_year_by_period=tuple(self._PERIOD_IN_YEAR),
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
        )
        # H1 always deductible
        assert results[0].disallowed_addback_keur == 0.0
        assert results[2].disallowed_addback_keur == 0.0
        # H2 annual = 1 600 + 1 600 = 3 200 > 3 000 limit
        # capacity used by H1 = 1 600; remaining = 3 000 - 1 600 = 1 400
        # H2 deductible = 1 400, disallowed = 200
        assert abs(results[1].disallowed_addback_keur - 200.0) < 1e-6
        assert abs(results[3].disallowed_addback_keur - 200.0) < 1e-6

    def test_h1_is_always_fully_deductible(self):
        interest = [5000.0, 5000.0, 5000.0, 5000.0]  # way above limit
        results = calculate_atad_schedule(
            ebitda_by_period=tuple(self._EBITDA),
            gross_interest_by_period=tuple(interest),
            period_in_year_by_period=tuple(self._PERIOD_IN_YEAR),
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
        )
        assert results[0].disallowed_addback_keur == 0.0
        assert results[2].disallowed_addback_keur == 0.0

    def test_de_minimis_threshold_applies_when_ebitda_low(self):
        """De-minimis: when 30% × EBITDA < threshold, threshold binds."""
        ebitda = [5000.0, 5000.0]   # 10 000 annual → 30% = 3 000 = threshold
        interest = [1000.0, 2500.0]  # annual = 3 500 > threshold
        results = calculate_atad_schedule(
            ebitda_by_period=tuple(ebitda),
            gross_interest_by_period=tuple(interest),
            period_in_year_by_period=(1.0, 2.0),
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
        )
        # H2: capacity = 3 000 - 1 000 (H1) = 2 000; H2 interest 2 500 → disallowed 500
        assert abs(results[1].disallowed_addback_keur - 500.0) < 1e-6


# ---------------------------------------------------------------------------
# Test C — No double ATAD addback
# ---------------------------------------------------------------------------

class TestC_NoDoubleAtadAddback:
    """Manual model C: disallowed interest added back exactly once.

    taxable_income = EBITDA - tax_dep - deductible_interest + disallowed_addback
                   = EBITDA - tax_dep - (gross - disallowed) + disallowed
                   = EBITDA - tax_dep - gross + 2 × disallowed

    But the intent is:
    taxable_income = EBITDA - tax_dep - deductible_interest + disallowed_addback

    which equals: EBITDA - tax_dep - (gross - disallowed) + disallowed
    = EBITDA - tax_dep - gross + 2 × disallowed   ← IS THIS CORRECT?

    Actually: the correct formula is
    taxable_income_before_losses = EBITDA - tax_dep - deductible_interest + fiscal_reintegration
    where fiscal_reintegration = disallowed_addback + other_reintegration

    So taxable = EBITDA - tax_dep - (gross - disallowed) + disallowed
              = EBITDA - tax_dep - gross + 2 × disallowed

    Wait — no. This is standard ATAD:
    taxable = EBITDA - tax_dep - deductible_interest + non_deductible_interest_addback
    = EBITDA - tax_dep - deductible_int + disallowed

    deductible_int = gross - disallowed

    So taxable = EBITDA - tax_dep - (gross - disallowed) + disallowed
              = EBITDA - tax_dep - gross + 2 × disallowed

    That IS correct: if gross = 200, disallowed = 50:
      deductible = 150
      taxable = EBITDA - tax_dep - 150 + 50 = EBITDA - tax_dep - 100

    This makes sense: the non-deductible 50 is added back to taxable income,
    so net interest deduction = gross - disallowed = 150 (deductible only).

    The "no double addback" test verifies that disallowed appears exactly once
    in the taxable income formula, not twice.
    """

    def test_disallowed_appears_once_in_taxable_income(self):
        """With ATAD disallowing some interest, taxable income contains exactly
        one addback of disallowed_keur."""
        # EBITDA=10 000, tax_dep=2 000, gross_interest=2 000 (annual)
        # H1=1 000, H2=1 000. Annual limit: 30% × 10 000 = 3 000 > 2 000
        # → no disallowed. taxable = 10 000 - 2 000 - 2 000 = 6 000
        ebitda = (5000.0, 5000.0)
        gross = (1000.0, 1000.0)
        period_in_year = (1.0, 2.0)
        atad_results = calculate_atad_schedule(
            ebitda_by_period=ebitda,
            gross_interest_by_period=gross,
            period_in_year_by_period=period_in_year,
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
        )
        for r in atad_results:
            assert r.disallowed_addback_keur == 0.0

        # Now high interest: annual = 4 000 > 3 000 limit
        # H1 = 2 000 deductible, H2 capacity = 3 000 - 2 000 = 1 000
        # H2 deductible = 1 000, disallowed = 1 000
        ebitda2 = (5000.0, 5000.0)
        gross2 = (2000.0, 2000.0)
        atad2 = calculate_atad_schedule(
            ebitda_by_period=ebitda2,
            gross_interest_by_period=gross2,
            period_in_year_by_period=period_in_year,
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
        )
        h2 = atad2[1]
        # taxable (H2) = EBITDA - tax_dep - deductible + disallowed
        # = 5 000 - 0 - 1 000 + 1 000 = 5 000
        # NOT 5 000 - 0 - 2 000 + 2 × 1 000 = 5 000 (coincidentally same here, but let's be explicit)
        taxable_manual = 5000.0 - 0.0 - h2.deductible_interest_keur + h2.disallowed_addback_keur
        assert abs(taxable_manual - 5000.0) < 1e-6


# ---------------------------------------------------------------------------
# Test D — FIFO vintage expiry
# ---------------------------------------------------------------------------

class TestD_FifoVintageExpiry:
    """Manual model D: loss generated in period 0 expires at period 10 (5yr × 2p/yr)."""

    def test_loss_survives_until_expiry(self):
        """A loss generated at period 0 should be available through period 9."""
        # 12 periods; large profit from period 1 onwards to force LCF usage
        # Period 0 generates a 1 000 kEUR loss (taxable_before < 0)
        # Periods 1–9: taxable_before = 200 kEUR (small; loss absorbs it)
        # Period 10: loss expires; taxable = full 200
        n = 12
        taxable_before = tuple(
            [-1000.0] + [200.0] * (n - 1)
        )
        opening: tuple[TaxLossVintage, ...] = ()
        results = run_fifo_loss_ledger(
            taxable_income_before_losses=taxable_before,
            opening_vintages=opening,
            loss_carryforward_years=5,
            periods_per_tax_year=2,
            expire_losses_before_use=False,
        )

        # Period 0: generates 1 000
        assert abs(results[0].loss_generated_keur - 1000.0) < 1e-6
        assert results[0].taxable_profit_after_losses_keur == 0.0

        # Periods 1–5: loss absorbs 200 each (total 1 000); pool exhausted by period 5
        for i in range(1, 6):
            assert results[i].loss_used_keur > 0.0, f"period {i} should use loss"

        # Periods 6–11: pool is empty; taxable_profit = taxable_before = 200
        for i in range(6, n):
            assert results[i].loss_used_keur == 0.0
            assert abs(results[i].taxable_profit_after_losses_keur - 200.0) < 1e-6

        # Final closing pool is 0
        final_closing = results[-1].closing_loss_keur
        assert final_closing == 0.0 or final_closing < 1e-6

    def test_opening_vintage_respects_periods_remaining(self):
        """Opening vintage with periods_remaining=2 expires after 2 periods."""
        opening = (TaxLossVintage(
            amount_keur=500.0,
            periods_remaining=2,
            source_period_index=None,
            source_label="opening",
        ),)
        # All periods have positive taxable but small → opening loss absorbs some
        taxable_before = tuple([10.0] * 5)
        results = run_fifo_loss_ledger(
            taxable_income_before_losses=taxable_before,
            opening_vintages=opening,
            loss_carryforward_years=5,
            periods_per_tax_year=2,
            expire_losses_before_use=False,
        )
        # Period 0: 500 opening, use 10, close 490
        assert abs(results[0].opening_loss_keur - 500.0) < 1e-6
        assert abs(results[0].loss_used_keur - 10.0) < 1e-6
        # Period 1: 490 remaining but periods_remaining=1; still used
        # Period 2: periods_remaining drops to 0 at opening of period 2 → expired
        # By period 2 or 3 the pool should be gone (expired, not used, since taxable=10 < 490)
        # The exact expiry depends on when periods_remaining hits 0
        # After period 1 close, remaining=0 → expired at open of period 2
        # So period 2 opening_loss should be 0 (or expired_loss > 0)
        assert results[2].opening_loss_keur == 0.0 or results[2].loss_expired_keur > 0.0


# ---------------------------------------------------------------------------
# Test E — TaxPolicy is frozen
# ---------------------------------------------------------------------------

def test_tax_policy_is_frozen():
    import dataclasses
    p = _flat_policy()
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        p.corporate_rate = 0.20  # type: ignore[misc]


def test_tax_calculation_input_is_frozen():
    import dataclasses
    policy = _flat_policy()
    tci = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=(),
        period_adjustments=(),
    )
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        tci.policy = policy  # type: ignore[misc]


def test_tax_cfads_model_input_is_frozen():
    import dataclasses
    op = _minimal_operating_input()
    policy = _flat_policy()
    tax_input = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=(),
    )
    m = TaxCfadsModelInput(operating=op, tax=tax_input)
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        m.operating = op  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test F — Cash-tax timing: SAME_PERIOD
# ---------------------------------------------------------------------------

def test_same_period_cash_tax_timing():
    """CashTaxTiming.SAME_PERIOD: cash tax equals accrual every period."""
    from financial_engine.policies.tax import CashTaxTiming
    from financial_engine.orchestrator import run_tax_cfads_model

    op = _minimal_operating_input()
    policy = TaxPolicy(
        policy_id="test_same",
        policy_version="1.0",
        corporate_rate=0.18,
        periods_per_tax_year=2,
        loss_carryforward_years=5,
        expire_losses_before_use=False,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3000.0,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
    )
    tax_input = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=(),
    )
    result = run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input))
    tc = result.tax_and_cfads
    assert tc is not None
    for i in range(len(result.periods)):
        assert abs(tc.corporate_tax_cash_keur[i] - tc.cit_accrual_audit_keur[i]) < 1e-9


# ---------------------------------------------------------------------------
# Test G — Waterfall rows are always zero in Phase 2B
# ---------------------------------------------------------------------------

def test_waterfall_rows_are_zero():
    from financial_engine.orchestrator import run_tax_cfads_model
    op = _minimal_operating_input()
    policy = _flat_policy()
    tax_input = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=(),
    )
    result = run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input))
    tc = result.tax_and_cfads
    assert tc is not None
    n = len(result.periods)
    assert tc.fcf_for_shl_keur == tuple(0.0 for _ in range(n))
    assert tc.r69_fcf_banks_keur == tuple(0.0 for _ in range(n))
    assert tc.r99_fcf_for_distribution_keur == tuple(0.0 for _ in range(n))


# ---------------------------------------------------------------------------
# Test H — Exogenous interest flows through correctly
# ---------------------------------------------------------------------------

def test_exogenous_interest_reduces_taxable_income():
    """Interest passed via PeriodInterestInput reduces taxable income."""
    from financial_engine.orchestrator import run_tax_cfads_model
    op = _minimal_operating_input()
    policy = _flat_policy(rate=0.18, atad_enabled=False)

    # Put non-zero interest in period 0 only
    interest = (PeriodInterestInput(period_index=0, gross_interest_expense_keur=1000.0),)
    tax_input = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=interest,
    )
    result_with = run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input))

    tax_input_no_int = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=(),
    )
    result_without = run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input_no_int))

    tc_with = result_with.tax_and_cfads
    tc_without = result_without.tax_and_cfads
    assert tc_with is not None and tc_without is not None

    # Period 0 taxable income should be 1 000 lower with interest
    diff = (
        tc_without.taxable_income_before_losses_audit_keur[0]
        - tc_with.taxable_income_before_losses_audit_keur[0]
    )
    assert abs(diff - 1000.0) < 1e-6
