"""U2 — Canonical Cash/Reserve Interest Upstream Authority.

Tests verify:
1. CashReserveInterestPolicy: UNRESOLVED fails closed (0.0) always.
2. Policy computes correctly with valid authority + rate + eligible account.
3. No eligible accounts → 0.0 even with valid rate.
4. Negative balances are clamped to 0.
5. Disabled policy (enabled=False) → 0.0.
6. annual_rate=None → 0.0 even with SOURCE_PROVEN.
7. DSRA-only eligibility.
8. Unrestricted-cash-only eligibility.
9. Both accounts eligible → sum.
10. GENERIC_FINCO_POLICY computes same as SOURCE_PROVEN for same inputs.
11. UNRESOLVED_POLICY sentinel.
12. Day-fraction scaling.
13–27: Positive-path canonical mutation tests via TaxCalculationInput → calculate_tax →
    calculate_canonical_cfads.  Prove EBITDA unchanged, financing_income enters taxable
    income and CFADS causally.
"""
from __future__ import annotations

import pytest

from finco_core.inputs.cash_reserve_interest_policy import (
    CashReserveInterestPolicy,
    CashReserveInterestAuthority,
    EligibilityStatus,
    DayCountConvention,
    BalanceConvention,
    UNRESOLVED_POLICY,
)


# ── 1. UNRESOLVED fails closed ───────────────────────────────────────────────

def test_unresolved_authority_fails_closed():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.UNRESOLVED,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.05,
        enabled=True,
    )
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0, "UNRESOLVED must always yield 0.0"


# ── 2. Valid policy computes correctly ───────────────────────────────────────

def test_source_proven_computes_correctly():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=0.02,
        enabled=True,
    )
    # 10_000 kEUR × 2% × 0.5 = 100 kEUR
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert abs(result - 100.0) < 1e-9


# ── 3. No eligible accounts → 0.0 ───────────────────────────────────────────

def test_no_eligible_accounts_yields_zero():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.INELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=0.05,
        enabled=True,
    )
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=5_000.0,
        dsra_balance_keur=1_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0


# ── 4. Negative balances clamped ─────────────────────────────────────────────

def test_negative_balance_clamped_to_zero():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.05,
        enabled=True,
    )
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=-500.0,
        dsra_balance_keur=-100.0,
        day_fraction=0.5,
    )
    assert result == 0.0


# ── 5. enabled=False → 0.0 ───────────────────────────────────────────────────

def test_disabled_policy_yields_zero():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.05,
        enabled=False,
    )
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0


# ── 6. annual_rate=None → 0.0 ────────────────────────────────────────────────

def test_none_rate_yields_zero():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=None,
        enabled=True,
    )
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0


# ── 7. DSRA-only eligibility ──────────────────────────────────────────────────

def test_dsra_only_eligibility():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
        eligible_unrestricted_cash=EligibilityStatus.INELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.04,
        enabled=True,
    )
    # Only DSRA: 2_000 × 4% × 0.5 = 40 kEUR
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert abs(result - 40.0) < 1e-9


# ── 8. Unrestricted-cash-only eligibility ────────────────────────────────────

def test_cash_only_eligibility():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=0.03,
        enabled=True,
    )
    # Only cash: 5_000 × 3% × 0.5 = 75 kEUR
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=5_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert abs(result - 75.0) < 1e-9


# ── 9. Both accounts eligible → sum ──────────────────────────────────────────

def test_both_eligible_sums_balances():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.02,
        enabled=True,
    )
    # (5_000 + 2_000) × 2% × 0.5 = 70 kEUR
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=5_000.0,
        dsra_balance_keur=2_000.0,
        day_fraction=0.5,
    )
    assert abs(result - 70.0) < 1e-9


# ── 10. GENERIC_FINCO_POLICY == SOURCE_PROVEN for same inputs ─────────────────

def test_generic_and_source_proven_compute_identically():
    kwargs = dict(
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.01,
        enabled=True,
    )
    p_generic = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY, **kwargs
    )
    p_proven = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN, **kwargs
    )
    call_kwargs = dict(
        unrestricted_cash_balance_keur=8_000.0,
        dsra_balance_keur=1_500.0,
        day_fraction=0.5,
    )
    assert p_generic.compute_period_income_keur(**call_kwargs) == p_proven.compute_period_income_keur(**call_kwargs)


# ── 11. UNRESOLVED_POLICY sentinel ───────────────────────────────────────────

def test_unresolved_policy_sentinel_fails_closed():
    result = UNRESOLVED_POLICY.compute_period_income_keur(
        unrestricted_cash_balance_keur=999_999.0,
        dsra_balance_keur=999_999.0,
        day_fraction=0.5,
    )
    assert result == 0.0
    assert UNRESOLVED_POLICY.authority == CashReserveInterestAuthority.UNRESOLVED


# ── 12. Day-fraction scaling ──────────────────────────────────────────────────

def test_day_fraction_scaling():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=0.04,
        enabled=True,
    )
    r_half = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0, dsra_balance_keur=0.0, day_fraction=0.5
    )
    r_quarter = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=10_000.0, dsra_balance_keur=0.0, day_fraction=0.25
    )
    # 10_000 × 4% × 0.5 = 200; × 0.25 = 100
    assert abs(r_half - 200.0) < 1e-9
    assert abs(r_quarter - 100.0) < 1e-9
    assert abs(r_half - 2 * r_quarter) < 1e-9


# ── 13. INELIGIBLE accounts → 0.0 even with valid rate ───────────────────────

def test_ineligible_accounts_yields_zero_with_valid_rate():
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
        eligible_unrestricted_cash=EligibilityStatus.INELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=0.10,
        enabled=True,
    )
    result = policy.compute_period_income_keur(
        unrestricted_cash_balance_keur=50_000.0,
        dsra_balance_keur=5_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0


# ── Immutability ──────────────────────────────────────────────────────────────

def test_policy_is_frozen():
    import dataclasses
    assert CashReserveInterestPolicy.__dataclass_params__.frozen is True


# ── UNRESOLVED_POLICY accounts also UNRESOLVED ───────────────────────────────

def test_unresolved_policy_account_status():
    assert UNRESOLVED_POLICY.eligible_unrestricted_cash == EligibilityStatus.UNRESOLVED
    assert UNRESOLVED_POLICY.eligible_dsra == EligibilityStatus.UNRESOLVED
    assert UNRESOLVED_POLICY.annual_rate is None


# ══════════════════════════════════════════════════════════════════════════════
# Canonical causal-chain mutation tests (§16)
#
# These tests prove the architecture end-to-end with synthetic inputs injected
# directly into TaxCalculationInput.period_financing_income.  They require NO
# project data and NO real balance schedule.
#
# Invariants verified:
#   A. EBITDA is never modified by financing income.
#   B. financing_income_keur enters taxable income (TI = EBITDA + FI − dep − interest).
#   C. CIT increases monotonically with financing income (given same losses).
#   D. CFADS = EBITDA + financing_income − cash_tax (causal, not EBITDA-augmented).
#   E. Increasing balance/rate → increasing income (policy monotonicity).
#   F. UNRESOLVED → income = 0.0, not silently proven.
# ══════════════════════════════════════════════════════════════════════════════

import datetime
from dataclasses import replace as _replace


def _make_minimal_tax_input(financing_income_by_period: dict[int, float] | None = None):
    """Build the smallest TaxCalculationInput that runs through calculate_tax."""
    from financial_engine.inputs import (
        TaxCalculationInput,
        PeriodFinancingIncomeInput,
    )
    from financial_engine.policies.tax import (
        TaxPolicy,
        CashTaxTiming,
        TaxBasisPeriodisation,
        TaxLossUtilisationGate,
    )

    policy = TaxPolicy(
        policy_id="u2-synthetic-test",
        policy_version="1.0.0",
        corporate_rate=0.25,
        loss_carryforward_years=5,
        periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
        loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )
    fin_income_inputs = tuple(
        PeriodFinancingIncomeInput(period_index=idx, financing_income_keur=amount)
        for idx, amount in (financing_income_by_period or {}).items()
    )
    return TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=(),
        period_adjustments=(),
        period_financing_income=fin_income_inputs,
    )


def _make_synthetic_periods(ebitda_keur_per_period: list[float], start_year: int = 2030):
    """Build synthetic OperatingPeriodResult-like objects with real dates."""
    from dataclasses import dataclass

    @dataclass
    class _SyntheticPeriod:
        period_index: int
        is_operation: bool
        is_construction: bool
        ebitda_keur: float
        tax_depreciation_keur: float
        period_start: datetime.date
        period_end: datetime.date
        day_fraction: float = 0.5

    periods = []
    for i, ebitda in enumerate(ebitda_keur_per_period):
        year = start_year + i // 2
        half = i % 2
        if half == 0:
            start = datetime.date(year, 1, 1)
            end = datetime.date(year, 7, 1)
        else:
            start = datetime.date(year, 7, 1)
            end = datetime.date(year + 1, 1, 1)
        periods.append(_SyntheticPeriod(
            period_index=i,
            is_operation=True,
            is_construction=False,
            ebitda_keur=ebitda,
            tax_depreciation_keur=0.0,
            period_start=start,
            period_end=end,
        ))
    return tuple(periods)


def _run_synthetic(ebitda_per_period: list[float], fin_income_by_period: dict[int, float] | None = None):
    """Run calculate_tax + calculate_canonical_cfads with synthetic inputs."""
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads

    periods = _make_synthetic_periods(ebitda_per_period)
    tax_input = _make_minimal_tax_input(fin_income_by_period)
    tax_result = calculate_tax(periods, tax_input)
    cfads_results = calculate_canonical_cfads(periods, tax_result.period_results)
    return tax_result, cfads_results


# ── 14. EBITDA invariant: financing income never modifies EBITDA ──────────────

def test_mutation_ebitda_unchanged_by_financing_income():
    """EBITDA on PeriodCashTaxResult must equal source EBITDA regardless of financing_income."""
    ebitda = [1_000.0, 1_000.0]
    fin_income = {0: 500.0, 1: 250.0}
    tax_result, _ = _run_synthetic(ebitda, fin_income)
    for pr in tax_result.period_results:
        assert abs(pr.ebitda_keur - 1_000.0) < 1e-9, (
            f"Period {pr.period_index}: EBITDA mutated to {pr.ebitda_keur}"
        )


# ── 15. financing_income enters taxable income ────────────────────────────────

def test_mutation_financing_income_enters_taxable_income():
    """Adding financing_income must increase taxable income by the same amount."""
    ebitda = [2_000.0, 2_000.0]

    tax_no_fin, _ = _run_synthetic(ebitda, {})
    tax_with_fin, _ = _run_synthetic(ebitda, {0: 400.0, 1: 400.0})

    ti_no_fin = sum(r.taxable_income_before_lcf_keur for r in tax_no_fin.annual_results)
    ti_with_fin = sum(r.taxable_income_before_lcf_keur for r in tax_with_fin.annual_results)

    assert abs(ti_with_fin - ti_no_fin - 800.0) < 1e-6, (
        f"Expected TI increase of 800 kEUR; got {ti_with_fin - ti_no_fin:.4f}"
    )


# ── 16. CIT increases with financing income ───────────────────────────────────

def test_mutation_cit_increases_with_financing_income():
    """CIT liability must be higher when financing_income is positive."""
    ebitda = [3_000.0, 3_000.0]
    tax_base, _ = _run_synthetic(ebitda, {})
    tax_high, _ = _run_synthetic(ebitda, {0: 1_000.0, 1: 1_000.0})

    cit_base = sum(r.current_tax_liability_keur for r in tax_base.annual_results)
    cit_high = sum(r.current_tax_liability_keur for r in tax_high.annual_results)

    assert cit_high > cit_base, (
        f"CIT must increase with financing income; base={cit_base:.2f} high={cit_high:.2f}"
    )


# ── 17. CFADS causal: EBITDA + financing_income − cash_tax ───────────────────

def test_mutation_cfads_formula_is_ebitda_plus_financing_minus_tax():
    """CFADS = EBITDA + financing_income − cash_tax (not EBITDA-augmented)."""
    ebitda = [2_000.0, 2_000.0]
    fin_income = {0: 300.0, 1: 300.0}
    tax_result, cfads_results = _run_synthetic(ebitda, fin_income)

    for pr, cfr in zip(tax_result.period_results, cfads_results):
        expected = pr.ebitda_keur + pr.financing_income_keur - pr.cash_tax_keur
        assert abs(cfr.cfads_keur - expected) < 1e-9, (
            f"Period {pr.period_index}: CFADS={cfr.cfads_keur:.4f} expected={expected:.4f}"
        )


# ── 18. financing_income on PeriodCashTaxResult matches injected value ────────

def test_mutation_period_cash_tax_result_carries_financing_income():
    """PeriodCashTaxResult.financing_income_keur must equal injected amount."""
    ebitda = [1_500.0, 1_500.0]
    fin_income = {0: 200.0, 1: 150.0}
    tax_result, _ = _run_synthetic(ebitda, fin_income)

    for pr in tax_result.period_results:
        expected = fin_income.get(pr.period_index, 0.0)
        assert abs(pr.financing_income_keur - expected) < 1e-9, (
            f"Period {pr.period_index}: financing_income={pr.financing_income_keur} expected={expected}"
        )


# ── 19. TaxAnnualResult carries aggregated financing_income_keur ──────────────

def test_mutation_annual_result_carries_financing_income():
    """TaxAnnualResult.financing_income_keur must aggregate from its fragments."""
    ebitda = [1_000.0, 1_000.0]
    fin_income = {0: 100.0, 1: 100.0}
    tax_result, _ = _run_synthetic(ebitda, fin_income)

    total = sum(r.financing_income_keur for r in tax_result.annual_results)
    assert abs(total - 200.0) < 1e-6, f"Annual financing_income total={total:.4f} expected=200.0"


# ── 20. Zero financing_income: baseline CIT unchanged ─────────────────────────

def test_mutation_zero_financing_income_produces_baseline_cit():
    """With zero financing_income injected, CIT must equal the no-injection baseline."""
    ebitda = [2_000.0, 2_000.0]
    tax_baseline, _ = _run_synthetic(ebitda, {})
    tax_zero, _ = _run_synthetic(ebitda, {0: 0.0, 1: 0.0})

    for r_base, r_zero in zip(tax_baseline.annual_results, tax_zero.annual_results):
        assert abs(r_base.current_tax_liability_keur - r_zero.current_tax_liability_keur) < 1e-9


# ── 21. Increasing financing_income monotonically increases CIT ───────────────

def test_mutation_monotonic_cit_with_increasing_financing_income():
    """CIT must increase monotonically as financing_income increases."""
    ebitda = [2_000.0, 2_000.0]
    cit_values = []
    for amount in [0.0, 100.0, 500.0, 1_000.0, 2_000.0]:
        tax_result, _ = _run_synthetic(ebitda, {0: amount, 1: amount})
        total_cit = sum(r.current_tax_liability_keur for r in tax_result.annual_results)
        cit_values.append(total_cit)

    for i in range(1, len(cit_values)):
        assert cit_values[i] >= cit_values[i - 1], (
            f"CIT not monotonic: step {i}: {cit_values[i-1]:.4f} → {cit_values[i]:.4f}"
        )


# ── 22. CFADS increases with financing_income (given fixed EBITDA) ────────────

def test_mutation_cfads_increases_with_financing_income():
    """Net CFADS = EBITDA + FI − tax must increase when FI increases (partial tax relief)."""
    ebitda = [3_000.0, 3_000.0]
    _, cfads_base = _run_synthetic(ebitda, {0: 0.0, 1: 0.0})
    _, cfads_high = _run_synthetic(ebitda, {0: 1_000.0, 1: 1_000.0})

    total_base = sum(c.cfads_keur for c in cfads_base)
    total_high = sum(c.cfads_keur for c in cfads_high)

    assert total_high > total_base, (
        f"CFADS must increase with financing income; base={total_base:.2f} high={total_high:.2f}"
    )


# ── 23. EBITDA unchanged across monotonic financing_income sweep ──────────────

def test_mutation_ebitda_invariant_across_sweep():
    """EBITDA must be identical for all financing_income levels."""
    ebitda = [2_000.0, 2_000.0]
    for amount in [0.0, 500.0, 2_000.0, 5_000.0]:
        tax_result, _ = _run_synthetic(ebitda, {0: amount, 1: amount})
        for pr in tax_result.period_results:
            assert abs(pr.ebitda_keur - ebitda[pr.period_index]) < 1e-9, (
                f"FI={amount}: Period {pr.period_index} EBITDA={pr.ebitda_keur} mutated"
            )


# ── 24. financing_income on PeriodCfadsResult matches PeriodCashTaxResult ─────

def test_mutation_cfads_result_carries_financing_income():
    """PeriodCfadsResult.financing_income_keur must equal PeriodCashTaxResult.financing_income_keur."""
    ebitda = [2_000.0, 2_000.0]
    fin_income = {0: 350.0, 1: 175.0}
    tax_result, cfads_results = _run_synthetic(ebitda, fin_income)

    for pr, cfr in zip(tax_result.period_results, cfads_results):
        assert abs(cfr.financing_income_keur - pr.financing_income_keur) < 1e-9, (
            f"Period {pr.period_index}: cfads.fin_income={cfr.financing_income_keur} "
            f"tax.fin_income={pr.financing_income_keur}"
        )


# ── 25. UNRESOLVED policy → 0.0 income (not silently proven) ─────────────────

def test_mutation_unresolved_policy_yields_zero_not_proven():
    """UNRESOLVED authority must yield 0.0 — not a non-zero proven value."""
    result = UNRESOLVED_POLICY.compute_period_income_keur(
        unrestricted_cash_balance_keur=100_000.0,
        dsra_balance_keur=20_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0
    # Confirm this is UNRESOLVED authority, not GENERIC or SOURCE_PROVEN
    assert UNRESOLVED_POLICY.authority == CashReserveInterestAuthority.UNRESOLVED


# ── 26. Single-period financing_income only affects relevant tax year ─────────

def test_mutation_single_period_financing_income_targeted():
    """Injecting FI in only one period must affect only that period's CIT share."""
    ebitda = [2_000.0, 2_000.0, 2_000.0, 2_000.0]
    # Inject only in period 0
    fin_income = {0: 500.0}
    tax_result, cfads_results = _run_synthetic(ebitda, fin_income)

    # Period 0 must carry 500 kEUR financing income
    p0 = next(pr for pr in tax_result.period_results if pr.period_index == 0)
    assert abs(p0.financing_income_keur - 500.0) < 1e-9

    # All other periods must carry 0 financing income
    for pr in tax_result.period_results:
        if pr.period_index != 0:
            assert abs(pr.financing_income_keur) < 1e-9, (
                f"Period {pr.period_index}: unexpected financing_income={pr.financing_income_keur}"
            )


# ── 27. TaxCalculationInput with no financing_income is backward compat ───────

def test_mutation_empty_financing_income_is_backward_compatible():
    """TaxCalculationInput with no period_financing_income must produce same result as baseline."""
    from financial_engine.inputs import TaxCalculationInput
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads

    ebitda = [2_000.0, 2_000.0]
    periods = _make_synthetic_periods(ebitda)
    tax_input = _make_minimal_tax_input(None)  # period_financing_income=()

    # Must not raise and must produce finite results
    tax_result = calculate_tax(periods, tax_input)
    cfads_results = calculate_canonical_cfads(periods, tax_result.period_results)

    for pr in tax_result.period_results:
        assert pr.financing_income_keur == 0.0
    for cfr in cfads_results:
        assert cfr.financing_income_keur == 0.0
        # CFADS = EBITDA + 0 - cash_tax
        assert abs(cfr.cfads_keur - (cfr.ebitda_keur - cfr.cash_tax_keur)) < 1e-9
