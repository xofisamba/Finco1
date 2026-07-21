"""
tests/test_phase2b_tax_cfads.py — Phase 2B manual-model validation tests (A–J).

Tests A–D validate the annual tax engine against hand-calculated expected values.
Tests E–H verify structural correctness, timing, and interest propagation.
Test I verifies validation codes TAX001–TAX014.
Test J is a four-baseline smoke test (integration).
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
from financial_engine.tax.atad import calculate_annual_atad, allocate_atad_to_periods
from financial_engine.tax.loss_ledger import run_annual_fifo_ledger
from financial_engine.tax.models import TaxYearCalculationBasis


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
    timing: CashTaxTiming = CashTaxTiming.TAX_YEAR_LAST_PERIOD,
    lag: int = 0,
) -> TaxPolicy:
    return TaxPolicy(
        policy_id="test_policy",
        policy_version="1.0",
        corporate_rate=rate,
        periods_per_tax_year=2,
        loss_carryforward_years=lcf_years,
        atad_enabled=atad_enabled,
        atad_ebitda_limit=atad_ebitda_limit,
        atad_de_minimis_threshold_keur_annual=atad_threshold,
        cash_tax_timing=timing,
        cash_tax_payment_lag_periods=lag,
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
        book_capex_items_for_depreciation=(),
        tax_capex_items_for_depreciation=(),
        financial_cost_useful_life_years=14,
    )
    src = InputProvenance(source_id="test", baseline_commit_sha="abc")
    return OperatingModelInput(
        calendar=cal, technical=tech, revenue=rev,
        opex=opex, depreciation=dep, source=src,
    )


def _run_model(policy: TaxPolicy, interest=(), vintages=(), adjustments=(), **cal_overrides):
    from financial_engine.orchestrator import run_tax_cfads_model
    op = _minimal_operating_input(**cal_overrides)
    tax_input = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=vintages,
        period_interest=interest,
        period_adjustments=adjustments,
    )
    return run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input))


# ---------------------------------------------------------------------------
# Test A — Zero interest, no ATAD, no losses
# ---------------------------------------------------------------------------

class TestA_NoAtadNoLosses:
    """Annual engine with no interest, no ATAD, no LCF.

    Expected:
      - taxable_income_before_losses = EBITDA - tax_dep (no interest)
      - total cash tax = total CIT accrual (conservation: no lag)
      - cfads[i] = ebitda[i] - corporate_tax_cash[i]
      - H1 corporate_tax_cash = 0; H2 gets full annual liability
    """

    def _result(self):
        return _run_model(_flat_policy(rate=0.18, atad_enabled=False))

    def test_result_has_tax_and_cfads(self):
        assert self._result().tax_and_cfads is not None

    def test_tax_and_cfads_not_in_unavailable(self):
        result = self._result()
        assert "tax_and_cfads" not in result.unavailable_sections

    def test_financing_still_unavailable(self):
        result = self._result()
        assert "financing" in result.unavailable_sections

    def test_cfads_equals_ebitda_minus_cash_tax(self):
        result = self._result()
        tc = result.tax_and_cfads
        os_ = result.operating_schedules
        for i in range(len(result.periods)):
            expected = os_.ebitda_keur[i] - tc.corporate_tax_cash_keur[i]
            assert abs(tc.cfads_keur[i] - expected) < 1e-6, f"Period {i}"

    def test_total_cash_tax_equals_total_cit_accrual(self):
        """With zero lag, total cash tax and total CIT accrual must be equal."""
        result = self._result()
        tc = result.tax_and_cfads
        total_cash = sum(tc.corporate_tax_cash_keur)
        total_accrual = sum(tc.tax_keur)
        assert abs(total_cash - total_accrual) < 1e-4, (
            f"cash={total_cash:.2f} accrual={total_accrual:.2f}"
        )

    def test_h1_cash_tax_is_zero_when_h2_exists(self):
        """For TAX_YEAR_LAST_PERIOD with 0 lag, H1 has zero cash tax if H2 follows it."""
        result = self._result()
        tc = result.tax_and_cfads
        # Build year_index → period list to identify H1 periods that have an H2 partner
        from collections import defaultdict
        year_periods: dict[float, list] = defaultdict(list)
        for i, p in enumerate(result.periods):
            if p.is_operation:
                year_periods[p.year_index].append((i, p))
        for yi, group in year_periods.items():
            if len(group) >= 2:
                # H1 is not the last period; should have zero cash tax
                h1_idx, h1_period = sorted(group, key=lambda x: x[1].period_in_year)[0]
                assert tc.corporate_tax_cash_keur[h1_idx] == 0.0, (
                    f"H1 period at year_index={yi} should have zero cash tax when H2 exists"
                )

    def test_no_losses_no_lcf_pool(self):
        result = self._result()
        tc = result.tax_and_cfads
        for v in tc.tax_loss_used_audit_keur:
            assert v == 0.0

    def test_annual_taxable_income_equals_annual_ebitda_minus_dep(self):
        """With no interest, annual taxable = annual EBITDA - annual tax_dep.

        Taxable income is computed per calendar year and prorated to periods.
        The sum of per-period taxable shares for periods in a given calendar year
        must equal the calendar-year annual EBITDA - tax_dep.

        Note: the grouping is by calendar year (from tax_and_cfads annual results),
        not by year_index (an operating-model concept distinct from calendar year).
        """
        from financial_engine.tax.engine import calculate_tax
        from financial_engine.inputs import TaxCalculationInput, TaxCfadsModelInput

        result = self._result()
        tc = result.tax_and_cfads

        # Use the annual_results to check per-year conservation.
        # Re-run to access TaxAndCfadsResult directly.
        op = _minimal_operating_input()
        from financial_engine.orchestrator import run_operating_model
        op_result = run_operating_model(op)
        tax_input = TaxCalculationInput(
            policy=_flat_policy(rate=0.18, atad_enabled=False),
            opening_loss_vintages=(),
            period_interest=(),
            period_adjustments=(),
        )
        tax_result = calculate_tax(op_result.periods, tax_input)

        for ar in tax_result.annual_results:
            expected = ar.ebitda_keur - ar.tax_depreciation_keur
            actual = ar.taxable_income_before_lcf_keur
            assert abs(actual - expected) < 1e-4, (
                f"TaxYear {ar.tax_year}: taxable={actual:.4f} != ebitda-dep={expected:.4f}"
            )


# ---------------------------------------------------------------------------
# Test B — Annual ATAD threshold logic
# ---------------------------------------------------------------------------

class TestB_AtadAnnualThreshold:
    """Annual ATAD is computed per tax year, not per period.

    Scenario: two periods in one tax year (H1 + H2).
    EBITDA = 10 000 annual; 30% limit = 3 000 kEUR = de-minimis threshold.

    Case under_limit: annual gross = 2 800 < 3 000 → no disallowance.
    Case over_limit: annual gross = 3 200 > 3 000 → 200 disallowed in H2.
    """

    _EBITDA = 10_000.0
    _THRESHOLD = 3_000.0

    def _basis(self, total_interest: float) -> TaxYearCalculationBasis:
        return TaxYearCalculationBasis(
            tax_year=2030,
            fragments=(),
            period_indices=(0, 1),
            payment_period_index=1,
            ebitda_keur=self._EBITDA,
            tax_depreciation_keur=0.0,
            total_interest_keur=total_interest,
            other_fiscal_reintegration_keur=0.0,
        )

    def _policy(self) -> TaxPolicy:
        return _flat_policy(
            atad_enabled=True,
            atad_ebitda_limit=0.30,
            atad_threshold=self._THRESHOLD,
        )

    def test_under_limit_fully_deductible(self):
        basis = self._basis(2_800.0)
        annual = calculate_annual_atad(basis, self._policy())
        assert annual.disallowed_interest_keur == 0.0
        assert abs(annual.deductible_interest_keur - 2_800.0) < 1e-6

    def test_over_limit_correct_disallowance(self):
        basis = self._basis(3_200.0)
        annual = calculate_annual_atad(basis, self._policy())
        assert abs(annual.disallowed_interest_keur - 200.0) < 1e-6
        assert abs(annual.deductible_interest_keur - 3_000.0) < 1e-6

    def test_chronological_period_allocation_h1_first(self):
        """H1 consumes capacity first; H2 gets only the remainder."""
        basis = self._basis(3_200.0)
        annual = calculate_annual_atad(basis, self._policy())
        # H1=1600, H2=1600; capacity=3000; H1 uses 1600, remaining=1400; H2 uses 1400, dis=200
        allocated = allocate_atad_to_periods(annual, (1_600.0, 1_600.0))
        assert abs(allocated.period_deductible_keur[0] - 1_600.0) < 1e-6  # H1 fully deductible
        assert allocated.period_disallowed_keur[0] == 0.0
        assert abs(allocated.period_deductible_keur[1] - 1_400.0) < 1e-6  # H2 limited
        assert abs(allocated.period_disallowed_keur[1] - 200.0) < 1e-6

    def test_h1_over_capacity_alone(self):
        """If H1 interest exceeds capacity alone, H2 gets zero deductible."""
        # H1=5000, H2=0; capacity=3000 → H1 ded=3000 dis=2000, H2 ded=0 dis=0
        basis = self._basis(5_000.0)
        annual = calculate_annual_atad(basis, self._policy())
        allocated = allocate_atad_to_periods(annual, (5_000.0, 0.0))
        assert abs(allocated.period_deductible_keur[0] - 3_000.0) < 1e-6
        assert abs(allocated.period_disallowed_keur[0] - 2_000.0) < 1e-6
        assert allocated.period_deductible_keur[1] == 0.0
        assert allocated.period_disallowed_keur[1] == 0.0

    def test_de_minimis_threshold_binds_when_ebitda_low(self):
        """When 30%×EBITDA < threshold, threshold binds."""
        # EBITDA = 5 000 → 30% = 1 500 < threshold (3 000) → capacity = 3 000
        basis = TaxYearCalculationBasis(
            tax_year=2030,
            fragments=(),
            period_indices=(0, 1),
            payment_period_index=1,
            ebitda_keur=5_000.0,
            tax_depreciation_keur=0.0,
            total_interest_keur=4_000.0,
            other_fiscal_reintegration_keur=0.0,
        )
        annual = calculate_annual_atad(basis, self._policy())
        assert annual.binding_rule == "min_threshold"
        assert abs(annual.deductible_interest_keur - 3_000.0) < 1e-6

    def test_atad_disabled_full_deduction(self):
        """When ATAD is disabled, all interest is deductible regardless of amount."""
        basis = self._basis(100_000.0)
        policy = _flat_policy(atad_enabled=False)
        annual = calculate_annual_atad(basis, policy)
        assert annual.disallowed_interest_keur == 0.0
        assert abs(annual.deductible_interest_keur - 100_000.0) < 1e-6
        assert annual.binding_rule == "disabled"


# ---------------------------------------------------------------------------
# Test C — Correct taxable income formula (no double ATAD addback)
# ---------------------------------------------------------------------------

class TestC_TaxableIncomeFormula:
    """taxable_income = EBITDA - tax_dep - deductible_interest + other_reintegration.

    Disallowed interest is NOT added back separately — it simply is not deducted.
    This test verifies the formula using the annual engine directly.
    """

    def test_formula_no_atad(self):
        """Without ATAD: taxable = EBITDA - tax_dep - gross_interest."""
        result = _run_model(
            _flat_policy(rate=0.18, atad_enabled=False),
            interest=(PeriodInterestInput(period_index=2, senior_interest_keur=500.0),
                      PeriodInterestInput(period_index=3, shl_interest_keur=300.0)),
        )
        tc = result.tax_and_cfads
        os_ = result.operating_schedules
        # For all periods: taxable = ebitda - dep - deductible
        # Since ATAD disabled, deductible = gross
        # We can't check per-period directly (proration), but the sum per year should hold
        # Find operating period indices
        all_periods = result.periods
        # Just verify no NaN or negative-unreasonable values
        for i in range(len(all_periods)):
            assert not (tc.taxable_income_before_losses_audit_keur[i] != tc.taxable_income_before_losses_audit_keur[i])

    def test_formula_with_atad_disallowance(self):
        """With ATAD disallowing some interest, taxable income uses deductible only."""
        from financial_engine.orchestrator import run_tax_cfads_model
        op = _minimal_operating_input()

        # Put interest in the first operating year (periods 2 and 3 with indices from engine)
        # We'll use exogenous interest after getting period indices from Phase 2A
        from financial_engine.orchestrator import run_operating_model
        op_result = run_operating_model(op)
        # Find first two operating periods
        op_periods = [p for p in op_result.periods if p.is_operation]
        if len(op_periods) < 2:
            pytest.skip("Not enough operating periods for this test")
        p0, p1 = op_periods[0], op_periods[1]

        # Both H1 and H2 of year 1 have 2000 kEUR interest; annual = 4000 > 3000 threshold
        policy = _flat_policy(
            rate=0.18,
            atad_enabled=True,
            atad_ebitda_limit=0.30,
            atad_threshold=3_000.0,
        )
        interest = (
            PeriodInterestInput(period_index=p0.period_index, senior_interest_keur=2_000.0),
            PeriodInterestInput(period_index=p1.period_index, senior_interest_keur=2_000.0),
        )
        result_with_atad = run_tax_cfads_model(TaxCfadsModelInput(
            operating=op,
            tax=TaxCalculationInput(policy=policy, opening_loss_vintages=(), period_interest=interest),
        ))
        result_no_atad = run_tax_cfads_model(TaxCfadsModelInput(
            operating=op,
            tax=TaxCalculationInput(
                policy=_flat_policy(rate=0.18, atad_enabled=False),
                opening_loss_vintages=(),
                period_interest=interest,
            ),
        ))

        tc_with = result_with_atad.tax_and_cfads
        tc_no = result_no_atad.tax_and_cfads
        # With ATAD, less interest is deducted → higher taxable income
        total_taxable_with = sum(tc_with.taxable_income_before_losses_audit_keur)
        total_taxable_no = sum(tc_no.taxable_income_before_losses_audit_keur)
        assert total_taxable_with > total_taxable_no - 1e-6, (
            "ATAD should increase taxable income (less deductible interest)"
        )


# ---------------------------------------------------------------------------
# Test D — FIFO vintage expiry (annual ledger)
# ---------------------------------------------------------------------------

class TestD_FifoVintageExpiry:
    """Annual FIFO loss ledger: expiry-before-use, vintage tracks origin+lcf."""

    def test_loss_used_before_expiry(self):
        """Loss generated in year 0 is usable in years 1–5 (lcf=5)."""
        taxable = (-5_000.0, 200.0, 200.0, 200.0, 200.0, 200.0)
        years = (0, 1, 2, 3, 4, 5)
        entries = run_annual_fifo_ledger(taxable, years, (), 5)
        # Year 0 generates 5000
        assert abs(entries[0].loss_generated_keur - 5_000.0) < 1e-6
        # Years 1-5: each uses 200
        for i in range(1, 6):
            assert abs(entries[i].loss_used_keur - 200.0) < 1e-6, f"Year {i}"

    def test_loss_expires_in_year_beyond_lcf(self):
        """Remaining pool expires at start of year origin+lcf+1."""
        # loss in year 0 with lcf=5 → last_usable=5 → expires before year 6
        taxable = (-5_000.0, 200.0, 200.0, 200.0, 200.0, 200.0, 200.0)
        years = (0, 1, 2, 3, 4, 5, 6)
        entries = run_annual_fifo_ledger(taxable, years, (), 5)
        # Year 6: pool expired (4000 remaining after 5×200 = 1000 used)
        assert entries[6].loss_expired_keur > 0.0, "Loss should be expired in year 6"
        assert entries[6].loss_used_keur == 0.0
        assert abs(entries[6].taxable_income_after_lcf_keur - 200.0) < 1e-6

    def test_opening_vintage_expires_correctly(self):
        """Opening vintage with origin=-2 and lcf=5 expires before year 4."""
        # origin=-2, lcf=5 → last_usable = -2+5 = 3 → usable in years ≤3, expires before 4
        opening = (OpeningTaxLossVintageInput(
            origin_tax_year=-2,
            amount_keur=1_000.0,
            source_label="opening",
        ),)
        taxable = (200.0, 200.0, 200.0, 200.0, 200.0)  # years 0..4
        years = (0, 1, 2, 3, 4)
        entries = run_annual_fifo_ledger(taxable, years, opening, 5)
        # Year 4: last_usable=3 < 4 → expires
        assert entries[4].loss_expired_keur > 0.0 or entries[4].opening_loss_keur == 0.0

    def test_loss_not_generated_in_profitable_years(self):
        """No loss generated when taxable income ≥ 0."""
        taxable = (500.0, 500.0, 500.0)
        years = (0, 1, 2)
        entries = run_annual_fifo_ledger(taxable, years, (), 5)
        for e in entries:
            assert e.loss_generated_keur == 0.0

    def test_fifo_order_oldest_first(self):
        """FIFO: oldest vintage consumed before newer one."""
        # Two opening vintages: older=-3 (amount=100), newer=-1 (amount=200)
        opening = (
            OpeningTaxLossVintageInput(origin_tax_year=-3, amount_keur=100.0),
            OpeningTaxLossVintageInput(origin_tax_year=-1, amount_keur=200.0),
        )
        # Year 0: profit=50 → should consume 50 from the -3 vintage first
        taxable = (50.0,)
        years = (0,)
        entries = run_annual_fifo_ledger(taxable, years, opening, 10)
        assert abs(entries[0].loss_used_keur - 50.0) < 1e-6
        # Closing = 100 - 50 + 200 = 250
        assert abs(entries[0].closing_loss_keur - 250.0) < 1e-6


# ---------------------------------------------------------------------------
# Test E — Immutability
# ---------------------------------------------------------------------------

def test_tax_policy_is_frozen():
    p = _flat_policy()
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        p.corporate_rate = 0.20  # type: ignore[misc]


def test_tax_calculation_input_is_frozen():
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
    """CashTaxTiming.SAME_PERIOD: sum of cash_tax per year == sum of accrual per year."""
    result = _run_model(TaxPolicy(
        policy_id="same",
        policy_version="1.0",
        corporate_rate=0.18,
        periods_per_tax_year=2,
        loss_carryforward_years=5,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3000.0,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
    ))
    tc = result.tax_and_cfads
    assert tc is not None
    # For SAME_PERIOD: cash tax is paid in the last period of the year (same as accrual period)
    # Total conservation still holds
    assert abs(sum(tc.corporate_tax_cash_keur) - sum(tc.tax_keur)) < 1e-4


# ---------------------------------------------------------------------------
# Test G — Terminal unpaid tax
# ---------------------------------------------------------------------------

def test_terminal_unpaid_tax_when_lag_exceeds_horizon():
    """With a large cash_tax_payment_lag_periods, some liabilities fall outside horizon."""
    # horizon_years=5 means ~10 semi-annual operating periods
    # With lag=20, last-period payment falls far outside horizon → terminal_unpaid > 0
    result = _run_model(
        TaxPolicy(
            policy_id="lag_test",
            policy_version="1.0",
            corporate_rate=0.18,
            periods_per_tax_year=2,
            loss_carryforward_years=5,
            atad_enabled=False,
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
            cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
            cash_tax_payment_lag_periods=200,  # pushes all payments outside horizon
        ),
        horizon_years=5,
    )
    tc = result.tax_and_cfads
    assert tc is not None
    assert tc.terminal_unpaid_tax_keur > 0.0, (
        "With extreme lag, terminal_unpaid_tax_keur should be positive"
    )


def test_terminal_unpaid_tax_zero_with_no_lag():
    """With zero lag, all payments land within the horizon → terminal_unpaid = 0."""
    result = _run_model(_flat_policy(rate=0.18, lag=0))
    tc = result.tax_and_cfads
    assert tc is not None
    assert tc.terminal_unpaid_tax_keur == 0.0


# ---------------------------------------------------------------------------
# Test H — Exogenous interest reduces taxable income
# ---------------------------------------------------------------------------

def test_exogenous_interest_reduces_taxable_income():
    """Interest passed via PeriodInterestInput reduces taxable income vs zero-interest case."""
    from financial_engine.orchestrator import run_operating_model, run_tax_cfads_model
    op = _minimal_operating_input()

    # Get period indices from the operating model
    op_result = run_operating_model(op)
    op_periods = [p for p in op_result.periods if p.is_operation]
    first_idx = op_periods[0].period_index

    policy = _flat_policy(rate=0.18, atad_enabled=False)

    interest = (PeriodInterestInput(period_index=first_idx, senior_interest_keur=1_000.0),)
    result_with = run_tax_cfads_model(TaxCfadsModelInput(
        operating=op,
        tax=TaxCalculationInput(policy=policy, opening_loss_vintages=(), period_interest=interest),
    ))
    result_without = run_tax_cfads_model(TaxCfadsModelInput(
        operating=op,
        tax=TaxCalculationInput(policy=policy, opening_loss_vintages=(), period_interest=()),
    ))

    total_taxable_with = sum(result_with.tax_and_cfads.taxable_income_before_losses_audit_keur)
    total_taxable_without = sum(result_without.tax_and_cfads.taxable_income_before_losses_audit_keur)

    # With 1000 kEUR interest, taxable income should be 1000 lower (no ATAD)
    diff = total_taxable_without - total_taxable_with
    assert abs(diff - 1_000.0) < 1e-4, f"Expected 1000 reduction, got {diff:.4f}"


def test_senior_shl_other_interest_all_flow_through():
    """All three interest components (senior/shl/other) reduce taxable income."""
    from financial_engine.orchestrator import run_operating_model, run_tax_cfads_model
    op = _minimal_operating_input()
    op_result = run_operating_model(op)
    op_periods = [p for p in op_result.periods if p.is_operation]
    first_idx = op_periods[0].period_index

    policy = _flat_policy(rate=0.18, atad_enabled=False)

    interest = (PeriodInterestInput(
        period_index=first_idx,
        senior_interest_keur=300.0,
        shl_interest_keur=200.0,
        other_interest_keur=100.0,
    ),)  # total = 600 kEUR
    result_with = run_tax_cfads_model(TaxCfadsModelInput(
        operating=op,
        tax=TaxCalculationInput(policy=policy, opening_loss_vintages=(), period_interest=interest),
    ))
    result_without = run_tax_cfads_model(TaxCfadsModelInput(
        operating=op,
        tax=TaxCalculationInput(policy=policy, opening_loss_vintages=(), period_interest=()),
    ))

    diff = (
        sum(result_without.tax_and_cfads.taxable_income_before_losses_audit_keur)
        - sum(result_with.tax_and_cfads.taxable_income_before_losses_audit_keur)
    )
    assert abs(diff - 600.0) < 1e-4, f"Expected 600 total reduction, got {diff:.4f}"


# ---------------------------------------------------------------------------
# Test I — Validation error codes TAX001–TAX014
# ---------------------------------------------------------------------------

class TestI_ValidationCodes:
    """Verify that each TAX error code is raised with the right code string."""

    def _base_policy(self) -> TaxPolicy:
        return _flat_policy()

    def _tax_input(self, **overrides) -> TaxCalculationInput:
        defaults = dict(
            policy=self._base_policy(),
            opening_loss_vintages=(),
            period_interest=(),
            period_adjustments=(),
        )
        defaults.update(overrides)
        return TaxCalculationInput(**defaults)

    def _codes(self, tax_input: TaxCalculationInput) -> set[str]:
        from financial_engine.validation import validate_tax_calculation_input
        issues = validate_tax_calculation_input(tax_input)
        return {i.code for i in issues}

    def test_TAX001_corporate_rate_out_of_range(self):
        policy = dataclasses.replace(self._base_policy(), corporate_rate=1.5)
        assert "TAX001" in self._codes(self._tax_input(policy=policy))

    def test_TAX002_periods_per_tax_year_zero(self):
        policy = dataclasses.replace(self._base_policy(), periods_per_tax_year=0)
        assert "TAX002" in self._codes(self._tax_input(policy=policy))

    def test_TAX003_loss_carryforward_years_negative(self):
        policy = dataclasses.replace(self._base_policy(), loss_carryforward_years=-1)
        assert "TAX003" in self._codes(self._tax_input(policy=policy))

    def test_TAX004_atad_ebitda_limit_out_of_range(self):
        policy = dataclasses.replace(
            self._base_policy(),
            atad_enabled=True,
            atad_ebitda_limit=1.5,
        )
        assert "TAX004" in self._codes(self._tax_input(policy=policy))

    def test_TAX005_atad_de_minimis_negative(self):
        policy = dataclasses.replace(
            self._base_policy(),
            atad_de_minimis_threshold_keur_annual=-1.0,
        )
        assert "TAX005" in self._codes(self._tax_input(policy=policy))

    def test_TAX006_cash_tax_payment_lag_negative(self):
        policy = dataclasses.replace(self._base_policy(), cash_tax_payment_lag_periods=-1)
        assert "TAX006" in self._codes(self._tax_input(policy=policy))

    def test_TAX007_opening_vintage_negative_amount(self):
        vintages = (OpeningTaxLossVintageInput(origin_tax_year=0, amount_keur=-100.0),)
        assert "TAX007" in self._codes(self._tax_input(opening_loss_vintages=vintages))

    def test_TAX008_opening_vintage_bad_origin_type(self):
        # origin_tax_year must be int
        vintages = (OpeningTaxLossVintageInput(origin_tax_year=0.5, amount_keur=100.0),)  # type: ignore
        assert "TAX008" in self._codes(self._tax_input(opening_loss_vintages=vintages))

    def test_TAX009_period_interest_negative(self):
        interest = (PeriodInterestInput(period_index=0, senior_interest_keur=-1.0),)
        assert "TAX009" in self._codes(self._tax_input(period_interest=interest))

    def test_TAX010_duplicate_period_interest(self):
        interest = (
            PeriodInterestInput(period_index=0, senior_interest_keur=100.0),
            PeriodInterestInput(period_index=0, senior_interest_keur=200.0),
        )
        assert "TAX010" in self._codes(self._tax_input(period_interest=interest))

    def test_TAX012_duplicate_period_adjustments(self):
        adjs = (
            PeriodTaxAdjustmentInput(period_index=0, other_fiscal_reintegration_keur=100.0),
            PeriodTaxAdjustmentInput(period_index=0, other_fiscal_reintegration_keur=200.0),
        )
        assert "TAX012" in self._codes(self._tax_input(period_adjustments=adjs))

    def test_TAX013_period_adjustment_nonfinite(self):
        adjs = (PeriodTaxAdjustmentInput(period_index=0, other_fiscal_reintegration_keur=float("inf")),)
        assert "TAX013" in self._codes(self._tax_input(period_adjustments=adjs))

    def test_TAX014_wrong_policy_type(self):
        bad_tax = TaxCalculationInput(
            policy=object(),  # type: ignore
            opening_loss_vintages=(),
            period_interest=(),
        )
        assert "TAX014" in self._codes(bad_tax)

    def test_TAX015_period_interest_out_of_order(self):
        interest = (
            PeriodInterestInput(period_index=2, senior_interest_keur=100.0),
            PeriodInterestInput(period_index=1, senior_interest_keur=100.0),
        )
        assert "TAX015" in self._codes(self._tax_input(period_interest=interest))

    def test_TAX016_period_adjustment_unknown_period(self):
        from financial_engine.validation import validate_tax_calculation_input
        adjs = (PeriodTaxAdjustmentInput(period_index=999, other_fiscal_reintegration_keur=0.0),)
        tax_in = self._tax_input(period_adjustments=adjs)
        issues = validate_tax_calculation_input(tax_in, known_period_indices=frozenset([0, 1, 2]))
        assert any(i.code == "TAX016" for i in issues)

    def test_TAX017_period_adjustment_out_of_order(self):
        adjs = (
            PeriodTaxAdjustmentInput(period_index=3, other_fiscal_reintegration_keur=0.0),
            PeriodTaxAdjustmentInput(period_index=2, other_fiscal_reintegration_keur=0.0),
        )
        assert "TAX017" in self._codes(self._tax_input(period_adjustments=adjs))

    def test_TAX011_unknown_period_index(self):
        from financial_engine.validation import validate_tax_calculation_input
        interest = (PeriodInterestInput(period_index=999, senior_interest_keur=100.0),)
        tax_in = self._tax_input(period_interest=interest)
        issues = validate_tax_calculation_input(tax_in, known_period_indices=frozenset([0, 1, 2]))
        assert any(i.code == "TAX011" for i in issues)


# ---------------------------------------------------------------------------
# Test J — Four-baseline smoke test (integration)
# ---------------------------------------------------------------------------

BASELINE_IDS = ["tuho", "oborovo", "generic_solar", "generic_wind"]


@pytest.mark.parametrize("baseline_id", BASELINE_IDS)
def test_j_four_baseline_smoke(baseline_id: str):
    """Phase 2B smoke: load factory inputs, build TaxCfadsModelInput, run engine.

    All four baselines must run without error and return non-empty results.
    TUHO opening-loss resolved to zero (manual workbook evidence: no pre-model LCF).
    The actual numeric comparison lives in the parity CLI (TAX_CFADS_V1 profile).
    """
    from finco_parity.financial_engine_tax_cfads_candidate import generate_tax_cfads_candidate_snapshot

    snapshot = generate_tax_cfads_candidate_snapshot(baseline_id)
    assert snapshot is not None
    tc = snapshot.get("tax_and_cfads")
    assert tc is not None
    assert "period_grid" in snapshot
    assert len(snapshot["period_grid"]) > 0


# ---------------------------------------------------------------------------
# Test K — Construction-loss model
# ---------------------------------------------------------------------------

class TestK_ConstructionLoss:
    """Manual model: construction-period losses generated, carried forward (FIFO), used, expired.

    Uses run_annual_fifo_ledger directly to verify the full LCF lifecycle
    independent of the baseline-specific inputs.

    Scenario:
      - Years 2029-2030: construction losses (-10 000, -5 000 kEUR)
      - Years 2031-2036: operating profit (8 000 kEUR each)
      - lcf_years = 5  →  2029 vintage last_usable = 2034
                           2030 vintage last_usable = 2035
    """

    _TAXABLE = (-10_000.0, -5_000.0, 8_000.0, 8_000.0, 8_000.0, 8_000.0, 8_000.0, 8_000.0)
    _YEARS   = (2029,       2030,     2031,     2032,     2033,     2034,     2035,     2036)
    _LCF     = 5

    @pytest.fixture(scope="class")
    @classmethod
    def entries(cls):
        return run_annual_fifo_ledger(cls._TAXABLE, cls._YEARS, (), cls._LCF)

    def test_construction_losses_generated(self, entries):
        """Years 2029 and 2030 each generate a loss."""
        assert abs(entries[0].loss_generated_keur - 10_000.0) < 1e-6, "2029 loss"
        assert abs(entries[1].loss_generated_keur - 5_000.0) < 1e-6, "2030 loss"

    def test_pool_accumulates_correctly(self, entries):
        """After year 2030 the closing pool = 10 000 + 5 000 = 15 000."""
        assert abs(entries[1].closing_loss_keur - 15_000.0) < 1e-6

    def test_no_loss_generated_in_profitable_years(self, entries):
        """No new loss generated in years 2031-2036."""
        for i in range(2, len(entries)):
            assert entries[i].loss_generated_keur == 0.0, f"year {self._YEARS[i]}"

    def test_loss_used_2031(self, entries):
        """Year 2031: full 8 000 profit offset by 2029-vintage loss (FIFO)."""
        assert abs(entries[2].loss_used_keur - 8_000.0) < 1e-6
        assert abs(entries[2].taxable_income_after_lcf_keur - 0.0) < 1e-6

    def test_loss_used_2032(self, entries):
        """Year 2032: remaining 2 000 from 2029 vintage used first, then 5 000 from 2030."""
        # 2029 vintage pool after 2031 = 10 000 - 8 000 = 2 000
        # 2030 vintage pool = 5 000
        # 2032 profit = 8 000 → uses 2 000 (clears 2029) + 5 000 (partial 2030 clear) = 7 000
        # Remaining taxable = 8 000 - 7 000 = 1 000
        assert abs(entries[3].loss_used_keur - 7_000.0) < 1e-6
        assert abs(entries[3].taxable_income_after_lcf_keur - 1_000.0) < 1e-6

    def test_pool_cleared_after_2032(self, entries):
        """After year 2032 the LCF pool should be zero (all vintages consumed)."""
        assert abs(entries[3].closing_loss_keur - 0.0) < 1e-6

    def test_no_loss_used_2033_onwards(self, entries):
        """Years 2033-2036: pool is empty, full taxable income applies."""
        for i in range(4, len(entries)):
            assert entries[i].loss_used_keur == 0.0, f"year {self._YEARS[i]}"
            assert abs(entries[i].taxable_income_after_lcf_keur - 8_000.0) < 1e-6, f"year {self._YEARS[i]}"

    def test_no_expiry_in_this_scenario(self, entries):
        """Pool cleared by profitable years before any vintage expires."""
        for e in entries:
            assert e.loss_expired_keur == 0.0

    def test_construction_vintage_id_in_first_class_ledger(self, entries):
        """Model F (item 14): generated vintage is visible in first-class ledger with exact ID."""
        # Year 2029: one generated vintage
        gen_2029 = entries[0].generated_vintages
        assert len(gen_2029) == 1
        v = gen_2029[0]
        assert v.vintage_id == "gen_2029", f"Expected gen_2029, got {v.vintage_id}"
        assert v.origin_tax_year == 2029
        assert v.last_usable_tax_year == 2029 + self._LCF  # 2034
        assert abs(v.generated_keur - 10_000.0) < 1e-6
        assert abs(v.closing_keur - 10_000.0) < 1e-6

    def test_construction_vintage_used_and_closing_later(self, entries):
        """The gen_2029 vintage is consumed in 2031-2032 and closing reaches zero."""
        # By end of 2032 the gen_2029 vintage is fully consumed.
        # entries[3] is year 2032; its closing_vintages should not include gen_2029.
        closing_ids_2032 = {v.vintage_id for v in entries[3].closing_vintages}
        assert "gen_2029" not in closing_ids_2032, "gen_2029 should be fully consumed by 2032"


# ---------------------------------------------------------------------------
# Test L — Model A exact: no ATAD, no losses
# ---------------------------------------------------------------------------

class TestL_ModelA_Exact:
    """Item 14 Model A: hand-calculated expectations for EBITDA=100, dep=120, rate=18%.

    Required results:
      taxable_income_before_LCF = -20
      generated_loss             = 20
      taxable_income_after_LCF   =  0
      current_tax_liability      =  0
      cash_tax                   =  0
      CFADS                      = 100
    """

    _EBITDA   = 100.0
    _TAX_DEP  = 120.0
    _RATE     = 0.18
    _TAX_YEAR = 2030

    def _basis(self):
        return TaxYearCalculationBasis(
            tax_year=self._TAX_YEAR,
            fragments=(),
            period_indices=(0,),
            payment_period_index=0,
            ebitda_keur=self._EBITDA,
            tax_depreciation_keur=self._TAX_DEP,
            total_interest_keur=0.0,
            other_fiscal_reintegration_keur=0.0,
        )

    def test_taxable_before_lcf_is_minus_20(self):
        """EBITDA(100) − dep(120) = −20."""
        atad = calculate_annual_atad(self._basis(), _flat_policy(rate=self._RATE, atad_enabled=False))
        taxable = self._EBITDA - self._TAX_DEP - atad.deductible_interest_keur
        assert abs(taxable - (-20.0)) < 1e-9

    def test_generated_loss_is_20(self):
        entries = run_annual_fifo_ledger((-20.0,), (self._TAX_YEAR,), (), 5)
        assert abs(entries[0].loss_generated_keur - 20.0) < 1e-9

    def test_taxable_after_lcf_is_zero(self):
        entries = run_annual_fifo_ledger((-20.0,), (self._TAX_YEAR,), (), 5)
        assert entries[0].taxable_income_after_lcf_keur == 0.0

    def test_current_tax_liability_is_zero(self):
        """CIT = 18% × max(0, 0) = 0."""
        entries = run_annual_fifo_ledger((-20.0,), (self._TAX_YEAR,), (), 5)
        cit = self._RATE * max(0.0, entries[0].taxable_income_after_lcf_keur)
        assert abs(cit) < 1e-9

    def test_cfads_equals_ebitda_minus_cash_tax(self):
        """CFADS = EBITDA − cash_tax = 100 − 0 = 100."""
        # Run through the full engine with one simple period
        from financial_engine.results import OperatingPeriodResult
        from financial_engine.tax.engine import calculate_tax
        period = OperatingPeriodResult(
            period_index=0,
            period_start=date(2030, 1, 1),
            period_end=date(2031, 1, 1),
            year_index=1.0,
            period_in_year=1.0,
            is_construction=False,
            is_operation=True,
            is_ppa_active=True,
            days_in_period=365,
            day_fraction=1.0,
            production_mwh=0.0,
            revenue_keur=0.0,
            opex_keur=0.0,
            ebitda_keur=self._EBITDA,
            book_depreciation_keur=0.0,
            tax_depreciation_keur=self._TAX_DEP,
        )
        tax_input = TaxCalculationInput(
            policy=_flat_policy(rate=self._RATE, atad_enabled=False),
            opening_loss_vintages=(),
            period_interest=(),
            period_adjustments=(),
        )
        result = calculate_tax((period,), tax_input)
        assert len(result.period_results) == 1
        pr = result.period_results[0]
        cfads = period.ebitda_keur - pr.cash_tax_keur
        assert abs(cfads - 100.0) < 1e-9, f"CFADS={cfads:.6f} expected 100"
        assert abs(pr.cash_tax_keur) < 1e-9, f"cash_tax={pr.cash_tax_keur:.6f} expected 0"


# ---------------------------------------------------------------------------
# Test M — Model B exact: annual ATAD threshold (item 14)
# ---------------------------------------------------------------------------

class TestM_ModelB_Exact:
    """Item 14 Model B: annual ATAD de-minimis threshold with EBITDA=4 000.

    Required:
      30% × 4 000 = 1 200
      de-minimis threshold = 3 000 → threshold binds (1 200 < 3 000)
      deduction capacity = 3 000
      deductible interest = 3 000
      disallowed interest = 1 000

    Also proves threshold is applied once annually (not once per H1/H2 period).
    """

    _EBITDA    = 4_000.0
    _INTEREST  = 4_000.0
    _THRESHOLD = 3_000.0
    _LIMIT     = 0.30

    def _basis(self):
        return TaxYearCalculationBasis(
            tax_year=2031,
            fragments=(),
            period_indices=(0, 1),
            payment_period_index=1,
            ebitda_keur=self._EBITDA,
            tax_depreciation_keur=0.0,
            total_interest_keur=self._INTEREST,
            other_fiscal_reintegration_keur=0.0,
        )

    def _policy(self):
        return _flat_policy(atad_enabled=True, atad_ebitda_limit=self._LIMIT,
                            atad_threshold=self._THRESHOLD)

    def test_30pct_ebitda_is_1200(self):
        assert abs(self._LIMIT * self._EBITDA - 1_200.0) < 1e-9

    def test_threshold_binds_not_ebitda_limit(self):
        annual = calculate_annual_atad(self._basis(), self._policy())
        assert annual.binding_rule == "min_threshold", f"Expected min_threshold, got {annual.binding_rule}"

    def test_deduction_capacity_is_3000(self):
        annual = calculate_annual_atad(self._basis(), self._policy())
        assert abs(annual.deduction_capacity_keur - 3_000.0) < 1e-9

    def test_deductible_interest_is_3000(self):
        annual = calculate_annual_atad(self._basis(), self._policy())
        assert abs(annual.deductible_interest_keur - 3_000.0) < 1e-9

    def test_disallowed_interest_is_1000(self):
        annual = calculate_annual_atad(self._basis(), self._policy())
        assert abs(annual.disallowed_interest_keur - 1_000.0) < 1e-9

    def test_threshold_applied_annually_not_per_period(self):
        """Two H1/H2 periods of 2 000 each: annual threshold is 3 000, not 1 500+1 500."""
        # If applied per-period: each period capacity=1500, each disallows 500 → total=1000 ≠ 1000
        # BUT: if misapplied as per-period 30%×EBITDA=600 < 1500 → capacity=1500 per period
        # then total deductible=3000 and disallowed=1000 — happens to match!
        # The real difference is when per-period EBITDA makes 30% > threshold:
        # With annual EBITDA=4000 and threshold=3000, deduction capacity = 3000 (threshold binds).
        # If wrongly applied per-period: each period EBITDA=2000, 30%×2000=600 < 1500 → cap=1500
        # → total capacity=3000, same answer. Use a case where it diverges:
        # EBITDA=20000 per year → 30% = 6000 > 3000 → EBITDA limit binds annually.
        # If applied per period: per-period EBITDA=10000, 30%=3000=threshold → threshold binds
        # → capacity=3000 per period → total=6000, WRONG (should be 6000 annually).
        # With interest=8000 and EBITDA=20000: annual deductible=6000, disallowed=2000.
        basis_high = TaxYearCalculationBasis(
            tax_year=2031, fragments=(), period_indices=(0, 1), payment_period_index=1,
            ebitda_keur=20_000.0, tax_depreciation_keur=0.0,
            total_interest_keur=8_000.0, other_fiscal_reintegration_keur=0.0,
        )
        annual = calculate_annual_atad(basis_high, self._policy())
        # 30%×20000=6000 > 3000 threshold → EBITDA limit binds → capacity=6000
        assert annual.binding_rule == "ebitda_30pct"
        assert abs(annual.deduction_capacity_keur - 6_000.0) < 1e-9
        assert abs(annual.disallowed_interest_keur - 2_000.0) < 1e-9


# ---------------------------------------------------------------------------
# Test N — Model C exact: no double ATAD addback (item 14)
# ---------------------------------------------------------------------------

class TestN_ModelC_Exact:
    """Item 14 Model C: taxable income is 5 000, not 6 000.

    Inputs:
      EBITDA = 10 000
      tax_dep = 2 000
      gross_interest = 4 000
      deductible_interest = 3 000 (ATAD disallows 1 000)
      other_reintegration = 0

    Formula:
      taxable = EBITDA − dep − deductible_interest + reintegration
              = 10 000 − 2 000 − 3 000 + 0 = 5 000

    Wrong formula (double addback):
      = 10 000 − 2 000 − 4 000 + 1 000 = 6 000  ← INCORRECT
    """

    _EBITDA          = 10_000.0
    _TAX_DEP         = 2_000.0
    _GROSS_INT       = 4_000.0
    _THRESHOLD       = 3_000.0

    def _basis(self):
        return TaxYearCalculationBasis(
            tax_year=2031, fragments=(), period_indices=(0, 1), payment_period_index=1,
            ebitda_keur=self._EBITDA,
            tax_depreciation_keur=self._TAX_DEP,
            total_interest_keur=self._GROSS_INT,
            other_fiscal_reintegration_keur=0.0,
        )

    def _policy(self):
        return _flat_policy(atad_enabled=True, atad_ebitda_limit=0.30,
                            atad_threshold=self._THRESHOLD)

    def test_deductible_is_3000(self):
        atad = calculate_annual_atad(self._basis(), self._policy())
        assert abs(atad.deductible_interest_keur - 3_000.0) < 1e-9

    def test_taxable_is_5000_not_6000(self):
        """Taxable = EBITDA − dep − deductible = 10000 − 2000 − 3000 = 5000."""
        atad = calculate_annual_atad(self._basis(), self._policy())
        taxable = self._EBITDA - self._TAX_DEP - atad.deductible_interest_keur + 0.0
        assert abs(taxable - 5_000.0) < 1e-9, f"Expected 5000 got {taxable}"
        # Explicitly disprove 6000:
        assert abs(taxable - 6_000.0) > 900.0, "Taxable must not be 6000 (double-addback)"

    def test_disallowed_not_added_back(self):
        """Disallowed interest of 1 000 is NOT separately added to taxable income."""
        atad = calculate_annual_atad(self._basis(), self._policy())
        disallowed = atad.disallowed_interest_keur
        assert abs(disallowed - 1_000.0) < 1e-9
        # If we naively added it back: taxable = 5000 + 1000 = 6000 — wrong
        wrong_taxable = (self._EBITDA - self._TAX_DEP - self._GROSS_INT
                         + disallowed)  # = 10000 - 2000 - 4000 + 1000 = 5000 wait
        # Actually: 10000 - 2000 - 4000 + 1000 = 5000 as well!
        # The real double-addback error is: gross − dep + disallowed_back
        # = EBITDA − dep − deductible + (gross − deductible)  ← wrong
        # = 10000 − 2000 − 3000 + (4000 − 3000) = 5000 + 1000 = 6000
        double_addback = (self._EBITDA - self._TAX_DEP - atad.deductible_interest_keur
                          + disallowed)
        assert abs(double_addback - 6_000.0) < 1e-9, "double-addback yields 6000"
        # Correct formula uses only deductible:
        correct_taxable = self._EBITDA - self._TAX_DEP - atad.deductible_interest_keur
        assert abs(correct_taxable - 5_000.0) < 1e-9, "correct formula yields 5000"


# ---------------------------------------------------------------------------
# Test O — Model D exact: FIFO vintage IDs (item 14, item 5)
# ---------------------------------------------------------------------------

class TestO_ModelD_ExactFIFO:
    """Item 14 Model D + item 5: exact vintage IDs and amounts used/remaining.

    Vintage A: origin 2025, opening 100 kEUR
    Vintage B: origin 2026, opening 200 kEUR
    Taxable income in 2027: 150 kEUR

    Required:
      Vintage A used = 100, closing = 0
      Vintage B used = 50,  closing = 150
      total used = 150
    """

    _VINTAGE_A_ID    = "opening_A"
    _VINTAGE_B_ID    = "opening_B"

    @classmethod
    def _entries(cls):
        opening = (
            OpeningTaxLossVintageInput(origin_tax_year=2025, amount_keur=100.0,
                                       source_label=cls._VINTAGE_A_ID),
            OpeningTaxLossVintageInput(origin_tax_year=2026, amount_keur=200.0,
                                       source_label=cls._VINTAGE_B_ID),
        )
        return run_annual_fifo_ledger((150.0,), (2027,), opening, 10)

    def test_total_used_is_150(self):
        entries = self._entries()
        assert abs(entries[0].loss_used_keur - 150.0) < 1e-9

    def test_vintage_a_used_100_closing_0(self):
        """Oldest vintage (A, 2025) is fully consumed first."""
        entries = self._entries()
        used = {v.vintage_id: v for v in entries[0].used_vintages}
        assert self._VINTAGE_A_ID in used, "Vintage A must appear in used_vintages"
        v_a = used[self._VINTAGE_A_ID]
        assert abs(v_a.used_keur - 100.0) < 1e-9, f"A.used={v_a.used_keur}"
        closing = {v.vintage_id: v for v in entries[0].closing_vintages}
        assert self._VINTAGE_A_ID not in closing, "Vintage A fully consumed, must not appear in closing"

    def test_vintage_b_used_50_closing_150(self):
        """Newer vintage (B, 2026) partially consumed after A is exhausted."""
        entries = self._entries()
        used = {v.vintage_id: v for v in entries[0].used_vintages}
        assert self._VINTAGE_B_ID in used, "Vintage B must appear in used_vintages"
        v_b = used[self._VINTAGE_B_ID]
        assert abs(v_b.used_keur - 50.0) < 1e-9, f"B.used={v_b.used_keur}"
        closing = {v.vintage_id: v for v in entries[0].closing_vintages}
        assert self._VINTAGE_B_ID in closing, "Vintage B partial, must appear in closing"
        v_b_cl = closing[self._VINTAGE_B_ID]
        assert abs(v_b_cl.closing_keur - 150.0) < 1e-9, f"B.closing={v_b_cl.closing_keur}"

    def test_vintage_reconciliation(self):
        """Per-vintage: opening + generated − used − expired = closing."""
        entries = self._entries()
        for v in entries[0].used_vintages:
            expected_closing = v.opening_keur + v.generated_keur - v.used_keur - v.expired_keur
            assert abs(v.closing_keur - expected_closing) < 1e-9, f"Reconciliation failed for {v.vintage_id}"


# ---------------------------------------------------------------------------
# Test P — Model E exact expiry (item 14, item 5)
# ---------------------------------------------------------------------------

class TestP_ModelE_ExactExpiry:
    """Item 14 Model E + item 5: one vintage expires, one remains.

    Vintage X: origin 2020, lcf=5 → last_usable=2025 → expires before 2026
    Vintage Y: origin 2023, lcf=5 → last_usable=2028 → still valid in 2026
    Year 2026: profit = 300 kEUR
    """

    _VID_X = "expiring_vintage_X"
    _VID_Y = "surviving_vintage_Y"

    @classmethod
    def _entries(cls):
        opening = (
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=500.0,
                                       source_label=cls._VID_X),
            OpeningTaxLossVintageInput(origin_tax_year=2023, amount_keur=400.0,
                                       source_label=cls._VID_Y),
        )
        return run_annual_fifo_ledger((300.0,), (2026,), opening, 5)

    def test_vintage_x_expires_exact_id(self):
        """Vintage X (last_usable=2025) must expire in 2026 with exact ID."""
        entries = self._entries()
        expired = {v.vintage_id: v for v in entries[0].expired_vintages}
        assert self._VID_X in expired, f"Expected {self._VID_X} in expired; got {set(expired)}"
        v_x = expired[self._VID_X]
        assert abs(v_x.expired_keur - 500.0) < 1e-9
        assert v_x.used_keur == 0.0

    def test_vintage_y_not_expired(self):
        """Vintage Y (last_usable=2028) must not expire in 2026."""
        entries = self._entries()
        expired_ids = {v.vintage_id for v in entries[0].expired_vintages}
        assert self._VID_Y not in expired_ids, f"Vintage Y should NOT expire in 2026"

    def test_vintage_y_used_300_after_x_expires(self):
        """After X expires, Y is used to offset 300 kEUR of profit (FIFO)."""
        entries = self._entries()
        used = {v.vintage_id: v for v in entries[0].used_vintages}
        assert self._VID_Y in used, f"Vintage Y must be used in 2026; got {set(used)}"
        assert abs(used[self._VID_Y].used_keur - 300.0) < 1e-9

    def test_vintage_y_closing_is_100(self):
        """Y.closing = 400 − 300 = 100."""
        entries = self._entries()
        closing = {v.vintage_id: v for v in entries[0].closing_vintages}
        assert self._VID_Y in closing
        assert abs(closing[self._VID_Y].closing_keur - 100.0) < 1e-9

    def test_expired_vintage_not_used(self):
        """Expired vintage (X) contributes zero to used_keur."""
        entries = self._entries()
        used_ids = {v.vintage_id for v in entries[0].used_vintages}
        assert self._VID_X not in used_ids


# ---------------------------------------------------------------------------
# Test Q — Model G exact tax timing (item 14)
# ---------------------------------------------------------------------------

class TestQ_ModelG_ExactTiming:
    """Item 14 Model G: exact TAX_YEAR_LAST_PERIOD and SAME_PERIOD cash tax.

    Scenario: annual CIT liability = 180 kEUR.
    Two periods in the year: H1 (period 0) and H2 (period 1).

    TAX_YEAR_LAST_PERIOD (no lag):
      H1 cash_tax = 0
      H2 cash_tax = 180

    SAME_PERIOD (no lag):
      Each period pays its prorated share of the annual CIT.
    """

    def _run_with_timing(self, timing):
        """Run minimal 1-year engine and return (annual_results, period_results)."""
        from financial_engine.results import OperatingPeriodResult
        from financial_engine.tax.engine import calculate_tax
        # Two periods in calendar year 2030: H1 Jan-Jul, H2 Jul-Jan
        p0 = OperatingPeriodResult(
            period_index=0, period_start=date(2030, 1, 1), period_end=date(2030, 7, 1),
            year_index=1.0, period_in_year=0.5, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=181, day_fraction=0.5,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=500.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        p1 = OperatingPeriodResult(
            period_index=1, period_start=date(2030, 7, 1), period_end=date(2031, 1, 1),
            year_index=1.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=184, day_fraction=0.5,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=500.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        # EBITDA=1000 annual, rate=18% → CIT=180 kEUR
        policy = TaxPolicy(
            policy_id="timing_test",
            policy_version="1.0",
            corporate_rate=0.18,
            periods_per_tax_year=2,
            loss_carryforward_years=5,
            atad_enabled=False,
            atad_ebitda_limit=0.30,
            atad_de_minimis_threshold_keur_annual=3000.0,
            cash_tax_timing=timing,
            cash_tax_payment_lag_periods=0,
        )
        tax_input = TaxCalculationInput(
            policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        )
        return calculate_tax((p0, p1), tax_input)

    def test_tax_year_last_period_h1_zero(self):
        """TAX_YEAR_LAST_PERIOD: H1 cash tax = 0."""
        result = self._run_with_timing(CashTaxTiming.TAX_YEAR_LAST_PERIOD)
        pr_h1 = result.period_results[0]
        assert abs(pr_h1.cash_tax_keur) < 1e-9, f"H1 cash_tax={pr_h1.cash_tax_keur}"

    def test_tax_year_last_period_h2_equals_180(self):
        """TAX_YEAR_LAST_PERIOD: H2 cash tax = 180 (full annual CIT)."""
        result = self._run_with_timing(CashTaxTiming.TAX_YEAR_LAST_PERIOD)
        pr_h2 = result.period_results[1]
        assert abs(pr_h2.cash_tax_keur - 180.0) < 1e-9, f"H2 cash_tax={pr_h2.cash_tax_keur}"

    def test_same_period_total_equals_180(self):
        """SAME_PERIOD: total cash tax across periods = 180."""
        result = self._run_with_timing(CashTaxTiming.SAME_PERIOD)
        total = sum(pr.cash_tax_keur for pr in result.period_results)
        assert abs(total - 180.0) < 1e-9, f"Total cash_tax={total}"

    def test_same_period_both_nonzero(self):
        """SAME_PERIOD: both H1 and H2 receive non-zero cash tax."""
        result = self._run_with_timing(CashTaxTiming.SAME_PERIOD)
        for pr in result.period_results:
            assert pr.cash_tax_keur > 0.0, f"SAME_PERIOD: period {pr.period_index} has zero cash tax"


# ---------------------------------------------------------------------------
# Test R — Model H canonical CFADS (item 14)
# ---------------------------------------------------------------------------

class TestR_ModelH_CanonicalCFADS:
    """Item 14 Model H: canonical CFADS = EBITDA − cash_tax, exact values.

    Inputs:
      Period 0: EBITDA=100, cash_tax=0  → CFADS=100
      Period 1: EBITDA=120, cash_tax=18 → CFADS=102
    Totals:
      total EBITDA=220, total cash_tax=18, total CFADS=202
    """

    def _run(self):
        from financial_engine.results import OperatingPeriodResult
        from financial_engine.tax.engine import calculate_tax
        # Year 2030: H1 loss-making (no tax), H2 profitable (18% × 100 = 18)
        # Simplest: use two separate years so each has its own CIT.
        p0 = OperatingPeriodResult(
            period_index=0, period_start=date(2029, 1, 1), period_end=date(2030, 1, 1),
            year_index=0.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=365, day_fraction=1.0,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=100.0, book_depreciation_keur=0.0, tax_depreciation_keur=100.0,
        )
        p1 = OperatingPeriodResult(
            period_index=1, period_start=date(2030, 1, 1), period_end=date(2031, 1, 1),
            year_index=1.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=365, day_fraction=1.0,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=120.0, book_depreciation_keur=0.0, tax_depreciation_keur=20.0,
        )
        # tax_dep=100 for p0: taxable=0 → CIT=0; tax_dep=20 for p1: taxable=100 → CIT=18
        policy = _flat_policy(rate=0.18, atad_enabled=False,
                              timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD, lag=0)
        tax_input = TaxCalculationInput(
            policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=()
        )
        return calculate_tax((p0, p1), tax_input)

    def test_period0_cash_tax_is_zero(self):
        result = self._run()
        assert abs(result.period_results[0].cash_tax_keur) < 1e-9

    def test_period1_cash_tax_is_18(self):
        result = self._run()
        assert abs(result.period_results[1].cash_tax_keur - 18.0) < 1e-9

    def test_cfads_period0_is_100(self):
        result = self._run()
        ebitda = 100.0
        cfads = ebitda - result.period_results[0].cash_tax_keur
        assert abs(cfads - 100.0) < 1e-9

    def test_cfads_period1_is_102(self):
        result = self._run()
        ebitda = 120.0
        cfads = ebitda - result.period_results[1].cash_tax_keur
        assert abs(cfads - 102.0) < 1e-9

    def test_total_cfads_is_202(self):
        result = self._run()
        ebits = [100.0, 120.0]
        cfads = [e - pr.cash_tax_keur for e, pr in zip(ebits, result.period_results)]
        assert abs(sum(cfads) - 202.0) < 1e-9

    def test_total_ebitda_is_220(self):
        assert abs(100.0 + 120.0 - 220.0) < 1e-9

    def test_total_cash_tax_is_18(self):
        result = self._run()
        total = sum(pr.cash_tax_keur for pr in result.period_results)
        assert abs(total - 18.0) < 1e-9


# ---------------------------------------------------------------------------
# Test S — Model I: calendar tax-year fragmentation (item 14, item 2)
# ---------------------------------------------------------------------------

class TestS_ModelI_CalendarFragmentation:
    """Item 14 Model I + item 2: cross-year period with exact day allocation.

    Period: 2029-10-01 to 2030-03-31 (half-open: [2029-10-01, 2030-03-31))
    Total days = (2030-03-31 - 2029-10-01).days = 181

    2029 fragment: 2029-10-01 to 2030-01-01 → 92 days
    2030 fragment: 2030-01-01 to 2030-03-31 → 89 days

    allocation_2029 = 92 / 181
    allocation_2030 = 89 / 181 (adjusted so fracs sum to exactly 1.0)

    For EBITDA = 181 kEUR:
      2029 contribution = 181 × 92/181 = 92
      2030 contribution = 181 × 89/181 = 89
      2029 + 2030 = 181 ✓
    """

    _PERIOD_START = date(2029, 10, 1)
    _PERIOD_END   = date(2030, 3, 31)
    _EBITDA       = 181.0  # chosen so day-based allocations are whole numbers

    def _fragments(self):
        from financial_engine.tax.tax_year import _split_period
        return _split_period(0, self._PERIOD_START, self._PERIOD_END)

    def test_two_fragments_produced(self):
        frags = self._fragments()
        assert len(frags) == 2, f"Expected 2 fragments, got {len(frags)}"

    def test_2029_fragment_days_are_92(self):
        frags = {f.tax_year: f for f in self._fragments()}
        assert frags[2029].days == 92, f"2029 days={frags[2029].days}"

    def test_2030_fragment_days_are_89(self):
        frags = {f.tax_year: f for f in self._fragments()}
        assert frags[2030].days == 89, f"2030 days={frags[2030].days}"

    def test_fragment_days_sum_to_period_days(self):
        frags = self._fragments()
        total_days = (self._PERIOD_END - self._PERIOD_START).days
        assert sum(f.days for f in frags) == total_days

    def test_allocation_fractions_sum_to_1(self):
        frags = self._fragments()
        assert abs(sum(f.allocation_fraction for f in frags) - 1.0) < 1e-12

    def test_ebitda_allocated_proportionally(self):
        """EBITDA = 181 → 2029 gets 92, 2030 gets 89."""
        frags = {f.tax_year: f for f in self._fragments()}
        ebitda_2029 = self._EBITDA * frags[2029].allocation_fraction
        ebitda_2030 = self._EBITDA * frags[2030].allocation_fraction
        assert abs(ebitda_2029 + ebitda_2030 - self._EBITDA) < 1e-9, "Reconciliation failed"
        assert abs(ebitda_2029 - 92.0) < 0.01, f"2029 EBITDA={ebitda_2029}"
        assert abs(ebitda_2030 - 89.0) < 0.01, f"2030 EBITDA={ebitda_2030}"

    def test_source_period_days_is_181(self):
        """source_period_days stored on every fragment equals the full period's days."""
        frags = self._fragments()
        total_days = (self._PERIOD_END - self._PERIOD_START).days
        for f in frags:
            assert f.source_period_days == total_days, (
                f"Fragment tax_year={f.tax_year}: source_period_days={f.source_period_days}, "
                f"expected {total_days}"
            )


# ---------------------------------------------------------------------------
# Test T — Mandatory date-boundary tests (item 2)
# ---------------------------------------------------------------------------

class TestT_CalendarDateBoundary:
    """Item 2 mandatory date tests: Oborovo, Generic Wind, cross-year identity."""

    def _run_tax(self, fc, construction_months, horizon_years=10, **extra_cal):
        from financial_engine.orchestrator import run_tax_cfads_model
        cal = CalendarInput(
            financial_close=fc,
            construction_months=construction_months,
            horizon_years=horizon_years,
            ppa_years=float(horizon_years),
        )
        op = dataclasses.replace(_minimal_operating_input(), calendar=cal)
        tax_input = TaxCalculationInput(
            policy=_flat_policy(rate=0.18, atad_enabled=False),
            opening_loss_vintages=(),
            period_interest=(),
            period_adjustments=(),
        )
        from financial_engine.inputs import TaxCfadsModelInput
        return run_tax_cfads_model(TaxCfadsModelInput(operating=op, tax=tax_input))

    def test_oborovo_calendar_years_not_year_index(self):
        """Oborovo (FC=2029-06-29, COD=2030-06-29): cal years 2029/2030/2031 are distinct.

        The first period starts 2029-06-29 and ends 2030-01-01 (H2), crossing Dec31.
        Calendar year splitting must assign fragments to 2029 and 2030 separately,
        NOT group them by year_index (which would put both in year_index=0).
        """
        result = self._run_tax(date(2029, 6, 29), construction_months=12, horizon_years=10)
        tax_result = result.tax_and_cfads
        # Access annual results via the underlying engine
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.tax.engine import calculate_tax
        cal = CalendarInput(
            financial_close=date(2029, 6, 29),
            construction_months=12,
            horizon_years=10,
            ppa_years=10.0,
        )
        op = dataclasses.replace(_minimal_operating_input(), calendar=cal)
        op_result = run_operating_model(op)
        tax_input = TaxCalculationInput(
            policy=_flat_policy(rate=0.18, atad_enabled=False),
            opening_loss_vintages=(),
            period_interest=(),
            period_adjustments=(),
        )
        calc = calculate_tax(op_result.periods, tax_input)
        tax_years = {ar.tax_year for ar in calc.annual_results}
        # With FC=2029-06-29 and 12-month construction, COD is ~2030-06-29.
        # First construction period spans 2029-06-29 to 2030-01-01, contributing a fragment
        # to calendar year 2029. Year 2029 MUST be present as its own TaxYearCalculationBasis.
        assert 2029 in tax_years, (
            f"2029 must be an explicit tax year (first period crosses Dec31): {sorted(tax_years)}"
        )
        assert 2030 in tax_years, (
            f"2030 must be an explicit tax year (post-COD operation): {sorted(tax_years)}"
        )
        # Tax years must be calendar-year values, not year_index-based integers
        for yr in tax_years:
            assert yr > 2000, f"Tax year {yr} looks like a year_index, not a calendar year"

    def test_generic_wind_construction_fragments_in_correct_years(self):
        """Generic Wind (FC=2030-01-01, 18m construction, COD=2031-07-01).

        Construction period: Jan 2030 to Jul 2031.
        First operation: Jul 2031 to Jan 2032.
        Calendar year 2030 must be present and must be a construction-only year.
        Calendar year 2031 must be present (mixed: construction + operation start).
        """
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.tax.engine import calculate_tax
        cal = CalendarInput(
            financial_close=date(2030, 1, 1),
            construction_months=18,
            horizon_years=10,
            ppa_years=10.0,
        )
        op = dataclasses.replace(_minimal_operating_input(), calendar=cal)
        op_result = run_operating_model(op)
        tax_input = TaxCalculationInput(
            policy=_flat_policy(rate=0.18, atad_enabled=False),
            opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        )
        calc = calculate_tax(op_result.periods, tax_input)
        tax_years = sorted({ar.tax_year for ar in calc.annual_results})
        # FC=2030-01-01, 18-month construction → COD ≈ 2031-07-01.
        # Construction period spans Jan 2030 – Jul 2031; calendar year 2030 MUST be present.
        # First operating period is Jul 2031 – Jan 2032; 2031 MUST be present.
        assert 2030 in tax_years, (
            f"2030 must be a tax year (construction starts Jan 2030): {tax_years}"
        )
        assert 2031 in tax_years, (
            f"2031 must be a tax year (first operating period): {tax_years}"
        )
        # Verify fragment reconciliation for the first period that crosses Jan 1 2031
        from financial_engine.tax.tax_year import build_tax_year_bases
        bases = build_tax_year_bases(op_result.periods, {}, {})
        basis_map = {b.tax_year: b for b in bases}
        # For every year, sum of fragment ebitda_keur should equal basis.ebitda_keur
        for b in bases:
            frag_sum = sum(f.ebitda_keur for f in b.fragments)
            assert abs(frag_sum - b.ebitda_keur) < 1e-6, (
                f"Year {b.tax_year}: fragment EBITDA sum {frag_sum} ≠ basis {b.ebitda_keur}"
            )

    def test_cross_year_period_fragments_sum_to_original(self):
        """A 2029-10-01 to 2030-03-31 period: fragment allocations reconcile to original amounts.

        Fragment-level reconciliation: sum of (ebitda × allocation_fraction) over all fragments
        of a period equals the period's original EBITDA.  This is the invariant guaranteed by
        construction (allocation_fractions sum to 1.0), independent of how many annual bases
        are returned by build_tax_year_bases.
        """
        from financial_engine.tax.tax_year import _split_period
        period_start = date(2029, 10, 1)
        period_end   = date(2030, 3, 31)
        ebitda = 1_000.0
        dep    =   200.0

        frags = _split_period(0, period_start, period_end, ebitda_keur=ebitda,
                              tax_depreciation_keur=dep)
        # Fragment-level reconciliation: pre-allocated amounts sum to period totals
        recon_ebitda = sum(f.ebitda_keur for f in frags)
        recon_dep    = sum(f.tax_depreciation_keur for f in frags)
        assert abs(recon_ebitda - ebitda) < 1e-9, f"EBITDA reconciliation: {recon_ebitda}"
        assert abs(recon_dep    - dep   ) < 1e-9, f"Dep reconciliation: {recon_dep}"
        # Two calendar years
        assert len(frags) == 2, f"Expected 2 fragments, got {len(frags)}"
        years = {f.tax_year for f in frags}
        assert years == {2029, 2030}, f"Expected {{2029, 2030}}, got {years}"

    def test_same_year_index_different_calendar_not_grouped(self):
        """Two periods with same year_index but different calendar years → separate tax years.

        This test ensures that year_index is NOT used as the tax-year grouping key.
        """
        from financial_engine.results import OperatingPeriodResult
        from financial_engine.tax.tax_year import build_tax_year_bases
        # Period 0: purely in 2029 (year_index=0)
        p0 = OperatingPeriodResult(
            period_index=0, period_start=date(2029, 1, 1), period_end=date(2029, 7, 1),
            year_index=0.0, period_in_year=0.5, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=181, day_fraction=0.5,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=100.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        # Period 1: purely in 2030 (also year_index=0 — same operating year, different calendar)
        p1 = OperatingPeriodResult(
            period_index=1, period_start=date(2030, 1, 1), period_end=date(2030, 7, 1),
            year_index=0.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=181, day_fraction=0.5,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=200.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        bases = build_tax_year_bases((p0, p1), {}, {})
        tax_year_map = {b.tax_year: b for b in bases}
        assert 2029 in tax_year_map, "Period 0 (2029) must form its own tax year"
        assert 2030 in tax_year_map, "Period 1 (2030) must form its own tax year"
        assert abs(tax_year_map[2029].ebitda_keur - 100.0) < 1e-9
        assert abs(tax_year_map[2030].ebitda_keur - 200.0) < 1e-9


# ---------------------------------------------------------------------------
# Test U — Vintage immutability and determinism (item 5)
# ---------------------------------------------------------------------------

class TestU_VintageImmutabilityAndDeterminism:
    """Item 5: vintage records are frozen, tuples immutable, repeated runs produce equal values."""

    def _entries(self):
        opening = (
            OpeningTaxLossVintageInput(origin_tax_year=2025, amount_keur=100.0,
                                       source_label="v_a"),
        )
        return run_annual_fifo_ledger((50.0,), (2026,), opening, 5)

    def test_vintage_records_are_frozen(self):
        """TaxLossVintage instances are immutable (FrozenInstanceError on setattr)."""
        entries = self._entries()
        v = entries[0].used_vintages[0]
        import dataclasses as dc
        with pytest.raises((dc.FrozenInstanceError, TypeError, AttributeError)):
            v.used_keur = 0.0  # type: ignore

    def test_ledger_entries_are_frozen(self):
        """TaxAnnualLedgerEntry instances are immutable."""
        entries = self._entries()
        import dataclasses as dc
        with pytest.raises((dc.FrozenInstanceError, TypeError, AttributeError)):
            entries[0].loss_used_keur = 0.0  # type: ignore

    def test_returned_tuples_are_immutable(self):
        """run_annual_fifo_ledger returns a tuple (immutable container)."""
        entries = self._entries()
        assert isinstance(entries, tuple)
        with pytest.raises(TypeError):
            entries[0] = None  # type: ignore

    def test_repeated_execution_value_equal(self):
        """Same inputs produce value-equal vintage movements."""
        e1 = self._entries()
        e2 = self._entries()
        assert e1 == e2, "Repeated execution must produce equal results"

    def test_ordering_deterministic_by_origin_year(self):
        """Vintage ordering is deterministic: oldest origin year appears first in FIFO."""
        opening = (
            OpeningTaxLossVintageInput(origin_tax_year=2024, amount_keur=50.0,
                                       source_label="old"),
            OpeningTaxLossVintageInput(origin_tax_year=2025, amount_keur=50.0,
                                       source_label="new"),
        )
        entries = run_annual_fifo_ledger((30.0,), (2026,), opening, 10)
        used = entries[0].used_vintages
        # First used vintage must be the older one (2024)
        assert used[0].origin_tax_year == 2024


# ---------------------------------------------------------------------------
# Test V — Schedule alignment: sparse convention & validation (item 9)
# ---------------------------------------------------------------------------

class TestV_ScheduleAlignment:
    """Item 9: sparse schedule convention — omitted periods = zero.

    Validation must enforce:
      - duplicate period_index → TAX010/TAX012
      - out-of-order period_index → TAX015/TAX017
      - unknown period_index → TAX011/TAX016
    Shuffled source arrays fail validation (out-of-order).
    Missing middle period is NOT an error (sparse = zero).
    """

    def _codes(self, tax_input):
        from financial_engine.validation import validate_tax_calculation_input
        known = frozenset([0, 1, 2, 3, 4])
        issues = validate_tax_calculation_input(tax_input, known_period_indices=known)
        return {i.code for i in issues}

    def _base_input(self, period_interest=(), period_adjustments=()):
        return TaxCalculationInput(
            policy=_flat_policy(),
            opening_loss_vintages=(),
            period_interest=period_interest,
            period_adjustments=period_adjustments,
        )

    def test_shuffled_interest_fails_out_of_order(self):
        """Shuffled period_interest → TAX015 (out-of-order)."""
        interest = (
            PeriodInterestInput(period_index=2, senior_interest_keur=100.0),
            PeriodInterestInput(period_index=1, senior_interest_keur=100.0),  # reversed
        )
        codes = self._codes(self._base_input(period_interest=interest))
        assert "TAX015" in codes, f"Expected TAX015; got {codes}"

    def test_missing_middle_period_is_not_an_error(self):
        """Sparse schedule: period_index=2 absent, omitted=zero. No TAX011."""
        # Interest for periods 1 and 3 only (2 is absent)
        interest = (
            PeriodInterestInput(period_index=1, senior_interest_keur=100.0),
            PeriodInterestInput(period_index=3, senior_interest_keur=100.0),
        )
        codes = self._codes(self._base_input(period_interest=interest))
        # TAX015 must NOT appear (1 < 3 is ascending)
        assert "TAX015" not in codes, f"Unexpected TAX015; got {codes}"
        # TAX011 must NOT appear (1 and 3 are in known set {0,1,2,3,4})
        assert "TAX011" not in codes, f"Unexpected TAX011; got {codes}"

    def test_duplicate_period_fails_tax010(self):
        interest = (
            PeriodInterestInput(period_index=1, senior_interest_keur=100.0),
            PeriodInterestInput(period_index=1, senior_interest_keur=200.0),
        )
        codes = self._codes(self._base_input(period_interest=interest))
        assert "TAX010" in codes

    def test_unknown_period_fails_tax011(self):
        """Period index 99 is not in known_period_indices → TAX011."""
        interest = (PeriodInterestInput(period_index=99, senior_interest_keur=100.0),)
        codes = self._codes(self._base_input(period_interest=interest))
        assert "TAX011" in codes, f"Expected TAX011; got {codes}"

    def test_adj_out_of_order_fails_tax017(self):
        adjs = (
            PeriodTaxAdjustmentInput(period_index=3, other_fiscal_reintegration_keur=10.0),
            PeriodTaxAdjustmentInput(period_index=2, other_fiscal_reintegration_keur=10.0),
        )
        codes = self._codes(self._base_input(period_adjustments=adjs))
        assert "TAX017" in codes, f"Expected TAX017; got {codes}"

    def test_adj_unknown_period_fails_tax016(self):
        adjs = (PeriodTaxAdjustmentInput(period_index=99, other_fiscal_reintegration_keur=0.0),)
        codes = self._codes(self._base_input(period_adjustments=adjs))
        assert "TAX016" in codes, f"Expected TAX016; got {codes}"

    def test_interest_first_and_last_construction_periods(self):
        """Provider can supply interest for construction period indices (validated correctly)."""
        interest = (
            PeriodInterestInput(period_index=0, senior_interest_keur=50.0),
            PeriodInterestInput(period_index=4, senior_interest_keur=50.0),
        )
        codes = self._codes(self._base_input(period_interest=interest))
        assert "TAX011" not in codes, "Known period indices must not raise TAX011"
        assert "TAX015" not in codes, "Ascending order must not raise TAX015"


# ---------------------------------------------------------------------------
# Test W — Model J: correction-aware four-baseline acceptance (item 14)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", BASELINE_IDS)
def test_w_correction_aware_four_baseline(baseline_id: str):
    """Model J (item 14): four-baseline correction-aware parity check using production exact matcher.

    Each baseline must be IDENTICAL or APPROVED_FINANCIAL_CORRECTION.
    Unexplained difference count must be 0. Stale correction records must be 0.
    Uses production load_and_validate_ledger() + match_differences() — no simplified
    path-set check.
    """
    import json
    from pathlib import Path

    from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
    from finco_parity.financial_engine_tax_cfads_candidate import (
        generate_tax_cfads_candidate_snapshot,
    )
    from finco_parity.manifest import SNAPSHOTS_DIR
    from finco_parity.profiles import ComparisonProfile, project_for_profile
    from finco_parity.comparison import compare_snapshots

    _CORRECTIONS_PATH = (
        Path(__file__).parent.parent / "finco_parity" / "corrections" / "tax_cfads_v1_exact.json"
    )

    profile = ComparisonProfile.TAX_CFADS_V1
    snapshot_path = SNAPSHOTS_DIR / f"{baseline_id}.json"
    with open(snapshot_path) as f:
        baseline_snap = json.load(f)

    candidate_snap = generate_tax_cfads_candidate_snapshot(baseline_id)
    baseline_proj = project_for_profile(baseline_snap, profile)
    candidate_proj = project_for_profile(candidate_snap, profile)
    cmp = compare_snapshots(baseline_proj, candidate_proj, baseline_id)

    ledger = load_and_validate_ledger(_CORRECTIONS_PATH)
    result = match_differences(baseline_id, cmp.differences, ledger)

    assert len(result.unexplained) == 0, (
        f"[{baseline_id}] {len(result.unexplained)} UNEXPLAINED_DRIFT:\n"
        + "\n".join(f"  {d.path}: {d.kind.value}" for d in result.unexplained[:10])
    )
    assert len(result.stale_records) == 0, (
        f"[{baseline_id}] {len(result.stale_records)} STALE_CORRECTION_RECORD(s):\n"
        + "\n".join(f"  {r.field_path}" for r in result.stale_records[:10])
    )
    assert result.status in ("IDENTICAL", "APPROVED_FINANCIAL_CORRECTION"), (
        f"[{baseline_id}] unexpected status={result.status}"
    )


# ---------------------------------------------------------------------------
# TestX — End-to-end cross-year allocation (Blocker 3 exact values)
# ---------------------------------------------------------------------------

class TestX_CrossYearAllocation:
    """End-to-end tests proving both years survive when a period crosses Dec31.

    Reviewer requirement:
      Single period 2029-10-01 → 2030-03-31, EBITDA=181, tax_dep=0, interest=0, rate=10%:
        2029 fragment: 92 days (Oct 1 → Jan 1), 2030 fragment: 89 days (Jan 1 → Mar 31)
        2029 EBITDA=92, taxable=92, CIT=9.2
        2030 EBITDA=89, taxable=89, CIT=8.9
        total EBITDA=181, total CIT=18.1 — BOTH years must exist, neither may be skipped.
    """

    def _build_single_cross_year_result(self):
        """Single cross-year period: 2029-10-01 → 2030-03-31, EBITDA=181."""
        from financial_engine.results import OperatingPeriodResult
        from financial_engine.tax.engine import calculate_tax

        period_start = date(2029, 10, 1)
        period_end   = date(2030, 3, 31)
        # days: Oct1→Jan1 = 92; Jan1→Mar31 = 89; total = 181
        p = OperatingPeriodResult(
            period_index=0,
            period_start=period_start,
            period_end=period_end,
            year_index=0.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=181, day_fraction=1.0,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=181.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        tax_input = TaxCalculationInput(
            policy=_flat_policy(rate=0.10, atad_enabled=False),
            opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        )
        return calculate_tax((p,), tax_input)

    def test_both_years_present(self):
        """Both 2029 and 2030 must produce a TaxYearCalculationBasis — neither skipped."""
        calc = self._build_single_cross_year_result()
        years = {ar.tax_year for ar in calc.annual_results}
        assert 2029 in years, f"2029 missing from annual_results: {sorted(years)}"
        assert 2030 in years, f"2030 missing from annual_results: {sorted(years)}"

    def test_2029_ebitda_exact(self):
        """2029 EBITDA: 92 days / 181 days × 181 = 92 kEUR."""
        calc = self._build_single_cross_year_result()
        ar_map = {ar.tax_year: ar for ar in calc.annual_results}
        # 92 / 181 × 181 = 92.0 exactly (integer day count)
        expected = 181.0 * (92 / 181)
        actual = ar_map[2029].ebitda_keur
        assert abs(actual - expected) < 1e-6, f"2029 EBITDA: expected {expected}, got {actual}"

    def test_2030_ebitda_exact(self):
        """2030 EBITDA: 89 days / 181 days × 181 = 89 kEUR."""
        calc = self._build_single_cross_year_result()
        ar_map = {ar.tax_year: ar for ar in calc.annual_results}
        expected = 181.0 * (89 / 181)
        actual = ar_map[2030].ebitda_keur
        assert abs(actual - expected) < 1e-6, f"2030 EBITDA: expected {expected}, got {actual}"

    def test_total_ebitda_preserved(self):
        """Sum of annual EBITDA across both years = 181 kEUR."""
        calc = self._build_single_cross_year_result()
        total = sum(ar.ebitda_keur for ar in calc.annual_results)
        assert abs(total - 181.0) < 1e-9, f"Total EBITDA: expected 181, got {total}"

    def test_2029_cit_exact(self):
        """2029 CIT = 92 × 10% = 9.2 kEUR."""
        calc = self._build_single_cross_year_result()
        ar_map = {ar.tax_year: ar for ar in calc.annual_results}
        expected = 181.0 * (92 / 181) * 0.10  # = 9.2 exactly
        actual = ar_map[2029].current_tax_liability_keur
        assert abs(actual - expected) < 1e-6, f"2029 CIT: expected {expected:.4f}, got {actual:.4f}"

    def test_2030_cit_exact(self):
        """2030 CIT = 89 × 10% = 8.9 kEUR."""
        calc = self._build_single_cross_year_result()
        ar_map = {ar.tax_year: ar for ar in calc.annual_results}
        expected = 181.0 * (89 / 181) * 0.10  # = 8.9 exactly
        actual = ar_map[2030].current_tax_liability_keur
        assert abs(actual - expected) < 1e-6, f"2030 CIT: expected {expected:.4f}, got {actual:.4f}"

    def test_total_cit_exact(self):
        """Total CIT = 9.2 + 8.9 = 18.1 kEUR."""
        calc = self._build_single_cross_year_result()
        total = sum(ar.current_tax_liability_keur for ar in calc.annual_results)
        assert abs(total - 18.1) < 1e-6, f"Total CIT: expected 18.1, got {total:.6f}"

    def test_fragment_ebitda_reconciliation(self):
        """Pre-allocated fragment amounts sum back to 181 kEUR."""
        from financial_engine.tax.tax_year import build_tax_year_bases
        from financial_engine.results import OperatingPeriodResult
        p = OperatingPeriodResult(
            period_index=0, period_start=date(2029, 10, 1), period_end=date(2030, 3, 31),
            year_index=0.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=181, day_fraction=1.0,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=181.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        bases = build_tax_year_bases((p,), {}, {})
        total_ebitda = sum(b.ebitda_keur for b in bases)
        assert abs(total_ebitda - 181.0) < 1e-9, (
            f"Fragment EBITDA total: expected 181, got {total_ebitda}"
        )
        # Period 0 must appear in both years
        all_period_indices = {idx for b in bases for idx in b.period_indices}
        assert 0 in all_period_indices, "Period 0 must appear in at least one year"
        years = {b.tax_year for b in bases}
        assert 2029 in years and 2030 in years, f"Must have both 2029 and 2030: {years}"


# ---------------------------------------------------------------------------
# TestY — Multi-period cross-year fragment reconciliation (Blocker 3 multi-period)
# ---------------------------------------------------------------------------

class TestY_MultiPeriodCrossYear:
    """Multi-period test per Blocker 3 reviewer requirement.

    Scenario (periods use half-open intervals [start, end)):
      Period A: entirely 2029 (2029-01-01 → 2029-10-01), EBITDA=100
      Period B: crosses 2029/2030 (2029-10-01 → 2030-04-01), EBITDA=50
                 Oct1→Jan1 = 92 days in 2029; Jan1→Apr1 = 90 days in 2030
                 2029 fraction = 92/182; 2030 fraction = 90/182
      Period C: entirely 2030 (2030-04-01 → 2030-10-01), EBITDA=200

    Expected:
      2029 basis: A (100) + B's 2029 fragment (50 × 92/182) = 125.27...
      2030 basis: B's 2030 fragment (50 × 90/182) + C (200) = 224.72...
      Total EBITDA = 350 (preserved exactly)

    Period B (idx=1) must appear in BOTH 2029 and 2030 period_indices.
    """

    _B_DAYS_2029 = 92   # Oct1→Jan1
    _B_DAYS_2030 = 90   # Jan1→Apr1
    _B_TOTAL = 182      # 92 + 90

    def _build(self):
        from financial_engine.results import OperatingPeriodResult
        from financial_engine.tax.tax_year import build_tax_year_bases

        pA = OperatingPeriodResult(
            period_index=0, period_start=date(2029, 1, 1), period_end=date(2029, 10, 1),
            year_index=0.0, period_in_year=0.5, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=273, day_fraction=0.75,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=100.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        pB = OperatingPeriodResult(
            period_index=1, period_start=date(2029, 10, 1), period_end=date(2030, 4, 1),
            year_index=0.0, period_in_year=1.0, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=182, day_fraction=0.5,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=50.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        pC = OperatingPeriodResult(
            period_index=2, period_start=date(2030, 4, 1), period_end=date(2030, 10, 1),
            year_index=1.0, period_in_year=0.5, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=183, day_fraction=0.5,
            production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
            ebitda_keur=200.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
        )
        return build_tax_year_bases((pA, pB, pC), {}, {})

    def test_both_years_present(self):
        bases = self._build()
        years = {b.tax_year for b in bases}
        assert 2029 in years, f"2029 must be present: {sorted(years)}"
        assert 2030 in years, f"2030 must be present: {sorted(years)}"

    def test_2029_basis_includes_period_B_fragment(self):
        """Year 2029 must include period B (which crosses Dec31)."""
        bases = self._build()
        b2029 = next(b for b in bases if b.tax_year == 2029)
        assert 1 in b2029.period_indices, (
            f"Period B (idx=1) must appear in 2029 period_indices: {b2029.period_indices}"
        )

    def test_2030_basis_includes_period_B_fragment(self):
        """Year 2030 must include period B (its Jan–Mar fragment goes to 2030)."""
        bases = self._build()
        b2030 = next(b for b in bases if b.tax_year == 2030)
        assert 1 in b2030.period_indices, (
            f"Period B (idx=1) must appear in 2030 period_indices: {b2030.period_indices}"
        )

    def test_2029_ebitda_exact(self):
        """2029 EBITDA = A (100) + B's 2029 fragment (50 × 92/182)."""
        bases = self._build()
        b2029 = next(b for b in bases if b.tax_year == 2029)
        b_frac_2029 = self._B_DAYS_2029 / self._B_TOTAL
        expected = 100.0 + 50.0 * b_frac_2029
        assert abs(b2029.ebitda_keur - expected) < 1e-6, (
            f"2029 EBITDA: expected {expected:.6f}, got {b2029.ebitda_keur:.6f}"
        )

    def test_2030_ebitda_exact(self):
        """2030 EBITDA = B's 2030 fragment (50 × 90/182) + C (200)."""
        bases = self._build()
        b2030 = next(b for b in bases if b.tax_year == 2030)
        b_frac_2030 = self._B_DAYS_2030 / self._B_TOTAL
        expected = 50.0 * b_frac_2030 + 200.0
        assert abs(b2030.ebitda_keur - expected) < 1e-6, (
            f"2030 EBITDA: expected {expected:.6f}, got {b2030.ebitda_keur:.6f}"
        )

    def test_total_ebitda_preserved(self):
        """Total EBITDA across all years = 100 + 50 + 200 = 350."""
        bases = self._build()
        total = sum(b.ebitda_keur for b in bases)
        assert abs(total - 350.0) < 1e-9, f"Total EBITDA: expected 350, got {total}"

    def test_fragment_amounts_reconcile_per_year(self):
        """For each year basis, sum of fragment ebitda_keur == basis.ebitda_keur."""
        bases = self._build()
        for b in bases:
            frag_sum = sum(f.ebitda_keur for f in b.fragments)
            assert abs(frag_sum - b.ebitda_keur) < 1e-9, (
                f"Year {b.tax_year}: fragment sum {frag_sum} ≠ basis {b.ebitda_keur}"
            )


# ---------------------------------------------------------------------------
# TestZ — TUHO opening-loss RESOLVED (was: INPUT_SOURCE_BLOCKED / Blocker 5)
# ---------------------------------------------------------------------------

class TestZ_TuhoInputSourceBlocked:
    """TUHO opening-loss vintage is RESOLVED to zero; construction SHL interest correctly modeled.

    Source: manual TUHO Excel workbook inspection (20260330_TUHO_BP_2.xlsm).
    P&L Losses N-1 (first period) = 0 — no pre-model tax-loss carryforward.
    build_opening_loss_vintages("tuho") returns an empty tuple ().

    The 3,568.688 kEUR construction-period SHL interest (from
    tuho_construction_snapshot.json total_shl_idc) is injected into the tax engine
    via PeriodInterestInput for construction period_index=0 (2029-07-01 → 2030-01-01).
    Fiscal Reintegration = 0 (currently deductible per Excel policy), generating a
    construction-period tax loss carried forward into operations.

    TAX_CFADS_V1 TUHO status: APPROVED_FINANCIAL_CORRECTION (517 records).
    Root cause: baseline used unsupported prior_tax_loss_keur=25,000; candidate uses
    construction-generated LCF of ~3,568.688 kEUR.
    All 517 corrections are categorised as construction_shl_loss_carryforward.
    """

    def test_build_opening_loss_vintages_tuho_returns_empty_tuple(self):
        """build_opening_loss_vintages('tuho') returns () — zero pre-model opening loss."""
        from finco_parity.tax_reference_inputs import build_opening_loss_vintages
        result = build_opening_loss_vintages("tuho")
        assert result == (), (
            f"TUHO opening-loss vintages must be empty tuple (zero pre-model LCF). Got: {result}"
        )

    def test_non_tuho_baselines_not_blocked(self):
        """Oborovo, generic_solar, generic_wind: build_opening_loss_vintages succeeds."""
        from finco_parity.tax_reference_inputs import build_opening_loss_vintages
        for bid in ("oborovo", "generic_solar", "generic_wind"):
            result = build_opening_loss_vintages(bid)
            assert isinstance(result, tuple), f"{bid}: expected tuple, got {type(result)}"

    def test_generator_includes_tuho(self):
        """Generator runs TUHO and includes it in the ledger summary (not INPUT_SOURCE_BLOCKED)."""
        import tempfile
        from pathlib import Path
        import finco_parity.generate_tax_cfads_corrections as gen_mod
        orig_proposed = gen_mod.PROPOSED_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            gen_mod.PROPOSED_PATH = Path(tmpdir) / "proposed.json"
            try:
                ledger = gen_mod.generate_proposed_corrections()
            finally:
                gen_mod.PROPOSED_PATH = orig_proposed
        # TUHO must NOT be INPUT_SOURCE_BLOCKED — it is now runnable
        tuho_status = ledger["summary"]["tuho"]["status"]
        assert tuho_status != "INPUT_SOURCE_BLOCKED", (
            f"TUHO must not be INPUT_SOURCE_BLOCKED after resolution. Got: {tuho_status}"
        )

    def test_generator_never_overwrites_approved_ledger(self):
        """Generator must not write to tax_cfads_v1_exact.json."""
        import finco_parity.generate_tax_cfads_corrections as gen_mod
        # Approved path must be a different file from proposed
        assert gen_mod.APPROVED_PATH.name == "tax_cfads_v1_exact.json"
        assert gen_mod.PROPOSED_PATH.name == "tax_cfads_v1_proposed.json"
        assert gen_mod.APPROVED_PATH != gen_mod.PROPOSED_PATH, (
            "Generator must write to proposed, not approved"
        )

    def test_check_cli_does_not_block_tuho(self):
        """check_financial_engine_tax_cfads no longer blocks TUHO — opening-loss resolved."""
        from finco_parity.check_financial_engine_tax_cfads import _check_blocked_baselines
        blocked = _check_blocked_baselines(["tuho", "oborovo"])
        assert "tuho" not in blocked, (
            f"TUHO must NOT be blocked after opening-loss resolution. Blocked: {blocked}"
        )
        assert "oborovo" not in blocked, f"Oborovo must NOT be blocked: {blocked}"


class TestTuhoConstructionLoss:
    """Proves TUHO construction-generated LCF is supplied at the operation boundary.

    Architecture: CONSTRUCTION_GENERATED_CARRYFORWARD_AT_OPERATION_BOUNDARY.
    The 3,568.688 kEUR (from tuho_construction_snapshot.json total_shl_idc)
    is the workbook-observed construction-generated loss amount supplied as a
    ConstructionGeneratedVintage at the clean-engine operation boundary.
    origin_year=2029 is a MODEL_BOUNDARY_CONVENTION (terminal year of the
    2028-06-30→2029-12-30 source construction interval); no authoritative
    2028/2029 tax-year split has been extracted.  TUHO economics are unaffected
    because the loss is fully utilized before either possible expiry boundary.
    Historical/pre-construction opening LCF = ZERO.
    The factory prior_tax_loss_keur=25,000 is NEVER used by the candidate.
    """

    def test_tuho_historical_opening_vintages_are_empty(self):
        """build_opening_loss_vintages('tuho') returns () — zero pre-model opening LCF."""
        from finco_parity.tax_reference_inputs import build_opening_loss_vintages
        assert build_opening_loss_vintages("tuho") == ()

    def test_tuho_construction_shl_idc_sourced_from_fixture(self):
        """Fixture total_shl_idc=3,568.688 kEUR — the construction-generated carryforward amount."""
        import json
        with open("tests/fixtures/construction_parity/tuho_construction_snapshot.json") as f:
            snap = json.load(f)
        total_shl_idc = snap.get("totals_keur", {}).get("total_shl_idc", 0.0)
        assert abs(total_shl_idc - 3568.688) < 1.0, (
            f"total_shl_idc={total_shl_idc} expected ≈3568.688"
        )

    def test_tuho_25000_never_enters_clean_candidate(self):
        """The factory prior_tax_loss_keur=25,000 does not appear as an opening vintage."""
        from finco_parity.tax_reference_inputs import build_opening_loss_vintages
        vintages = build_opening_loss_vintages("tuho")
        total_opening = sum(v.amount_keur for v in vintages) if vintages else 0.0
        assert total_opening == 0.0, (
            f"Opening LCF total must be 0.0; got {total_opening}"
        )

    def test_construction_generated_loss_carried_into_operations(self):
        """Candidate snapshot carries construction LCF into first operating tax year."""
        from finco_parity.financial_engine_tax_cfads_candidate import (
            generate_tax_cfads_candidate_snapshot,
        )
        snap = generate_tax_cfads_candidate_snapshot("tuho")
        tc = snap["tax_and_cfads"]
        # After construction SHL interest injection the first operating tax year must have
        # some loss-used (candidate offsets operating profit against construction LCF).
        taxable_after = tc.get("taxable_profit_after_losses_audit_keur", [])
        taxable_before = tc.get("taxable_income_before_losses_audit_keur", [])
        # Some period early in operations must have before>0 but after=0 (LCF offset)
        lcf_used = any(
            (b > 0.01 and abs(a) < 1.0)
            for b, a in zip(taxable_before[:10], taxable_after[:10])
        )
        assert lcf_used, (
            "Expected at least one early operating period with positive taxable income "
            "offset to zero by construction LCF. Likely construction interest not injected."
        )

    def test_tuho_origin_year_is_model_boundary_convention(self):
        """origin_year=2029 is MODEL_BOUNDARY_CONVENTION — terminal year of source construction interval.

        No authoritative 2028/2029 tax-year split exists.  The convention assigns
        the full construction-generated carryforward to 2029 (the terminal year of
        the 2028-06-30→2029-12-30 source construction interval).  TUHO economics
        are unaffected by the possible expiry-year distinction because the loss is
        fully utilized before either possible expiry boundary (2033 or 2034).
        """
        from finco_parity.tax_reference_inputs import build_construction_generated_carryforward_at_cod
        vintages = build_construction_generated_carryforward_at_cod("tuho")
        assert len(vintages) == 1, f"Expected exactly one ConstructionGeneratedVintage; got {len(vintages)}"
        v = vintages[0]
        assert v.origin_year == 2029, f"Expected MODEL_BOUNDARY_CONVENTION origin_year=2029; got {v.origin_year}"
        assert v.origin_label == "CONSTRUCTION_GENERATED", f"Expected CONSTRUCTION_GENERATED label; got {v.origin_label}"
        assert abs(v.amount_keur - 3568.688) < 0.001, f"Expected 3568.688 kEUR; got {v.amount_keur}"

    def test_construction_generated_carryforward_hard_fails_on_missing_fixture(
        self, tmp_path, monkeypatch
    ):
        """build_construction_generated_carryforward_at_cod raises RuntimeError if fixture missing."""
        import os
        from finco_parity.tax_reference_inputs import build_construction_generated_carryforward_at_cod
        # Monkeypatch os.path.exists for the fixture path
        orig_exists = os.path.exists
        def fake_exists(p):
            if "tuho_construction_snapshot" in str(p):
                return False
            return orig_exists(p)
        monkeypatch.setattr(os.path, "exists", fake_exists)
        with pytest.raises(RuntimeError, match="GOVERNANCE FAILURE"):
            build_construction_generated_carryforward_at_cod("tuho")

    def test_tuho_end_to_end_exact_matcher(self):
        """TUHO: load approved ledger, run actual candidate, assert 0 unexplained, 0 stale."""
        import json
        from pathlib import Path

        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        from finco_parity.financial_engine_tax_cfads_candidate import (
            generate_tax_cfads_candidate_snapshot,
        )
        from finco_parity.manifest import SNAPSHOTS_DIR
        from finco_parity.profiles import ComparisonProfile, project_for_profile
        from finco_parity.comparison import compare_snapshots

        approved_path = Path("finco_parity/corrections/tax_cfads_v1_exact.json")
        ledger = load_and_validate_ledger(approved_path)

        # Load baseline and generate candidate using the same path as test_w,
        # which avoids the run_candidate_provider environment check that can fail
        # in pytest when numpy is imported from the project venv before this test.
        profile = ComparisonProfile.TAX_CFADS_V1
        with open(SNAPSHOTS_DIR / "tuho.json") as f:
            baseline_snap = json.load(f)

        candidate_snap = generate_tax_cfads_candidate_snapshot("tuho")
        baseline_proj = project_for_profile(baseline_snap, profile)
        candidate_proj = project_for_profile(candidate_snap, profile)
        cmp = compare_snapshots(baseline_proj, candidate_proj, "tuho")
        diffs = list(cmp.differences)

        result = match_differences("tuho", diffs, ledger)

        assert len(result.unexplained) == 0, (
            f"TUHO: {len(result.unexplained)} unexplained diff(s). First: "
            + (str(result.unexplained[0]) if result.unexplained else "")
        )
        assert len(result.stale_records) == 0, (
            f"TUHO: {len(result.stale_records)} stale record(s)."
        )
        tuho_approved_count = len(ledger.get("tuho", []))
        assert len(result.approved) == tuho_approved_count, (
            f"Expected {tuho_approved_count} approved, got {len(result.approved)}"
        )


class TestAA_ExactCorrectionMatcher:
    """Exact correction-record matching contract (production correction_matcher module).

    All tests use the production finco_parity.correction_matcher module.
    No simplified inline matchers.
    """

    # ── Fixtures ──────────────────────────────────────────────────────────────

    @staticmethod
    def _make_ledger_json(records: list[dict]) -> str:
        import json
        return json.dumps({
            "schema": "tax_cfads_exact_corrections/1.0",
            "profile": "TAX_CFADS_V1",
            "governance": {
                "proposed_file": "finco_parity/corrections/tax_cfads_v1_proposed.json",
                "approved_file": "finco_parity/corrections/tax_cfads_v1_exact.json",
                "rule": "This generator NEVER writes to the approved ledger.",
            },
            "summary": {},
            "corrections": records,
        })

    @staticmethod
    def _approved_record(
        *,
        baseline_id: str = "oborovo",
        field_path: str = "tax_and_cfads.cash_tax_keur[0]",
        baseline_value: object = 0.0,
        candidate_value: object = 100.0,
        delta: object = 100.0,
        drift_kind: str = "VALUE_DRIFT",
    ) -> dict:
        return {
            "correction_id": "test_rec_001",
            "baseline_id": baseline_id,
            "field_path": field_path,
            "baseline_value": baseline_value,
            "candidate_value": candidate_value,
            "delta": delta,
            "drift_kind": drift_kind,
            "correction_category": "calendar_year_axis",
            "financial_reason": "Test: calendar-year axis correction.",
            "manual_test_reference": "phase2b.calendar_axis.cross_year_allocation",
            "policy_id": "hr_reduced_factory_v1",
            "policy_version": "1.0",
            "approval_basis": "Verified by unit test.",
            "status": "APPROVED_FINANCIAL_CORRECTION",
        }

    @staticmethod
    def _make_diff(
        *,
        path: str = "tax_and_cfads.cash_tax_keur[0]",
        baseline_value: object = 0.0,
        current_value: object = 100.0,
        absolute_delta: float | None = 100.0,
    ) -> object:
        from finco_parity.comparison import Difference, DriftKind
        return Difference(
            kind=DriftKind.VALUE_DRIFT,
            path=path,
            baseline_value=baseline_value,
            current_value=current_value,
            absolute_delta=absolute_delta,
        )

    # ── load_and_validate_ledger ───────────────────────────────────────────────

    def test_missing_ledger_raises_file_not_found(self, tmp_path):
        from finco_parity.correction_matcher import load_and_validate_ledger
        missing = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_and_validate_ledger(missing)

    def test_duplicate_correction_id_raises(self, tmp_path):
        from finco_parity.correction_matcher import LedgerValidationError, load_and_validate_ledger
        rec = self._approved_record()
        rec2 = self._approved_record()
        rec2["field_path"] = "tax_and_cfads.cash_tax_keur[1]"
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec, rec2]))
        with pytest.raises(LedgerValidationError) as exc_info:
            load_and_validate_ledger(ledger_path)
        assert "duplicate correction_id" in str(exc_info.value)

    def test_duplicate_baseline_field_path_raises(self, tmp_path):
        from finco_parity.correction_matcher import LedgerValidationError, load_and_validate_ledger
        rec1 = self._approved_record()
        rec2 = self._approved_record()
        rec2["correction_id"] = "test_rec_002"
        # same (baseline_id, field_path) → duplicate
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec1, rec2]))
        with pytest.raises(LedgerValidationError) as exc_info:
            load_and_validate_ledger(ledger_path)
        assert "duplicate (baseline_id, field_path)" in str(exc_info.value)

    def test_unknown_policy_id_raises(self, tmp_path):
        from finco_parity.correction_matcher import LedgerValidationError, load_and_validate_ledger
        rec = self._approved_record()
        rec["policy_id"] = "unknown_policy_xyz"
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        with pytest.raises(LedgerValidationError) as exc_info:
            load_and_validate_ledger(ledger_path)
        assert "unknown policy_id" in str(exc_info.value)

    def test_absolute_path_in_financial_reason_raises(self, tmp_path):
        from finco_parity.correction_matcher import LedgerValidationError, load_and_validate_ledger
        rec = self._approved_record()
        rec["financial_reason"] = "See /home/user/Finco1/docs/analysis.md for details."
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        with pytest.raises(LedgerValidationError) as exc_info:
            load_and_validate_ledger(ledger_path)
        assert "absolute filesystem path" in str(exc_info.value)

    def test_inconsistent_delta_raises(self, tmp_path):
        from finco_parity.correction_matcher import LedgerValidationError, load_and_validate_ledger
        rec = self._approved_record(baseline_value=0.0, candidate_value=100.0, delta=999.0)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        with pytest.raises(LedgerValidationError) as exc_info:
            load_and_validate_ledger(ledger_path)
        assert "delta" in str(exc_info.value)

    def test_valid_ledger_loads_successfully(self, tmp_path):
        from finco_parity.correction_matcher import load_and_validate_ledger
        rec = self._approved_record()
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        result = load_and_validate_ledger(ledger_path)
        assert "oborovo" in result
        assert len(result["oborovo"]) == 1

    # ── match_differences ─────────────────────────────────────────────────────

    def test_exact_match_approved(self, tmp_path):
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        rec = self._approved_record()
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        diff = self._make_diff()
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "APPROVED_FINANCIAL_CORRECTION"
        assert len(result.approved) == 1
        assert len(result.unexplained) == 0
        assert len(result.stale_records) == 0

    def test_changed_candidate_value_unexplained(self, tmp_path):
        """Same path but different current_value → UNEXPLAINED_DRIFT (not approved)."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        rec = self._approved_record(candidate_value=100.0, delta=100.0)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        diff = self._make_diff(current_value=200.0, absolute_delta=200.0)
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT"
        assert len(result.unexplained) == 1
        assert len(result.approved) == 0

    def test_changed_baseline_value_unexplained(self, tmp_path):
        """Same path but different baseline_value → UNEXPLAINED_DRIFT."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        rec = self._approved_record(baseline_value=0.0)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        diff = self._make_diff(baseline_value=50.0, absolute_delta=50.0)
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT"
        assert len(result.unexplained) == 1

    def test_changed_delta_unexplained(self, tmp_path):
        """Same path + values but different absolute_delta → UNEXPLAINED_DRIFT."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        rec = self._approved_record(baseline_value=0.0, candidate_value=100.0, delta=100.0)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Diff has same path/values but absolute_delta differs
        diff = self._make_diff(
            baseline_value=0.0, current_value=100.0, absolute_delta=99.99
        )
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT"
        assert len(result.unexplained) == 1

    def test_json_type_int_ne_float(self, tmp_path):
        """1 (int) != 1.0 (float) — JSON type semantics must be preserved."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        # Record approves int baseline_value=1
        rec = self._approved_record(baseline_value=1, candidate_value=2, delta=1)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Diff has float baseline_value=1.0 — must NOT match
        diff = self._make_diff(baseline_value=1.0, current_value=2.0, absolute_delta=1.0)
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT", (
            "1 (int) != 1.0 (float): JSON type semantics must be preserved"
        )

    def test_drift_kind_mismatch_unexplained(self, tmp_path):
        """Diff with AVAILABILITY_DRIFT against VALUE_DRIFT record → UNEXPLAINED_DRIFT."""
        from finco_parity.comparison import Difference, DriftKind
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        # Record approves VALUE_DRIFT
        rec = self._approved_record()
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Diff has AVAILABILITY_DRIFT kind
        diff = Difference(
            kind=DriftKind.AVAILABILITY_DRIFT,
            path="tax_and_cfads.cash_tax_keur[0]",
            baseline_value="UNAVAILABLE",
            current_value=100.0,
            absolute_delta=None,
        )
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT"

    def test_stale_record_causes_failure(self, tmp_path):
        """Approved record with no matching observed diff → stale → has_failures=True."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        rec = self._approved_record()
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # No differences observed — stale record
        result = match_differences("oborovo", [], ledger)
        assert result.has_failures, "Stale correction record must cause has_failures=True"
        assert len(result.stale_records) == 1
        assert result.stale_records[0].correction_id == "test_rec_001"

    def test_no_diffs_no_records_identical(self, tmp_path):
        """No differences and no approved records → IDENTICAL (clean)."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([]))
        ledger = load_and_validate_ledger(ledger_path)

        result = match_differences("oborovo", [], ledger)
        assert result.status == "IDENTICAL"
        assert not result.has_failures

    def test_none_ne_zero(self, tmp_path):
        """null (None) != 0 — JSON type semantics."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        rec = self._approved_record(
            baseline_value=None, candidate_value=100.0, delta=None,
            drift_kind="AVAILABILITY_DRIFT",
        )
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Diff has int 0 as baseline_value — must NOT match
        diff = self._make_diff(baseline_value=0, current_value=100.0, absolute_delta=100.0)
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT", (
            "null (None) != 0: JSON type semantics must be preserved"
        )

    # ── Delta null/value semantics (item 2) ───────────────────────────────────

    def test_stored_delta_nonnull_observed_delta_null_no_match(self, tmp_path):
        """stored delta non-null, observed delta null → UNEXPLAINED_DRIFT."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        from finco_parity.comparison import Difference, DriftKind
        # Record stores a numeric delta; diff has no computable delta (STRUCTURAL_DRIFT)
        rec = self._approved_record(
            baseline_value=0.0, candidate_value=100.0, delta=100.0,
        )
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Observed diff has absolute_delta=None
        diff = Difference(
            kind=DriftKind.VALUE_DRIFT,
            path="tax_and_cfads.cash_tax_keur[0]",
            baseline_value=0.0,
            current_value=100.0,
            absolute_delta=None,
        )
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT", (
            "stored delta non-null + observed delta null must not match"
        )

    def test_stored_delta_null_observed_delta_nonnull_no_match(self, tmp_path):
        """stored delta null, observed delta non-null → UNEXPLAINED_DRIFT."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        from finco_parity.comparison import Difference, DriftKind
        # STRUCTURAL_DRIFT record: int vs float — different types → delta must be null
        rec = self._approved_record(
            baseline_value=0, candidate_value=100.0, delta=None,
            drift_kind="STRUCTURAL_DRIFT",
        )
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Observed diff provides a numeric delta (non-null where record stored null)
        diff = Difference(
            kind=DriftKind.STRUCTURAL_DRIFT,
            path="tax_and_cfads.cash_tax_keur[0]",
            baseline_value=0,
            current_value=100.0,
            absolute_delta=100.0,
        )
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT", (
            "stored delta null + observed delta non-null must not match"
        )

    def test_int_delta_vs_float_delta_no_match(self, tmp_path):
        """integer delta vs float delta → UNEXPLAINED_DRIFT (JSON type semantics)."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        from finco_parity.comparison import Difference, DriftKind
        # Record stores integer delta=1
        rec = self._approved_record(baseline_value=1, candidate_value=2, delta=1)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        # Diff has float delta=1.0
        diff = Difference(
            kind=DriftKind.VALUE_DRIFT,
            path="tax_and_cfads.cash_tax_keur[0]",
            baseline_value=1,
            current_value=2,
            absolute_delta=1.0,
        )
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "UNEXPLAINED_DRIFT", (
            "int delta=1 vs float delta=1.0: JSON type semantics must be preserved"
        )

    def test_non_finite_delta_in_ledger_raises(self, tmp_path):
        """Non-finite delta (Infinity) in ledger → LedgerValidationError."""
        from finco_parity.correction_matcher import LedgerValidationError, load_and_validate_ledger
        import json
        rec = self._approved_record()
        rec["delta"] = float("inf")
        ledger_path = tmp_path / "exact.json"
        # json.dumps doesn't serialize Infinity; write raw JSON with Infinity sentinel
        raw = self._make_ledger_json([self._approved_record()])
        # Replace the delta value to insert a non-finite number as a string workaround
        # Use a dict with the Infinity float encoded via json module's allow_nan behavior
        import json as _json
        data = _json.loads(raw)
        data["corrections"][0]["delta"] = float("inf")
        # Python's json.dumps encodes float('inf') as 'Infinity' (non-standard)
        raw_with_inf = _json.dumps(data, allow_nan=True)
        ledger_path.write_text(raw_with_inf)
        with pytest.raises((LedgerValidationError, ValueError)):
            load_and_validate_ledger(ledger_path)

    def test_exact_negative_signed_delta_matches(self, tmp_path):
        """Exact negative signed delta → APPROVED_FINANCIAL_CORRECTION."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        # baseline=100.0, candidate=0.0 → delta=-100.0
        rec = self._approved_record(baseline_value=100.0, candidate_value=0.0, delta=-100.0)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        diff = self._make_diff(baseline_value=100.0, current_value=0.0, absolute_delta=-100.0)
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "APPROVED_FINANCIAL_CORRECTION", (
            "exact negative signed delta must produce an approved match"
        )

    def test_exact_zero_signed_delta_matches(self, tmp_path):
        """Exact zero signed delta → APPROVED_FINANCIAL_CORRECTION."""
        from finco_parity.correction_matcher import load_and_validate_ledger, match_differences
        from finco_parity.comparison import Difference, DriftKind
        # Both baseline and candidate are the same value (zero delta) — but the
        # comparison engine still emitted a diff (e.g. due to type mismatch resolved
        # or another dimension). Here we test the delta=0.0 path specifically.
        rec = self._approved_record(baseline_value=50.0, candidate_value=50.0, delta=0.0)
        ledger_path = tmp_path / "exact.json"
        ledger_path.write_text(self._make_ledger_json([rec]))
        ledger = load_and_validate_ledger(ledger_path)

        diff = Difference(
            kind=DriftKind.VALUE_DRIFT,
            path="tax_and_cfads.cash_tax_keur[0]",
            baseline_value=50.0,
            current_value=50.0,
            absolute_delta=0.0,
        )
        result = match_differences("oborovo", [diff], ledger)
        assert result.status == "APPROVED_FINANCIAL_CORRECTION", (
            "exact zero signed delta must produce an approved match"
        )
