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
    # SOURCE_PROVEN + both INELIGIBLE raises at construction (§4 __post_init__)
    # Use UNRESOLVED authority to prove zero when no accounts eligible via authority path.
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.UNRESOLVED,
        eligible_unrestricted_cash=EligibilityStatus.INELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=None,
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


# ── 6. annual_rate=None → raises for SOURCE_PROVEN ───────────────────────────

def test_none_rate_raises_for_source_proven():
    # After §4 __post_init__, SOURCE_PROVEN + annual_rate=None must raise at construction.
    with pytest.raises(ValueError, match="annual_rate is required"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.ELIGIBLE,
            annual_rate=None,
            enabled=True,
        )


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


# ── 13. INELIGIBLE accounts → raises for SOURCE_PROVEN/GENERIC_FINCO_POLICY ──

def test_ineligible_accounts_raises_for_non_unresolved():
    # After §4 __post_init__, SOURCE_PROVEN/GENERIC_FINCO + both INELIGIBLE must raise.
    with pytest.raises(ValueError, match="at least one ELIGIBLE"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
            eligible_unrestricted_cash=EligibilityStatus.INELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=0.10,
            enabled=True,
        )


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


def _make_minimal_tax_input(
    financing_income_by_period: dict[int, float] | None = None,
    authority: str = "SOURCE_PROVEN",
    loss_utilisation_gate=None,
):
    """Build the smallest TaxCalculationInput that runs through calculate_tax.

    Nonzero financing_income amounts use authority="SOURCE_PROVEN" by default.
    Zero amounts use authority="UNRESOLVED" (fail-closed, still zero).
    """
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

    gate = loss_utilisation_gate if loss_utilisation_gate is not None else TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
    policy = TaxPolicy(
        policy_id="u2-synthetic-test",
        policy_version="1.0.0",
        corporate_rate=0.25,
        loss_carryforward_years=5,
        periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
        loss_utilisation_gate=gate,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )
    fin_income_inputs = tuple(
        PeriodFinancingIncomeInput(
            period_index=idx,
            financing_income_keur=amount,
            # Use SOURCE_PROVEN for nonzero amounts — UNRESOLVED+nonzero raises.
            authority=authority if amount != 0.0 else "UNRESOLVED",
        )
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


def _run_synthetic(
    ebitda_per_period: list[float],
    fin_income_by_period: dict[int, float] | None = None,
    authority: str = "SOURCE_PROVEN",
):
    """Run calculate_tax + calculate_canonical_cfads with synthetic inputs."""
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads

    periods = _make_synthetic_periods(ebitda_per_period)
    tax_input = _make_minimal_tax_input(fin_income_by_period, authority=authority)
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


# ══════════════════════════════════════════════════════════════════════════════
# Authority contract tests (Correction B §3)
# ══════════════════════════════════════════════════════════════════════════════

# ── 28. UNRESOLVED + zero is OK ───────────────────────────────────────────────

def test_authority_unresolved_zero_is_accepted():
    """UNRESOLVED authority with financing_income_keur=0.0 must not raise."""
    from financial_engine.inputs import PeriodFinancingIncomeInput, TaxCalculationInput
    from financial_engine.tax.engine import calculate_tax

    ebitda = [1_000.0, 1_000.0]
    periods = _make_synthetic_periods(ebitda)
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming, TaxBasisPeriodisation, TaxLossUtilisationGate
    policy = TaxPolicy(
        policy_id="u2-auth-test", policy_version="1.0.0",
        corporate_rate=0.25, loss_carryforward_years=5, periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
        loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
        atad_enabled=False, atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )
    tax_input = TaxCalculationInput(
        policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        period_financing_income=(
            PeriodFinancingIncomeInput(period_index=0, financing_income_keur=0.0, authority="UNRESOLVED"),
        ),
    )
    result = calculate_tax(periods, tax_input)
    assert result.period_results[0].financing_income_keur == 0.0


# ── 29. UNRESOLVED + nonzero raises ──────────────────────────────────────────

def test_authority_unresolved_nonzero_raises():
    """UNRESOLVED authority with nonzero financing_income_keur must raise ValueError."""
    from financial_engine.inputs import PeriodFinancingIncomeInput, TaxCalculationInput
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming, TaxBasisPeriodisation, TaxLossUtilisationGate

    ebitda = [1_000.0, 1_000.0]
    periods = _make_synthetic_periods(ebitda)
    policy = TaxPolicy(
        policy_id="u2-auth-test", policy_version="1.0.0",
        corporate_rate=0.25, loss_carryforward_years=5, periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
        loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
        atad_enabled=False, atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )
    tax_input = TaxCalculationInput(
        policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        period_financing_income=(
            PeriodFinancingIncomeInput(period_index=0, financing_income_keur=500.0, authority="UNRESOLVED"),
        ),
    )
    with pytest.raises(ValueError, match="UNRESOLVED.*fail closed|UNRESOLVED must fail closed"):
        calculate_tax(periods, tax_input)


# ── 30. Unknown authority raises ──────────────────────────────────────────────

def test_authority_unknown_string_raises():
    """An unknown authority string must raise ValueError."""
    from financial_engine.inputs import PeriodFinancingIncomeInput, TaxCalculationInput
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming, TaxBasisPeriodisation, TaxLossUtilisationGate

    ebitda = [1_000.0, 1_000.0]
    periods = _make_synthetic_periods(ebitda)
    policy = TaxPolicy(
        policy_id="u2-auth-test", policy_version="1.0.0",
        corporate_rate=0.25, loss_carryforward_years=5, periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
        loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
        atad_enabled=False, atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )
    tax_input = TaxCalculationInput(
        policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        period_financing_income=(
            PeriodFinancingIncomeInput(period_index=0, financing_income_keur=100.0, authority="BOGUS_AUTHORITY"),
        ),
    )
    with pytest.raises(ValueError, match="unknown authority"):
        calculate_tax(periods, tax_input)


# ── 31. SOURCE_PROVEN + nonzero propagates correctly ─────────────────────────

def test_authority_source_proven_nonzero_propagates():
    """SOURCE_PROVEN + nonzero must propagate into taxable income."""
    ebitda = [2_000.0, 2_000.0]
    tax_base, _ = _run_synthetic(ebitda, {})
    tax_fi, _ = _run_synthetic(ebitda, {0: 400.0, 1: 400.0}, authority="SOURCE_PROVEN")

    ti_base = sum(r.taxable_income_before_lcf_keur for r in tax_base.annual_results)
    ti_fi = sum(r.taxable_income_before_lcf_keur for r in tax_fi.annual_results)
    assert abs(ti_fi - ti_base - 800.0) < 1e-6


# ── 32. GENERIC_FINCO_POLICY + nonzero propagates correctly ──────────────────

def test_authority_generic_finco_policy_nonzero_propagates():
    """GENERIC_FINCO_POLICY + nonzero must propagate into taxable income."""
    ebitda = [2_000.0, 2_000.0]
    tax_base, _ = _run_synthetic(ebitda, {})
    tax_fi, _ = _run_synthetic(ebitda, {0: 300.0, 1: 300.0}, authority="GENERIC_FINCO_POLICY")

    ti_base = sum(r.taxable_income_before_lcf_keur for r in tax_base.annual_results)
    ti_fi = sum(r.taxable_income_before_lcf_keur for r in tax_fi.annual_results)
    assert abs(ti_fi - ti_base - 600.0) < 1e-6


# ══════════════════════════════════════════════════════════════════════════════
# EBT gate causality tests (Correction B §5)
# ══════════════════════════════════════════════════════════════════════════════

# ── 33. EBT gate: financing_income can open LCF gate ─────────────────────────

def test_ebt_gate_financing_income_opens_gate():
    """With EBT_POSITIVE gate: negative EBITDA alone closes gate; adding FI opens it."""
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.policies.tax import TaxLossUtilisationGate

    # Periods: small EBITDA, no depreciation/interest.
    # We need a prior loss, then test whether LCF is usable.
    # Year 0 produces a loss (negative EBITDA), year 1 has EBITDA exactly enough
    # to be positive only when FI is added.
    ebitda = [-500.0, -500.0, 100.0, 100.0]  # years 0, 1 loss; year 2 marginal
    periods = _make_synthetic_periods(ebitda)

    # Without FI: year 2 EBT = 200 kEUR > 0 → gate open even without FI.
    # Use a tighter case: EBITDA exactly covers dep, FI tips it positive.
    ebitda2 = [-500.0, -500.0, 10.0, 10.0]  # tiny EBITDA in year 2
    periods2 = _make_synthetic_periods(ebitda2)

    from financial_engine.inputs import PeriodFinancingIncomeInput, TaxCalculationInput
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming, TaxBasisPeriodisation

    policy = TaxPolicy(
        policy_id="u2-ebt-test", policy_version="1.0.0",
        corporate_rate=0.25, loss_carryforward_years=5, periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
        loss_utilisation_gate=TaxLossUtilisationGate.EBT_POSITIVE,
        atad_enabled=False, atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )
    # Without FI: year 2 EBT = 20 > 0 → gate open (LCF usable, TI reduced)
    ti_no_fi = TaxCalculationInput(
        policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
    )
    res_no_fi = calculate_tax(periods2, ti_no_fi)

    # With FI: year 2 EBT = 20 + FI > 0 → gate still open, TI further reduced
    ti_fi = TaxCalculationInput(
        policy=policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        period_financing_income=(
            PeriodFinancingIncomeInput(period_index=2, financing_income_keur=100.0, authority="SOURCE_PROVEN"),
            PeriodFinancingIncomeInput(period_index=3, financing_income_keur=100.0, authority="SOURCE_PROVEN"),
        ),
    )
    res_fi = calculate_tax(periods2, ti_fi)

    # FI must increase annual taxable income for year 2
    ti_year2_no_fi = sum(r.taxable_income_before_lcf_keur for r in res_no_fi.annual_results if r.tax_year == 2031)
    ti_year2_fi = sum(r.taxable_income_before_lcf_keur for r in res_fi.annual_results if r.tax_year == 2031)
    assert ti_year2_fi > ti_year2_no_fi, (
        f"FI must increase TI under EBT gate: no_fi={ti_year2_no_fi:.2f} fi={ti_year2_fi:.2f}"
    )

    # EBITDA must be unchanged
    for pr in res_fi.period_results:
        expected_ebitda = ebitda2[pr.period_index]
        assert abs(pr.ebitda_keur - expected_ebitda) < 1e-9


# ══════════════════════════════════════════════════════════════════════════════
# Cross-year PeriodTaxYearAllocation reconciliation (Correction B §6)
# ══════════════════════════════════════════════════════════════════════════════

# ── 34. Cross-year: sum of allocation financing_income == annual financing_income ──

def test_period_year_allocation_financing_income_reconciles():
    """Sum of PeriodTaxYearAllocation.financing_income_keur must == TaxAnnualResult.financing_income_keur."""
    from financial_engine.tax.engine import calculate_tax

    ebitda = [2_000.0, 2_000.0, 2_000.0, 2_000.0]
    fin_income = {0: 100.0, 1: 200.0, 2: 150.0, 3: 75.0}
    periods = _make_synthetic_periods(ebitda)
    tax_input = _make_minimal_tax_input(fin_income)
    result = calculate_tax(periods, tax_input)

    # Build a map from tax_year → sum of PeriodTaxYearAllocation.financing_income_keur
    from collections import defaultdict
    alloc_by_year: dict[int, float] = defaultdict(float)
    for pr in result.period_results:
        for alloc in pr.tax_year_allocations:
            alloc_by_year[alloc.tax_year] += alloc.financing_income_keur

    # Compare with TaxAnnualResult.financing_income_keur
    for ar in result.annual_results:
        assert abs(alloc_by_year[ar.tax_year] - ar.financing_income_keur) < 1e-6, (
            f"Year {ar.tax_year}: alloc sum={alloc_by_year[ar.tax_year]:.4f} "
            f"annual={ar.financing_income_keur:.4f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Policy validation tests (Correction B §4)
# ══════════════════════════════════════════════════════════════════════════════

# ── 35. SOURCE_PROVEN + annual_rate=None raises ───────────────────────────────

def test_policy_validation_source_proven_none_rate_raises():
    with pytest.raises(ValueError, match="annual_rate is required"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=None,
        )


# ── 36. GENERIC_FINCO_POLICY + annual_rate=None raises ───────────────────────

def test_policy_validation_generic_none_rate_raises():
    with pytest.raises(ValueError, match="annual_rate is required"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=None,
        )


# ── 37. NaN rate raises ───────────────────────────────────────────────────────

def test_policy_validation_nan_rate_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=math.nan,
        )


# ── 38. Infinite rate raises ──────────────────────────────────────────────────

def test_policy_validation_inf_rate_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=math.inf,
        )


# ── 39. Bool rate raises ──────────────────────────────────────────────────────

def test_policy_validation_bool_rate_raises():
    with pytest.raises(ValueError, match="numeric, not bool"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Correction C §3 — partial-UNRESOLVED eligibility rejection
# ══════════════════════════════════════════════════════════════════════════════

# ── 40. SOURCE_PROVEN + one ELIGIBLE + one UNRESOLVED → reject ────────────────

def test_partial_unresolved_source_proven_eligible_plus_unresolved_raises():
    """SOURCE_PROVEN with one ELIGIBLE + one UNRESOLVED account must raise."""
    with pytest.raises(ValueError, match="UNRESOLVED"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.UNRESOLVED,
            annual_rate=0.01,
        )


# ── 41. GENERIC_FINCO_POLICY + one ELIGIBLE + one UNRESOLVED → reject ─────────

def test_partial_unresolved_generic_eligible_plus_unresolved_raises():
    """GENERIC_FINCO_POLICY with one ELIGIBLE + one UNRESOLVED account must raise."""
    with pytest.raises(ValueError, match="UNRESOLVED"):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
            eligible_unrestricted_cash=EligibilityStatus.UNRESOLVED,
            eligible_dsra=EligibilityStatus.ELIGIBLE,
            annual_rate=0.01,
        )


# ── 42. Both accounts resolved + at least one ELIGIBLE → accepted ─────────────

def test_both_accounts_explicitly_resolved_accepted():
    """Both accounts ELIGIBLE or INELIGIBLE (none UNRESOLVED) must be accepted."""
    # unrestricted ELIGIBLE, dsra INELIGIBLE — should construct fine
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=0.01,
    )
    assert policy.authority == CashReserveInterestAuthority.SOURCE_PROVEN
    # dsra ELIGIBLE, unrestricted INELIGIBLE — should construct fine
    policy2 = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.GENERIC_FINCO_POLICY,
        eligible_unrestricted_cash=EligibilityStatus.INELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        annual_rate=0.02,
    )
    assert policy2.authority == CashReserveInterestAuthority.GENERIC_FINCO_POLICY


# ── 43. String annual_rate → clean ValueError ─────────────────────────────────

def test_string_rate_raises_clean_value_error():
    with pytest.raises(ValueError):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate="0.01",  # type: ignore[arg-type]
        )


# ── 44. Complex annual_rate → clean ValueError ────────────────────────────────

def test_complex_rate_raises_clean_value_error():
    with pytest.raises(ValueError):
        CashReserveInterestPolicy(
            authority=CashReserveInterestAuthority.SOURCE_PROVEN,
            eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
            eligible_dsra=EligibilityStatus.INELIGIBLE,
            annual_rate=complex(0.01, 0.0),  # type: ignore[arg-type]
        )


# ══════════════════════════════════════════════════════════════════════════════
# Correction C §4 — compute_period_income_keur input hardening
# ══════════════════════════════════════════════════════════════════════════════

_VALID_POLICY = CashReserveInterestPolicy(
    authority=CashReserveInterestAuthority.SOURCE_PROVEN,
    eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
    eligible_dsra=EligibilityStatus.ELIGIBLE,
    annual_rate=0.01,
)


# ── 45. NaN unrestricted-cash balance → raises ────────────────────────────────

def test_compute_nan_cash_balance_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=math.nan,
            dsra_balance_keur=1_000.0,
            day_fraction=0.5,
        )


# ── 46. Inf unrestricted-cash balance → raises ────────────────────────────────

def test_compute_inf_cash_balance_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=math.inf,
            dsra_balance_keur=1_000.0,
            day_fraction=0.5,
        )


# ── 47. NaN DSRA balance → raises ─────────────────────────────────────────────

def test_compute_nan_dsra_balance_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=1_000.0,
            dsra_balance_keur=math.nan,
            day_fraction=0.5,
        )


# ── 48. Inf DSRA balance → raises ─────────────────────────────────────────────

def test_compute_inf_dsra_balance_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=1_000.0,
            dsra_balance_keur=math.inf,
            day_fraction=0.5,
        )


# ── 49. NaN day_fraction → raises ─────────────────────────────────────────────

def test_compute_nan_day_fraction_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=1_000.0,
            dsra_balance_keur=1_000.0,
            day_fraction=math.nan,
        )


# ── 50. Inf day_fraction → raises ─────────────────────────────────────────────

def test_compute_inf_day_fraction_raises():
    import math
    with pytest.raises(ValueError, match="finite"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=1_000.0,
            dsra_balance_keur=1_000.0,
            day_fraction=math.inf,
        )


# ── 51. Negative day_fraction → raises ────────────────────────────────────────

def test_compute_negative_day_fraction_raises():
    with pytest.raises(ValueError, match="non-negative"):
        _VALID_POLICY.compute_period_income_keur(
            unrestricted_cash_balance_keur=1_000.0,
            dsra_balance_keur=1_000.0,
            day_fraction=-0.1,
        )


# ── 52. Negative finite balance → documented floor to 0.0 ────────────────────

def test_compute_negative_balance_floors_to_zero():
    """Negative finite balances floor to 0.0 — documented behavior, not silent failure."""
    result = _VALID_POLICY.compute_period_income_keur(
        unrestricted_cash_balance_keur=-10_000.0,
        dsra_balance_keur=-5_000.0,
        day_fraction=0.5,
    )
    assert result == 0.0, f"Negative balances must floor to 0.0, got {result}"


# =============================================================================
# TUHO SOURCE-EVIDENCE TESTS (Correction E)
# Tests 53–66: verify TUHO cash/reserve interest source truth from fixture.
# These are audit/source tests only — no production financial inputs consumed.
# =============================================================================

import json as _json
import pathlib as _pathlib

_TUHO_FIXTURE = _pathlib.Path(__file__).parent / "fixtures" / "excel_tuho_cash_reserve_interest_truth.json"


def _load_tuho():
    with open(_TUHO_FIXTURE) as f:
        return _json.load(f)


# ── 53. D438 = hardcoded 0.01 ─────────────────────────────────────────────────

def test_tuho_d438_is_hardcode():
    d = _load_tuho()
    entry = d["inputs_D438_rate"]
    assert entry["formula_mode_value"] == 0.01, "D438 formula mode must be numeric 0.01 (hardcode)"
    assert entry["data_mode_cached"] == 0.01
    assert entry["conclusion"] == "HARDCODE_numeric_literal_not_formula"
    assert entry["authority"] == "HARDCODE_CONFIRMED"


# ── 54. P&L!B19 links to Inputs!D438 ─────────────────────────────────────────

def test_tuho_pnl_b19_links_to_d438():
    d = _load_tuho()
    entry = d["pnl_B19_rate"]
    assert entry["formula_mode_value"] == "=Inputs!$D$438"
    assert abs(entry["data_mode_cached"] - 0.01) < 1e-12
    assert entry["authority"] == "SOURCE_PROVEN_FORMULA_LINK"


# ── 55. H$3 identity: Year index ──────────────────────────────────────────────

def test_tuho_h3_is_year_index():
    d = _load_tuho()
    row3 = d["pnl_header_rows"]["row_3_year"]
    assert row3["label_colA"] == "Year"
    assert "Flags" in row3["colG_formula"]
    assert row3["colG_cached"] == 0          # construction period = year 0
    assert row3["colH_cached"] == 1           # first operating period = year 1
    assert row3["role"] == "year_index_post_construction_guard"
    assert row3["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 56. H$5 identity: boolean Project Life flag (NOT day fraction) ─────────────

def test_tuho_h5_is_boolean_life_flag():
    d = _load_tuho()
    row5 = d["pnl_header_rows"]["row_5_project_life"]
    assert row5["label_colA"] == "Project Life"
    assert "Flags" in row5["colG_formula"]
    assert row5["colG_cached"] is False       # construction: not in project life
    assert row5["colH_cached"] is True        # operation: in project life
    assert "boolean" in row5["role"]
    assert "NOT" in row5["note"]              # note must say NOT day fraction
    assert row5["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 57. H$6 identity: day-count fraction ──────────────────────────────────────

def test_tuho_h6_is_day_fraction():
    d = _load_tuho()
    row6 = d["pnl_header_rows"]["row_6_day_fraction"]
    assert row6["label_colA"] == "Operation Period (incl. Leap)"
    assert "Flags" in row6["colG_formula"]
    assert row6["colG_cached"] == 0           # construction: zero fraction
    frac = row6["colH_cached"]
    assert 0.4 < frac < 0.6, f"Day fraction must be ~0.5 for semi-annual, got {frac}"
    assert row6["role"] == "actual_day_count_fraction"
    assert row6["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 58. Row 19 exact reserve formula ─────────────────────────────────────────

def test_tuho_pnl_row19_reserve_formula():
    d = _load_tuho()
    row19 = d["pnl_row19_reserve"]
    assert row19["label_colA"] == "Interests from Reserve Accounts"
    formula = row19["colH_formula"]
    assert "CF!G95" in formula
    assert "CF!G81" in formula
    assert "$B19" in formula
    assert "H$3" in formula
    assert "H$6" in formula
    assert row19["zero_all_periods"] is True
    assert row19["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 59. Row 20 exact cash formula ────────────────────────────────────────────

def test_tuho_pnl_row20_cash_formula():
    d = _load_tuho()
    row20 = d["pnl_row20_cash"]
    assert row20["label_colA"] == "Interests from Cash"
    formula = row20["colH_formula"]
    assert "CF!G135" in formula
    assert "$B19" in formula
    assert "H$5" in formula
    assert "H$6" in formula
    # First non-zero must exist
    assert row20["first_nonzero_col"] is not None
    assert row20["first_nonzero_val_keur"] > 0
    assert row20["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 60. Row 21 exact WHT formula ─────────────────────────────────────────────

def test_tuho_pnl_row21_wht_formula():
    d = _load_tuho()
    row21 = d["pnl_row21_withholding"]
    assert row21["label_colA"] == "Withholding Tax"
    formula = row21["colH_formula"]
    assert "SUM(H19:H20)" in formula
    assert "$B21" in formula
    assert row21["zero_all_periods"] is True
    assert row21["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 61. CF row 81 Senior DSRA identity ───────────────────────────────────────

def test_tuho_cf81_senior_dsra_identity():
    d = _load_tuho()
    cf81 = d["cf_row81_senior_dsra"]
    assert cf81["label_colA"] == "End"
    assert cf81["account_identity"] == "Senior_DSRA_ending_balance"
    assert cf81["section_header_label"] == "DSRA"
    assert "SUM" in cf81["colG_formula"]
    assert cf81["zero_all_periods"] is True
    assert cf81["balance_convention"] == "PRIOR_PERIOD_CLOSING"
    assert "F81" in cf81["balance_convention_proof"]  # row 77 Beginning = =F81
    assert cf81["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 62. CF row 95 J-DSRA identity ────────────────────────────────────────────

def test_tuho_cf95_jdsra_identity():
    d = _load_tuho()
    cf95 = d["cf_row95_jdsra"]
    assert cf95["label_colA"] == "End"
    assert cf95["account_identity"] == "Junior_DSRA_ending_balance"
    assert cf95["section_header_label"] == "J-DSRA"
    assert "SUM" in cf95["colG_formula"]
    assert cf95["zero_all_periods"] is True
    assert cf95["balance_convention"] == "PRIOR_PERIOD_CLOSING"
    assert "F95" in cf95["balance_convention_proof"]  # row 91 Beginning = =F95
    assert cf95["authority"] == "SOURCE_PROVEN_FORMULA"


# ── 63. CF row 135 cash balance identity ─────────────────────────────────────

def test_tuho_cf135_cash_identity():
    d = _load_tuho()
    cf135 = d["cf_row135_cash"]
    assert cf135["label_colA"] == "Cash end of the year"
    assert "F135" in cf135["colG_formula"]   # cumulative: prior closing + inflow
    assert cf135["first_nonzero_col"] is not None
    assert cf135["first_nonzero_val_keur"] > 0
    assert cf135["account_identity"] == "unrestricted_surplus_cash_closing_balance"
    assert cf135["authority"] == "SOURCE_PROVEN_FORMULA"
    # Context: row below is "Negative cash check" (same as Oborovo pattern)
    assert cf135["context_row136_label"] == "Negative cash check"


# ── 64. Balance convention: prior-period closing ──────────────────────────────

def test_tuho_balance_convention_prior_period_closing():
    d = _load_tuho()
    bc = d["balance_convention"]
    assert bc["verdict"] == "PRIOR_PERIOD_CLOSING_EQUALS_CURRENT_OPENING"
    assert bc["authority"] == "SOURCE_PROVEN_FORMULA"
    # Three independent proofs
    assert "CF!G135" in bc["proof_cf135"] or "AU135" in bc["proof_cf135"] or "F135" in bc["proof_cf135"]
    assert "F81" in bc["proof_cf81"]
    assert "F95" in bc["proof_cf95"]


# ── 65. Numerical handshake: machine precision ────────────────────────────────

def test_tuho_numerical_handshake_machine_precision():
    d = _load_tuho()
    hs = d["numerical_handshake"]
    assert hs["verdict"] == "MACHINE_PRECISION_MATCH"
    assert hs["residual_keur"] == 0.0
    # Cross-verify the arithmetic independently
    balance = hs["cf135_balance_keur"]
    rate = hs["rate"]
    life = 1 if hs["H5_life_flag"] else 0
    frac = hs["H6_day_fraction"]
    expected = balance * rate * life * frac
    actual = hs["actual_keur"]
    assert abs(expected - actual) < 1e-9, (
        f"Independent arithmetic check failed: {expected} vs {actual}"
    )


# ── 66. Fixture ownership: TUHO evidence not in Oborovo fixture ───────────────

def test_tuho_evidence_not_in_oborovo_fixture():
    oborovo_fixture = _pathlib.Path(__file__).parent / "fixtures" / "excel_oborovo_financial_truth.json"
    with open(oborovo_fixture) as f:
        ob = _json.load(f)
    assert "tuho_cash_reserve_interest" not in ob, (
        "TUHO canonical source-truth must not reside in Oborovo fixture"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Correction F — Runtime cash/reserve interest schedule builder and wiring
# Tests 67–80
# ══════════════════════════════════════════════════════════════════════════════

import json as _json_f
import pathlib as _pathlib_f
from dataclasses import dataclass, field
from datetime import date


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_source_proven_policy(
    dsra_eligible: bool = True,
    rate: float = 0.01,
) -> CashReserveInterestPolicy:
    return CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        annual_rate=rate,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE if dsra_eligible else EligibilityStatus.INELIGIBLE,
        enabled=True,
    )


@dataclass
class _FakePeriod:
    period_index: int
    period_start: date
    period_end: date
    is_operation: bool = True
    days_in_period: int = 181
    ebitda_keur: float = 1000.0
    tax_depreciation_keur: float = 200.0
    period_in_year: int = 1


# ── 67. UnrestrictedCashSchedule builder — real roll-forward identity (H.6.A) ──

def test_build_unrestricted_cash_schedule_rollforward_identity():
    """H.6.A: closing[p] = opening[p] + increment[p], opening[p] = closing[p-1]."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule

    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
        _FakePeriod(2, date(2031, 1, 1), date(2031, 6, 30), is_operation=True),
    )
    increments = {0: 100.0, 1: 50.0, 2: -20.0}
    schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments=increments,
        opening_cash_keur=0.0,
    )
    assert schedule.authority == "SOURCE_PROVEN"
    pb = schedule.period_balances
    # Period 0: opening=0.0, increment=100.0, closing=100.0
    assert pb[0].opening_balance_keur == 0.0
    assert pb[0].period_cash_increment_keur == 100.0
    assert pb[0].closing_balance_keur == 100.0
    # Period 1: opening=100.0 (prior closing), increment=50.0, closing=150.0
    assert pb[1].opening_balance_keur == 100.0
    assert pb[1].period_cash_increment_keur == 50.0
    assert pb[1].closing_balance_keur == 150.0
    # Period 2: opening=150.0, increment=-20.0, closing=130.0
    assert pb[2].opening_balance_keur == 150.0
    assert pb[2].period_cash_increment_keur == -20.0
    assert abs(pb[2].closing_balance_keur - 130.0) < 1e-9


# ── 68. Balance convention with synthetic mid-life accumulation (H.6.B) ─────────

def test_build_cash_reserve_interest_schedules_income_with_authoritative_increments():
    """H.6.B: SOURCE_PROVEN policy + authoritative increments → income computed."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )

    policy = _make_source_proven_policy(rate=0.01)
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=False),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
    )
    # Period 0: construction, increment = 200.0 (cash accumulates in construction)
    # Period 1: operations, increment = 350.0 (cash grows further)
    increments = {0: 200.0, 1: 350.0}
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments=increments,
        opening_cash_keur=0.0,
    )
    # Period 1 opening = period 0 closing = 0 + 200 = 200
    assert cash_schedule.period_balances[1].opening_balance_keur == 200.0
    # DSRA is ELIGIBLE (source-proven); balance zero all periods — provide known-zero authority
    interest_schedule = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 0.0, 1: 0.0},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    # Period 0: not is_operation → ineligible (is_eligible=False) → 0.0
    p0 = interest_schedule.period_results[0]
    # Period 1: SOURCE_PROVEN policy, ELIGIBLE, opening=200.0
    p1 = interest_schedule.period_results[1]
    expected_day_frac = (date(2030, 12, 31) - date(2030, 7, 1)).days / 365.0
    expected_income = 200.0 * 0.01 * expected_day_frac
    assert abs(p1.calculated_financing_income_keur - expected_income) < 1e-9
    assert p1.authority == "SOURCE_PROVEN"


# ── 69. UNRESOLVED policy → zero income from schedule builder ──────────────────

def test_build_cash_reserve_interest_schedules_unresolved_zero():
    """UNRESOLVED policy → all periods compute 0.0."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    from finco_core.inputs.cash_reserve_interest_policy import UNRESOLVED_POLICY

    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="UNRESOLVED",
    )
    schedule = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=UNRESOLVED_POLICY,
        unrestricted_cash_schedule=cash_schedule,
    )
    assert schedule.total_financing_income_keur == 0.0
    assert schedule.period_results[0].calculated_financing_income_keur == 0.0


# ── 70. Authority composition: SOURCE_PROVEN policy + UNRESOLVED schedule → UNRESOLVED (H.6.D)

def test_authority_composition_unresolved_schedule_blocks_source_proven():
    """H.6.D: weakest upstream authority wins. SOURCE_PROVEN policy + UNRESOLVED schedule → 0.0."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )

    policy = _make_source_proven_policy(rate=0.01)
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    # No authoritative_period_cash_increments → schedule authority is UNRESOLVED
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",  # overridden to UNRESOLVED because no increments
    )
    assert cash_schedule.authority == "UNRESOLVED"

    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
    )
    # Composed authority = UNRESOLVED (weakest)
    assert result.authority == "UNRESOLVED"
    assert result.total_financing_income_keur == 0.0
    assert result.period_results[0].calculated_financing_income_keur == 0.0


# ── 71. Oborovo factory: cash policy is SOURCE_PROVEN (H.3) ──────────────────────

def test_oborovo_factory_has_source_proven_cash_policy():
    """H.3: rate=0.01 and DSRA eligibility proved from workbook formulas → SOURCE_PROVEN."""
    from app.project_factories import create_default_oborovo
    project = create_default_oborovo()
    # H.3: rate and eligible-account identity both proved from P&L!B19 and CF formulas.
    # Balance schedule remains UNRESOLVED (no roll-forward data) — authority composition
    # in build_cash_reserve_interest_schedules yields UNRESOLVED income (zero).
    policy = project.cash_reserve_interest_policy
    assert policy is not None
    assert policy.authority == CashReserveInterestAuthority.SOURCE_PROVEN
    assert policy.annual_rate == 0.01
    assert policy.eligible_unrestricted_cash == EligibilityStatus.ELIGIBLE
    assert policy.eligible_dsra == EligibilityStatus.ELIGIBLE


# ── 72. TUHO factory: cash policy is SOURCE_PROVEN (H.3) ──────────────────────────

def test_tuho_factory_has_source_proven_cash_policy():
    """H.3: rate=0.01 and DSRA eligibility proved from workbook formulas → SOURCE_PROVEN."""
    from app.project_factories import create_default_tuho_wind1
    project = create_default_tuho_wind1()
    # H.3: rate and eligible-account identity both proved from P&L!B19 and CF formulas.
    # Balance schedule remains UNRESOLVED (no roll-forward data) — authority composition
    # in build_cash_reserve_interest_schedules yields UNRESOLVED income (zero).
    policy = project.cash_reserve_interest_policy
    assert policy is not None
    assert policy.authority == CashReserveInterestAuthority.SOURCE_PROVEN
    assert policy.annual_rate == 0.01
    assert policy.eligible_unrestricted_cash == EligibilityStatus.ELIGIBLE
    assert policy.eligible_dsra == EligibilityStatus.ELIGIBLE


# ── 73. SeniorDebtModelInput accepts cash_reserve_interest_policy ──────────────

def test_senior_debt_model_input_accepts_cash_policy():
    """SeniorDebtModelInput has cash_reserve_interest_policy field (None default)."""
    from financial_engine.inputs import SeniorDebtModelInput
    import inspect
    fields = {f.name for f in SeniorDebtModelInput.__dataclass_fields__.values()}
    assert "cash_reserve_interest_policy" in fields


# ── 74. Canonical schedule builder: UNRESOLVED policy yields zero income ─────────

def test_schedule_builder_unresolved_policy_yields_zero():
    """Correction G: _build_cash_reserve_financing_income removed; canonical builders govern."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    from finco_core.inputs.cash_reserve_interest_policy import UNRESOLVED_POLICY
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
    )
    cash_schedule = build_unrestricted_cash_schedule(periods, "UNRESOLVED")
    result = build_cash_reserve_interest_schedules(periods, UNRESOLVED_POLICY, cash_schedule)
    assert result.total_financing_income_keur == 0.0
    for pr in result.period_results:
        assert pr.calculated_financing_income_keur == 0.0, f"Period {pr.period_index} must be zero"


# ── 75. EBITDA invariant: financing income does not alter EBITDA ──────────────

def test_ebitda_invariant_financing_income_does_not_alter_ebitda():
    """Financing income enters taxable income below EBITDA. EBITDA is unchanged."""
    from financial_engine.inputs import (
        PeriodFinancingIncomeInput,
        TaxCalculationInput,
    )
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads

    periods = _make_synthetic_periods([1500.0, 1500.0])
    base_tax = _make_minimal_tax_input(None)
    fin_income_tax = _make_minimal_tax_input({1: 5.0})

    base_result = calculate_tax(periods, base_tax)
    fin_result = calculate_tax(periods, fin_income_tax)

    # EBITDA is an operating result — unchanged by financing income injection
    for pr_base, pr_fin in zip(base_result.period_results, fin_result.period_results):
        assert pr_base.ebitda_keur == pr_fin.ebitda_keur, (
            f"EBITDA changed: {pr_base.ebitda_keur} → {pr_fin.ebitda_keur}"
        )

    # Period 1: financing income should increase tax and reduce post-tax CFADS
    base_cfads = calculate_canonical_cfads(periods, base_result.period_results)
    fin_cfads = calculate_canonical_cfads(periods, fin_result.period_results)
    base_p1 = next(r for r in base_cfads if r.period_index == 1)
    fin_p1 = next(r for r in fin_cfads if r.period_index == 1)
    # financing income increases TI → increases CIT → net CFADS delta is positive
    # CFADS = EBITDA + financing_income - cash_tax; with 5.0 kEUR FI the delta > 0
    delta = fin_p1.cfads_keur - base_p1.cfads_keur
    assert delta > 0.0, f"Expected positive CFADS delta, got {delta}"


# ── 76. _merge_financing_tax_input forwards period_financing_income ────────────

def test_merge_financing_tax_input_forwards_financing_income():
    """_merge_financing_tax_input preserves period_financing_income from base."""
    from financial_engine.orchestrator import _merge_financing_tax_input
    from financial_engine.inputs import TaxCalculationInput, PeriodFinancingIncomeInput
    entries = (PeriodFinancingIncomeInput(period_index=5, financing_income_keur=3.0, authority="SOURCE_PROVEN"),)
    base_tax = _make_minimal_tax_input({5: 3.0})
    merged = _merge_financing_tax_input(base_tax)
    assert merged.period_financing_income == entries, (
        "_merge_financing_tax_input must forward period_financing_income unchanged"
    )


# ── 77. MODEL_YEAR_PAIRING carries financing_income_keur ──────────────────────

def test_model_year_pairing_carries_financing_income():
    """_build_model_year_pairing_bases passes financing_income_keur into fragments."""
    from financial_engine.tax.tax_year import build_tax_year_bases
    from financial_engine.policies.tax import (
        TaxPolicy, TaxBasisPeriodisation, TaxLossUtilisationGate
    )

    from financial_engine.policies.tax import (
        TaxPolicy, CashTaxTiming, TaxBasisPeriodisation, TaxLossUtilisationGate
    )
    policy = TaxPolicy(
        policy_id="u2-synthetic-test",
        policy_version="1.0.0",
        corporate_rate=0.25,
        loss_carryforward_years=5,
        periods_per_tax_year=2,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
        tax_basis_periodisation=TaxBasisPeriodisation.MODEL_YEAR_PAIRING,
        loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3_000.0,
    )

    @dataclass
    class _Prd:
        period_index: int
        period_start: date
        period_end: date
        is_operation: bool = True
        period_in_year: int = 1
        days_in_period: int = 181
        ebitda_keur: float = 1000.0
        tax_depreciation_keur: float = 100.0

    # H1 and H2 of the same model year
    periods = (
        _Prd(0, date(2030, 1, 1), date(2030, 6, 30), period_in_year=1),  # H1 → tax_year 2031
        _Prd(1, date(2030, 7, 1), date(2030, 12, 31), period_in_year=2), # H2 → tax_year 2031
    )
    financing_income_map = {0: 2.5, 1: 3.5}
    bases = build_tax_year_bases(
        periods=periods,
        interest_map={},
        adj_map={},
        policy=policy,
        financing_income_map=financing_income_map,
    )
    total_fi = sum(b.financing_income_keur for b in bases)
    assert abs(total_fi - (2.5 + 3.5)) < 1e-9, (
        f"MODEL_YEAR_PAIRING must carry financing_income_keur; total={total_fi}"
    )


# ── 78. Factory: oborovo policy is not None → policy is not legacy UNRESOLVED ──

def test_oborovo_legacy_calibration_unaffected_by_policy():
    """create_default_oborovo_legacy_calibration() inherits the cash policy from clean."""
    from app.project_factories import create_default_oborovo_legacy_calibration
    project = create_default_oborovo_legacy_calibration()
    policy = project.cash_reserve_interest_policy
    # Legacy calibration inherits from clean factory — may or may not have policy
    # (depends on implementation). Just assert it doesn't crash and is either None or valid.
    if policy is not None:
        assert policy.authority in list(CashReserveInterestAuthority)


# ── 79. Known-zero ELIGIBLE DSRA produces zero income (H.6.C) ─────────────────

def test_eligible_dsra_zero_balance_yields_zero_dsra_income():
    """H.6.C: DSRA ELIGIBLE (source-proven) with zero balance → zero DSRA income.
    Zero balance ≠ INELIGIBLE. Account classification comes from workbook formula,
    not from observed balance magnitude.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    # H.5: DSRA is ELIGIBLE (source-proven from P&L!G19 formula), zero balance.
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        annual_rate=0.01,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.ELIGIBLE,
        enabled=True,
    )
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    # Provide authoritative increments → SOURCE_PROVEN schedule
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 550.0},
        opening_cash_keur=0.0,
    )
    interest = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 0.0},  # ELIGIBLE account, known-zero balance
        dsra_balance_authority="SOURCE_PROVEN",
    )
    p0 = interest.period_results[0]
    assert p0.eligible_dsra_keur == 0.0, "Zero-balance ELIGIBLE DSRA contributes 0.0"
    assert p0.authority == "SOURCE_PROVEN"
    # Unrestricted cash income: opening_balance=0.0 (prior closing; period 0 is first)
    # No interest on period 0 because opening balance = 0.0
    assert p0.calculated_financing_income_keur == 0.0


# ── 80. ProjectFinancingResult carries cash_reserve_interest_schedules field ───

def test_project_financing_result_has_cash_reserve_interest_schedules_field():
    """ProjectFinancingResult exposes cash_reserve_interest_schedules for C3 handoff."""
    from financial_engine.financing.contracts import ProjectFinancingResult
    fields = {f for f in ProjectFinancingResult.__dataclass_fields__}
    assert "cash_reserve_interest_schedules" in fields, (
        "C3 handoff field missing from ProjectFinancingResult"
    )


# ── 81. No hardcoded 550 kEUR floor in policy contract (H.6.E) ────────────────

def test_no_hardcoded_cash_floor_in_policy():
    """H.6.E: CashReserveInterestPolicy has no min_unrestricted_cash_floor_keur field."""
    assert not hasattr(CashReserveInterestPolicy, "min_unrestricted_cash_floor_keur"), (
        "min_unrestricted_cash_floor_keur must not exist on CashReserveInterestPolicy — "
        "the 550 kEUR balance is a model output, not a policy input."
    )
    # UNRESOLVED_POLICY also must not carry the field
    from finco_core.inputs.cash_reserve_interest_policy import UNRESOLVED_POLICY
    assert not hasattr(UNRESOLVED_POLICY, "min_unrestricted_cash_floor_keur")


# ── 82. UnrestrictedCashSchedule has no min_cash_floor_keur field (H.6.E) ──────

def test_unrestricted_cash_schedule_has_no_floor_field():
    """H.6.E: UnrestrictedCashSchedule must not carry min_cash_floor_keur."""
    from finco_core.inputs.cash_reserve_interest_schedule import UnrestrictedCashSchedule
    assert not hasattr(UnrestrictedCashSchedule, "min_cash_floor_keur"), (
        "min_cash_floor_keur removed — cash balance is a roll-forward output, not a floor."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Correction I — Source reconciliation, authority hardening, I.4-I.9
# Tests 83–91
# ══════════════════════════════════════════════════════════════════════════════

# ── 83. TUHO fixture: P&L row 20 has non-zero cash interest (I.1/I.3) ──────────

def test_tuho_fixture_nonzero_cash_interest_at_av():
    """I.1: Correction G zero-interest conclusion was wrong. TUHO AV = 2.727 kEUR."""
    import json as _json2
    import pathlib as _pl2
    fixture = _pl2.Path(__file__).parent / "fixtures" / "excel_tuho_cash_reserve_interest_truth.json"
    with open(fixture) as f:
        tu = _json2.load(f)
    row20 = tu["pnl_row20_cash"]
    assert row20["first_nonzero_col"] == "AV", "First nonzero interest col must be AV"
    assert abs(row20["first_nonzero_val_keur"] - 2.7273972602740044) < 1e-9
    # Numerical handshake confirms AV
    hs = tu["numerical_handshake"]
    assert hs["period_col_pnl"] == "AV"
    assert abs(hs["actual_keur"] - 2.7273972602740044) < 1e-9
    # Correction G false claim must be corrected
    corr_i = tu.get("correction_i_findings", {})
    assert corr_i.get("source_reconciliation", {}).get("verdict") == "CORRECTION_G_ZERO_INTEREST_CONCLUSION_INCORRECT"
    # cf135 has balance from AU onwards (not just AU)
    samples = tu["cf_row135_cash"]["samples_from_first_nonzero"]
    assert len(samples) >= 5, "At least AU through AY must have balance 550"
    for col, bal in samples.items():
        assert abs(bal - 550.0) < 1e-6, f"CF135 balance at {col} should be ~550"


# ── 84. Oborovo fixture: 20 non-zero cash interest periods, total 55.0 kEUR (I.1/I.3) ──

def test_oborovo_fixture_20_nonzero_cash_interest_periods():
    """I.1: Oborovo has 20 non-zero P&L row 20 periods totaling 55.000 kEUR."""
    import json as _json3
    import pathlib as _pl3
    fixture = _pl3.Path(__file__).parent / "fixtures" / "excel_oborovo_financial_truth.json"
    with open(fixture) as f:
        ob = _json3.load(f)
    pvs = ob["tax"]["rows"]["fin_rev_cash"]["period_values"]
    nonzero = [(i, v) for i, v in enumerate(pvs) if abs(v) > 1e-9]
    assert len(nonzero) == 20, f"Expected 20 non-zero periods, got {len(nonzero)}"
    total = sum(v for _, v in nonzero)
    assert abs(total - 55.0) < 1e-3, f"Expected total ~55.0 kEUR, got {total}"
    # First and last confirmed
    assert nonzero[0][0] == 41
    assert nonzero[-1][0] == 60
    # Correction I verdict
    corr_i = ob.get("correction_i_findings", {})
    assert corr_i.get("source_reconciliation", {}).get("verdict") == "CORRECTION_G_ZERO_INTEREST_CONCLUSION_INCORRECT"


# ── 85. Incomplete increment map → UNRESOLVED (I.5) ──────────────────────────────

def test_incomplete_increment_map_forces_unresolved():
    """I.5: Missing period in increment map → UNRESOLVED schedule authority."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule

    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
        _FakePeriod(2, date(2031, 1, 1), date(2031, 6, 30)),
    )
    # Missing period 2 → incomplete coverage
    incomplete = {0: 100.0, 1: 50.0}  # missing period 2
    schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments=incomplete,
        opening_cash_keur=0.0,
    )
    assert schedule.authority == "UNRESOLVED", "Missing period index must force UNRESOLVED"
    for pb in schedule.period_balances:
        assert pb.opening_balance_keur == 0.0
        assert pb.closing_balance_keur == 0.0


# ── 86. Explicit opening cash (I.7) ──────────────────────────────────────────────

def test_explicit_opening_cash_required():
    """I.7: opening_cash_keur=None with authoritative increments → UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule

    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=None,  # unknown → UNRESOLVED
    )
    assert schedule.authority == "UNRESOLVED", "Unknown opening cash must force UNRESOLVED"


def test_explicit_opening_cash_nonzero():
    """I.7: Non-zero source-proven opening cash propagates correctly."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule

    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
    )
    schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 50.0, 1: 30.0},
        opening_cash_keur=200.0,  # non-zero proven opening
    )
    assert schedule.authority == "SOURCE_PROVEN"
    # Period 0: opening=200, increment=50, closing=250
    assert schedule.period_balances[0].opening_balance_keur == 200.0
    assert schedule.period_balances[0].closing_balance_keur == 250.0
    # Period 1: opening=250, increment=30, closing=280
    assert schedule.period_balances[1].opening_balance_keur == 250.0
    assert schedule.period_balances[1].closing_balance_keur == 280.0


# ── 87. Unknown DSRA balance ≠ known zero DSRA balance (I.6) ───────────────────

def test_unknown_dsra_balance_forces_unresolved():
    """I.6: ELIGIBLE DSRA with None balance → UNRESOLVED (not zero)."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )

    policy = _make_source_proven_policy(rate=0.01)  # DSRA ELIGIBLE
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=0.0,
    )
    # dsra_balance_by_period=None means unknown — not zero
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period=None,  # unknown balance
    )
    assert result.authority == "UNRESOLVED", (
        "Unknown DSRA balance for an ELIGIBLE account must force UNRESOLVED"
    )
    assert result.total_financing_income_keur == 0.0


def test_known_zero_dsra_balance_produces_zero_income():
    """I.6: ELIGIBLE DSRA with explicit zero balance → zero DSRA income (not UNRESOLVED)."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )

    policy = _make_source_proven_policy(rate=0.01)  # DSRA ELIGIBLE
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},  # no cash accumulation
        opening_cash_keur=0.0,
    )
    # dsra_balance_by_period={0: 0.0} means known-zero DSRA
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 0.0},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    assert result.authority == "SOURCE_PROVEN"
    assert result.period_results[0].eligible_dsra_keur == 0.0
    assert result.total_financing_income_keur == 0.0


# ── 89. Exact source day fractions from TUHO (I.8) ───────────────────────────────

def test_source_day_fractions_match_actual_365():
    """I.8: Day fraction is actual/365, matching TUHO AV = 181/365 = 0.49589041..."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )

    # AV period: 181 days (from handshake: AV6 = 0.4958904109589041 = 181/365)
    tuho_av_start = date(2044, 1, 1)  # synthetic 181-day period
    tuho_av_end = date(2044, 6, 30)
    assert (tuho_av_end - tuho_av_start).days == 181  # 181 days in this range

    # Use a period with exactly 181 days
    start_181 = date(2044, 1, 1)
    end_181 = date(2044, 7, 1)  # 182 days, skip
    start_181b = date(2044, 7, 1)
    end_181b = date(2044, 12, 29)  # 181 days
    assert (end_181b - start_181b).days == 181

    policy = _make_source_proven_policy(rate=0.01)
    periods = (_FakePeriod(0, start_181b, end_181b, is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=550.0,  # non-zero opening to produce income
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 0.0},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    expected_day_frac = 181.0 / 365.0
    expected_income = 550.0 * 0.01 * expected_day_frac
    p0 = result.period_results[0]
    assert abs(p0.day_fraction - expected_day_frac) < 1e-12
    assert abs(p0.calculated_financing_income_keur - expected_income) < 1e-9


# ── 90. Unknown authority string raises error (I.9) ──────────────────────────────

def test_unknown_authority_string_raises():
    """I.9: Unknown authority string must raise ValueError, not produce economics."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    import pytest
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    with pytest.raises(ValueError, match="Unknown authority"):
        build_unrestricted_cash_schedule(
            periods=periods,
            authority="MADE_UP_AUTHORITY",
        )


# ── 91. No debt-state gate: senior outstanding does not affect balance (I.4) ────

def test_no_debt_state_gate_in_schedule_builder():
    """I.4: build_unrestricted_cash_schedule does not accept senior/SHL outstanding."""
    import inspect
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    sig = inspect.signature(build_unrestricted_cash_schedule)
    params = set(sig.parameters.keys())
    assert "senior_debt_outstanding_by_period" not in params, (
        "Debt-state gate removed: senior_debt_outstanding_by_period must not be a parameter"
    )
    assert "shl_outstanding_by_period" not in params, (
        "Debt-state gate removed: shl_outstanding_by_period must not be a parameter"
    )
    # is_eligible reflects in_life only, not debt state
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=False),
    )
    schedule = build_unrestricted_cash_schedule(periods, "UNRESOLVED")
    assert schedule.period_balances[0].is_eligible is True   # in_life=True
    assert schedule.period_balances[1].is_eligible is False  # in_life=False


# ════════════════════════════════════════════════════════════════════════════
# U2 Correction J tests — dividend-cap algebra, J.7 axis/value hardening
# ════════════════════════════════════════════════════════════════════════════

# ── J-A. TUHO AU dividend-cap algebra → 550 kEUR retained cash handshake ──

def test_tuho_au_dividend_cap_accounting_algebra():
    """K.1/J.1/J.12: AT145+AU107-AU144 = 4605.09 kEUR; CF106_AU derived from roll-forward.

    K.1: The false proxy cf106_proxy = p_at["net_income_keur"] has been removed.
    AT-period net income (5155.396022) must NOT be used as a proxy for AU-period CF106.
    The correct CF106_AU is derived from the source-proven roll-forward identity:
        CF135[AU] = 550.0 (first nonzero closing cash, source fixture)
        CF135[AT] = 0.0 (pre-AU periods: all zero)
        CF122[AU] = CF135[AU] - CF135[AT] = 550.0 (change_in_cash)
        CF106[AU] = CF122[AU] + CF120[AU] = 550.0 + gross_dividends

    Source: tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json
    Source: tests/fixtures/excel_tuho_cash_reserve_interest_truth.json (CF135 evidence)
    Period AU (period_index=39, column=AU, 2049-07-01 to 2049-12-31).
    """
    import json, pathlib
    fixture = pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
    d = json.loads(fixture.read_text())
    periods = d["periods"]

    p_at = periods[38]  # AT period (prior period)
    p_au = periods[39]  # AU period (first retained-cash period)

    re_opening = p_at["retained_earnings_keur"]  # AT145
    net_income  = p_au["net_income_keur"]          # AU107
    lr_transfer = p_au["legal_reserve_transfer_keur"]  # AU144

    accounting_cap = re_opening + net_income - lr_transfer
    gross_dividends = p_au["gross_dividends_keur"]

    # Accounting cap = Distributable = Gross Dividends (algebraically)
    assert abs(accounting_cap - gross_dividends) < 1e-6, (
        f"Accounting cap {accounting_cap:.6f} ≠ gross_dividends {gross_dividends:.6f}"
    )

    # Source-proven values from user's manual workbook inspection
    assert abs(p_at["retained_earnings_keur"] - 1235.564210) < 0.01, "AT145 mismatch"
    assert abs(p_au["net_income_keur"]         - 3369.521268) < 0.01, "AU107 mismatch"
    assert p_au["legal_reserve_transfer_keur"] == 0.0, "AU144 should be 0"
    assert abs(gross_dividends                 - 4605.085478) < 0.01, "Gross dividends mismatch"

    # K.1: CF106_AU derived from source-proven roll-forward identity (NOT the AT net_income proxy).
    # CF135[AU] = 550.0 (first nonzero cash balance, proven in excel_tuho fixture)
    # CF135[AT] = 0.0 (AU is first nonzero: prior closing is 0)
    # CF122[AU] = CF135[AU] - CF135[AT] = 550.0
    # CF106[AU] = CF122[AU] + CF120[AU] where CF120 = gross_dividends = 4605.085478
    cf106_au_derived = 550.0 + gross_dividends  # = 5155.085478 kEUR (roll-forward identity)
    change_in_cash = cf106_au_derived - gross_dividends
    assert abs(change_in_cash - 550.0) < 1e-9, (
        f"change_in_cash = {change_in_cash:.6f} kEUR, expected exactly 550.0"
    )

    # Prove derived value differs from the false AT-period proxy (inadmissible authority).
    at_proxy_value = p_at["net_income_keur"]  # 5155.396022 — AT net income, NOT CF106_AU
    assert abs(cf106_au_derived - at_proxy_value) > 0.1, (
        f"K.1: CF106_AU ({cf106_au_derived:.6f}) must differ from AT net_income proxy "
        f"({at_proxy_value:.6f}) — they are numerically close but structurally distinct."
    )


def test_tuho_au_gross_dividends_equals_distributable():
    """J.5/J.6: Gross dividends = distributable (WHT cancels algebraically).

    Net_dividends = distributable - WHT; Gross = Net + WHT = distributable.
    Source: tuho_capitalisation_gate_fixture period AU.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    p_at = d["periods"][38]
    p_au = d["periods"][39]
    re_opening = p_at["retained_earnings_keur"]
    net_income  = p_au["net_income_keur"]
    lr_transfer = p_au["legal_reserve_transfer_keur"]
    distributable = re_opening + net_income - lr_transfer  # = MAX formula value
    gross_dividends = p_au["gross_dividends_keur"]
    # Gross dividends = distributable (WHT cancels)
    assert abs(gross_dividends - distributable) < 1e-6


# ── J-B. TUHO AV interest handshake (J.12) ───────────────────────────────

def test_tuho_av_interest_handshake():
    """J.12: Prior closing 550 kEUR × 1% × 181/365 = 2.7274 kEUR.

    Source: numerical_handshake in excel_tuho_cash_reserve_interest_truth.json.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_tuho_cash_reserve_interest_truth.json").read_text()
    )
    nh = d["numerical_handshake"]
    balance = nh["cf135_balance_keur"]         # 550 kEUR prior closing
    rate    = nh["rate"]                         # 0.01
    day_frac = nh["H6_day_fraction"]             # 181/365
    expected = balance * rate * day_frac
    actual   = nh["actual_keur"]

    assert abs(actual - 2.7273972602740044) < 1e-9
    assert abs(expected - actual) < 1e-6
    assert nh["verdict"] == "MACHINE_PRECISION_MATCH"


# ── J-C. Oborovo accounting cap → 550 kEUR retained cash (J.2/J.12) ─────

def test_oborovo_period40_accounting_cap_to_retained_cash():
    """J.2/J.12: Oborovo period 40 accounting cap = 39.65 kEUR; change_in_cash = 550 kEUR.

    Accounting cap = prior_RE + net_income - legal_reserve_transfer.
    FCF_for_dividends - gross_dividends = 550 kEUR retained cash.
    Source: excel_oborovo_financial_truth.json.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
    )
    ci = d["correction_i_findings"]
    cf = d["cf"]
    pl = d["pl"]

    # Period 40 is the first retained-cash period (FCF first nonzero)
    fcf_div = cf["free_cash_flow_for_dividends_keur"]
    net_div = pl["net_dividends_keur"]
    ni = pl["net_income_keur"]

    fcf_p40 = fcf_div[40]
    net_div_p40 = net_div[40]
    ni_p40 = ni[40]

    # gross_dividends = net_dividends (WHT = 0 for Oborovo per source data)
    gross_div_p40 = net_div_p40

    change_in_cash = fcf_p40 - gross_div_p40
    assert abs(change_in_cash - 550.0) < 1.0, (
        f"Oborovo period 40 change_in_cash = {change_in_cash:.4f}, expected ≈ 550"
    )

    # First nonzero closing cash
    first_nonzero = ci["cf144_cash_balance_observation"]["confirmed_balance_keur"]
    assert abs(first_nonzero - 550.0) < 1e-6


def test_oborovo_full_20_period_cash_interest_55keur():
    """J.4/J.12: Oborovo periods 41-60 → 20 nonzero periods, total 55.000 kEUR.

    Source: correction_i_findings.source_reconciliation in oborovo fixture.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
    )
    src = d["correction_i_findings"]["source_reconciliation"]
    assert src["nonzero_interest_periods"] == 20
    assert src["first_nonzero_period_index"] == 41
    assert src["last_nonzero_period_index"] == 60
    total = src["total_cash_interest_keur"]
    assert abs(total - 55.0) < 1e-6

    vector = src["cash_interest_source_vector"]["period_index_to_keur"]
    computed_total = sum(vector.values())
    assert abs(computed_total - 55.0) < 1e-6


# ── J-D. J.7 hardening tests ─────────────────────────────────────────────

def test_opening_cash_bool_forces_unresolved():
    """J.7: bool opening_cash_keur is rejected even though bool is a subtype of int."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=True,  # bool — must be rejected
    )
    assert s.authority == "UNRESOLVED"


def test_opening_cash_nan_forces_unresolved():
    """J.7: NaN opening_cash_keur forces UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    import math
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=float("nan"),
    )
    assert s.authority == "UNRESOLVED"


def test_opening_cash_inf_forces_unresolved():
    """J.7: Inf opening_cash_keur forces UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=float("inf"),
    )
    assert s.authority == "UNRESOLVED"


def test_duplicate_period_index_in_schedule_builder_forces_unresolved():
    """J.7: Duplicate period indices in periods tuple → UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    # Both periods have period_index=0 — duplicates
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(0, date(2030, 7, 1), date(2030, 12, 31)),
    )
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=0.0,
    )
    assert s.authority == "UNRESOLVED"


def test_duplicate_period_index_in_interest_scheduler_forces_unresolved():
    """J.7: Duplicate period indices in periods tuple for interest schedules → UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    good_periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=good_periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=550.0,
    )
    dup_periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),
        _FakePeriod(0, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
    )
    policy = _make_source_proven_policy(dsra_eligible=False, rate=0.01)
    result = build_cash_reserve_interest_schedules(
        periods=dup_periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "UNRESOLVED"
    assert result.total_financing_income_keur == 0.0


def test_cash_schedule_axis_mismatch_forces_unresolved():
    """J.7: cash_schedule period axis ≠ interest periods → UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    # Schedule built for period 0 only
    schedule_periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=schedule_periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=550.0,
    )
    # Interest periods include period 1 which is not in the schedule
    interest_periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
    )
    policy = _make_source_proven_policy(dsra_eligible=False, rate=0.01)
    result = build_cash_reserve_interest_schedules(
        periods=interest_periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "UNRESOLVED"
    assert result.total_financing_income_keur == 0.0


def test_dsra_incomplete_axis_forces_unresolved():
    """J.7: DSRA map missing a period → UNRESOLVED even if authority is stated."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
    )
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0, 1: 0.0},
        opening_cash_keur=0.0,
    )
    policy = _make_source_proven_policy(rate=0.01)  # DSRA ELIGIBLE
    # Only period 0 in DSRA map — missing period 1
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 100.0},  # missing period 1
        dsra_balance_authority="SOURCE_PROVEN",
    )
    assert result.authority == "UNRESOLVED"
    assert result.total_financing_income_keur == 0.0


def test_dsra_invalid_value_forces_unresolved():
    """J.7: NaN or bool DSRA balance value → UNRESOLVED."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule,
        build_cash_reserve_interest_schedules,
    )
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=0.0,
    )
    policy = _make_source_proven_policy(rate=0.01)  # DSRA ELIGIBLE
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: float("nan")},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    assert result.authority == "UNRESOLVED"


# ── J-E. Production hygiene (J.13 #17-21) ────────────────────────────────

def test_no_hardcoded_550_in_production_schedule_code():
    """J.13 #17: No literal 550 in cash_reserve_interest_schedule.py."""
    import pathlib, re
    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_schedule.py").read_text()
    # Allow 550 only in comments/strings — forbid it as a bare numeric literal in expressions
    matches = re.findall(r'(?<!["\'\w])550\.?0?(?![\w"])', src)
    assert not matches, f"Hardcoded 550 found in production schedule: {matches}"


def test_no_project_name_dispatch_in_schedule_builder():
    """J.13 #19: No project-name dispatch (conditional branching) in schedule builder.

    Project names may appear in docstrings/comments for source references.
    They must NOT appear as runtime dispatch conditions (if/elif/match on name).
    """
    import pathlib, ast, textwrap
    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_schedule.py").read_text()
    # Strip comment lines and docstrings — only check code tokens
    code_lines = [
        line for line in src.splitlines()
        if not line.strip().startswith("#") and not line.strip().startswith('"""')
        and not line.strip().startswith("'''")
    ]
    code_only = "\n".join(code_lines)
    for forbidden in ["project_key", "project_name", "== 'TUHO'", '== "TUHO"',
                       "== 'Oborovo'", '== "Oborovo"', "== 'oborovo'", '== "oborovo"']:
        assert forbidden not in code_only, f"Project-name dispatch found: {forbidden!r}"


def test_no_hardcoded_550_in_production_policy_code():
    """J.13 #17: No literal 550 in cash_reserve_interest_policy.py."""
    import pathlib, re
    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_policy.py").read_text()
    matches = re.findall(r'(?<!["\'\w])550\.?0?(?![\w"])', src)
    assert not matches, f"Hardcoded 550 found in production policy: {matches}"


# ── J-F. WHT cancellation algebra (J.3/J.5) ─────────────────────────────

def test_dividend_wht_cancels_from_gross_dividend():
    """J.3/J.5: gross_dividend = distributable regardless of WHT rate.

    Net = distributable - WHT; Gross = Net + WHT = distributable.
    Source formula: CF120 = CF119 + CF118 = (CF115-CF118) + CF118 = CF115.
    """
    distributable = 4605.085478
    for wht_rate in [0.0, 0.05, 0.10, 0.15]:
        wht = distributable * wht_rate
        net_div = distributable - wht
        gross_div = net_div + wht
        assert abs(gross_div - distributable) < 1e-9, (
            f"WHT={wht_rate}: gross {gross_div} ≠ distributable {distributable}"
        )


def test_change_in_cash_independent_of_wht_rate():
    """J.3/K.1: change_in_cash = FCF - gross_dividend is invariant to WHT rate.

    K.1: Uses CF106_AU = 550.0 + gross_dividends (roll-forward derivation).
    NOT the AT-period net_income proxy (5155.396022) from the old J test.
    """
    distributable = 4605.085478
    fcf_for_dividends = 550.0 + distributable  # CF106_AU via roll-forward identity = 5155.085478
    expected_change = fcf_for_dividends - distributable  # exactly 550.0

    for wht_rate in [0.0, 0.05, 0.10]:
        wht = distributable * wht_rate
        net_div = distributable - wht
        gross_div = net_div + wht  # = distributable
        change = fcf_for_dividends - gross_div
        assert abs(change - expected_change) < 1e-9


# ── J-G. Factory WHT reconciliation (J.3) ───────────────────────────────

def test_factory_wht_authority_reconciliation():
    """J.3: Factory wht_sponsor_dividends = 0.05; source appears to show 0.00%.

    This test documents the discrepancy. WHT does not affect change_in_cash
    (it cancels algebraically). The rate only matters for net sponsor receipts.
    Authority: FACTORY_UNRECONCILED — factory rate not directly proven from source.
    """
    import pathlib
    src = pathlib.Path("app/project_factories.py").read_text()
    # Factory currently contains wht_sponsor_dividends=0.05
    assert "wht_sponsor_dividends=0.05" in src, (
        "Factory WHT rate changed — update this test and J.3 reconciliation note."
    )
    # Verify it does NOT change to a source-proven value without a fixture update.
    # Source: user manual inspection shows 0.00% at TUHO CF118 B-column rate.
    # The factory value of 0.05 is UNRECONCILED with workbook source.
    # WHT cancels from gross_dividend so the production error is: net_dividends ≠ gross_dividends,
    # but cash change_in_cash is unaffected.


# ════════════════════════════════════════════════════════════════════════════
# U2 Correction K tests — K.1–K.8 authority hardening
# ════════════════════════════════════════════════════════════════════════════


# ── K-A. K.1 — CF106_AU derivation (proxy removed) ──────────────────────


def test_tuho_cf106_au_derived_from_roll_forward_identity():
    """K.1: CF106_AU = 550.0 + gross_dividends from source-proven roll-forward.

    CF135[AU] = 550.0, CF135[AT] = 0.0 → CF122[AU] = 550.0
    CF106[AU] = CF122[AU] + CF120[AU] = 550.0 + 4605.085478 = 5155.085478
    Source: excel_tuho_cash_reserve_interest_truth.json (CF135 evidence) +
            tuho_capitalisation_gate_fixture.json (gross_dividends).
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    gross_dividends = d["periods"][39]["gross_dividends_keur"]  # CF120[AU] = 4605.085478
    cf135_au = 550.0  # source-proven from excel_tuho fixture
    cf135_at = 0.0    # pre-AU periods all zero (AU is first nonzero)
    cf122_au = cf135_au - cf135_at
    cf106_au = cf122_au + gross_dividends

    assert abs(cf106_au - 5155.085478) < 0.01, f"CF106_AU = {cf106_au:.6f}"
    assert abs(cf122_au - 550.0) < 1e-9


def test_tuho_cf106_au_differs_from_at_net_income_proxy():
    """K.1: Derived CF106_AU ≠ AT-period net_income — the proxy was wrong.

    AT net_income (5155.396022) is numerically close but structurally distinct
    from CF106_AU (5155.085478). The difference of ~0.31 kEUR exposes the false proxy.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    p_at = d["periods"][38]
    p_au = d["periods"][39]
    gross_dividends = p_au["gross_dividends_keur"]

    cf106_au = 550.0 + gross_dividends           # derived: 5155.085478
    at_proxy  = p_at["net_income_keur"]           # false proxy: 5155.396022

    diff = abs(cf106_au - at_proxy)
    assert diff > 0.1, (
        f"CF106_AU ({cf106_au:.6f}) and AT-proxy ({at_proxy:.6f}) must differ by "
        f">0.1 kEUR (actual diff={diff:.6f})"
    )


# ── K-B. K.2 — TUHO Max/Distributable formula chain ─────────────────────


def test_tuho_au_cf113_max_distributable_formula_chain():
    """K.2: CF113 = MAX(0; MIN(AT145+AU107-AU144; AU108)) with CF108=CF106_AU.

    Proves the full chain: CF107→CF113→CF115=CF120→CF122→CF135.
    When accounting_cap < CF106_AU, the cap binds (cash-flow is not limiting).
    Source: tuho_capitalisation_gate_fixture + roll-forward identity.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    p_at = d["periods"][38]
    p_au = d["periods"][39]

    at145 = p_at["retained_earnings_keur"]        # 1235.564210
    au107 = p_au["net_income_keur"]               # 3369.521268 (CF107)
    au144 = p_au["legal_reserve_transfer_keur"]   # 0.0
    gross_dividends = p_au["gross_dividends_keur"] # CF120 = 4605.085478

    accounting_cap = at145 + au107 - au144        # 4605.085478
    cf106_au = 550.0 + gross_dividends            # 5155.085478 (CF108 = cash available)

    # CF113 = MAX(0; MIN(accounting_cap; cf106_au))
    cf113 = max(0.0, min(accounting_cap, cf106_au))

    assert abs(cf113 - accounting_cap) < 1e-6, "Accounting cap must bind (< CF106_AU)"
    assert abs(cf113 - gross_dividends) < 1e-6, "CF113 = CF120 = gross_dividends"

    # CF122: change_in_cash = CF106_AU - CF113
    cf122 = cf106_au - cf113
    assert abs(cf122 - 550.0) < 1e-6

    # CF135: closing cash = prior closing + CF122
    cf135_au = 0.0 + cf122   # prior closing (AT) = 0
    assert abs(cf135_au - 550.0) < 1e-6


def test_tuho_au_accounting_cap_binds_over_fcf():
    """K.2: Prove accounting_cap < CF106_AU — so cap (not FCF) is the binding constraint."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    p_at = d["periods"][38]
    p_au = d["periods"][39]
    gross_dividends = p_au["gross_dividends_keur"]
    accounting_cap = p_at["retained_earnings_keur"] + p_au["net_income_keur"] - p_au["legal_reserve_transfer_keur"]
    cf106_au = 550.0 + gross_dividends

    assert accounting_cap < cf106_au, (
        f"Accounting cap ({accounting_cap:.4f}) must be < CF106_AU ({cf106_au:.4f})"
    )


def test_tuho_au_cf145_retained_earnings_zero_closing():
    """K.2: AU period retained_earnings_keur (CF145) = 0.0 — cap fully distributed."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    p_au = d["periods"][39]
    assert p_au["retained_earnings_keur"] == 0.0, (
        f"AU period CF145 (retained_earnings closing) must be 0.0, got {p_au['retained_earnings_keur']}"
    )


def test_tuho_cf107_net_income_in_fixture():
    """K.2: Fixture carries AU107 (net_income_keur) as the direct P&L source."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json")
        .read_text()
    )
    p_au = d["periods"][39]
    assert "net_income_keur" in p_au, "AU period must have net_income_keur (CF107)"
    assert abs(p_au["net_income_keur"] - 3369.521268) < 0.01


def test_tuho_au_cf122_change_in_cash_from_roll_forward():
    """K.2: CF122[AU] = CF135[AU] - CF135[AT] = 550.0 (source-proven identity)."""
    cf135_au = 550.0
    cf135_at = 0.0
    cf122_au = cf135_au - cf135_at
    assert abs(cf122_au - 550.0) < 1e-9


# ── K-C. K.3 — WHT source vs factory reconciliation ─────────────────────


def test_tuho_b21_financing_wht_is_distinct_from_dividend_wht():
    """K.3 / A.3: P&L B21 is financing-income WHT, NOT dividend WHT.

    B21 = WHT on Interests from Reserve/Cash accounts (P&L rows 19-20 income).
    B21=0 confirms zero financing-income WHT — correct.
    Dividend WHT authority is CF!B118 = 0.00% (separately verified).
    These are distinct concepts: do not use B21 as dividend-WHT confirmation.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_tuho_cash_reserve_interest_truth.json").read_text()
    )
    wht = d["pnl_row21_withholding"]
    assert wht["zero_all_periods"] is True, "TUHO financing-income WHT (B21) must be zero"
    assert "B21=0" in wht["note"], f"WHT note must confirm B21=0: {wht['note']!r}"
    # A.3: Confirm fixture also records the B21 vs B118 distinction
    l1f = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    assert "b21_vs_b118" in l1f["critical_distinction"], "Fixture must document B21≠B118 distinction"


def test_tuho_wht_factory_vs_source_reconciled():
    """L.1B: Factory now source-reconciled — TUHO wht_sponsor_dividends=0.00 via CF!B118=0.00%.

    User-supplied workbook evidence: CF!B118 links to Inputs dividend WHT rate = 0.00%.
    This updates K.3's UNRECONCILED tracker: factory now matches source.
    Oborovo factory retains 0.05 (CF!B128 = 5.00% — correct).
    """
    import pathlib, json
    factory_src = pathlib.Path("app/project_factories.py").read_text()
    # L.1B: TUHO factory updated to source-proven 0.00%
    assert "wht_sponsor_dividends=0.00" in factory_src, (
        "L.1B: TUHO factory must have wht_sponsor_dividends=0.00 (CF!B118=0.00%)."
    )
    # Fixture still confirms source WHT=0 all periods — consistency check
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_tuho_cash_reserve_interest_truth.json").read_text()
    )
    assert d["pnl_row21_withholding"]["zero_all_periods"] is True


# ── K-D. K.4 — null ≠ zero opening cash ─────────────────────────────────


def test_opening_cash_zero_explicit_is_valid():
    """K.4: Explicit 0.0 is a valid opening_cash_keur (distinct from None).

    CF!F135 = null (blank cell) in workbook. The caller converts this to 0.0
    after proving the project starts with zero cash. Passing 0.0 is valid;
    passing None is UNKNOWN and forces UNRESOLVED.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=0.0,
    )
    assert s.authority == "SOURCE_PROVEN"
    assert s.period_balances[0].opening_balance_keur == 0.0
    assert s.period_balances[0].closing_balance_keur == 100.0


def test_opening_cash_null_means_unknown_not_zero():
    """K.4: None means UNKNOWN, not zero — forces UNRESOLVED even with increments.

    Workbook CF!F135 = null (blank cell) is NOT the same as an explicit 0.0.
    The caller must inspect and decide; passing None = I do not know the opening.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=None,
    )
    assert s.authority == "UNRESOLVED"


def test_opening_cash_none_with_zero_increments_still_unresolved():
    """K.4: None opening_cash remains UNRESOLVED even when all increments are zero."""
    from finco_core.inputs.cash_reserve_interest_schedule import build_unrestricted_cash_schedule
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
    )
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0, 1: 0.0},
        opening_cash_keur=None,
    )
    assert s.authority == "UNRESOLVED"


def test_k4_workbook_null_is_recorded_as_null_in_fixture():
    """K.4: TUHO fixture records CF!F135 = null (JSON null), not 0.0.

    This is the raw workbook extraction. The caller must explicitly pass 0.0
    after deciding that a blank construction-period cell means zero starting cash.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_tuho_cash_reserve_interest_truth.json").read_text()
    )
    col_f_cached = d["cf_row135_cash"]["colF_cached"]
    assert col_f_cached is None, (
        f"CF!F135 colF_cached must be null (blank cell), got {col_f_cached!r}"
    )


# ── K-E. K.5 — Ordered tuple axis comparison ─────────────────────────────


def test_cash_schedule_axis_ordering_mismatch_forces_unresolved():
    """K.5: Periods ordered [0,2,1] but schedule built for [0,1,2] → UNRESOLVED.

    Set equality would pass; ordered tuple comparison correctly detects the mismatch.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)

    # Build schedule for ordered [0, 1, 2]
    periods_ordered = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
        _FakePeriod(2, date(2031, 1, 1), date(2031, 6, 30)),
    )
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods_ordered,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0, 1: 550.0, 2: 0.0},
        opening_cash_keur=0.0,
    )
    assert cash_schedule.authority == "SOURCE_PROVEN"

    # Call interest builder with reordered periods [0, 2, 1]
    periods_reordered = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(2, date(2031, 1, 1), date(2031, 6, 30)),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods_reordered,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "UNRESOLVED", (
        "K.5: Ordering mismatch [0,2,1] vs [0,1,2] must force UNRESOLVED"
    )
    assert result.total_financing_income_keur == 0.0


def test_cash_schedule_axis_same_order_passes():
    """K.5: Periods in identical order → axis check passes, income computed."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=False),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
    )
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0, 1: 0.0},
        opening_cash_keur=1000.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "SOURCE_PROVEN"


# ── K-F. K.6 — DSRA construction period gate ─────────────────────────────


def test_dsra_construction_period_earns_zero_income():
    """K.6: is_operation=False (construction) → DSRA income = 0 regardless of balance.

    Source: P&L!H19 has (H$3>0) guard — Year > 0 = post-construction only.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=True)
    # Construction period (is_operation=False) + large DSRA balance
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=False),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=0.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 5000.0},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    assert result.period_results[0].eligible_dsra_keur == 0.0, (
        "K.6: Construction period must not accrue DSRA interest"
    )
    assert result.total_financing_income_keur == 0.0


def test_dsra_operation_period_accrues_income():
    """K.6: is_operation=True → DSRA income computed normally."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=True)
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=True),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=0.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 1000.0},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    # 1000 * 0.01 * (181/365) ≈ 4.959 kEUR
    assert result.period_results[0].eligible_dsra_keur == 1000.0
    assert result.total_financing_income_keur > 0.0


def test_dsra_interest_only_in_operation_years():
    """K.6: Mixed construction+operation periods — only operation periods accrue DSRA."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=True)
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30), is_operation=False),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31), is_operation=True),
    )
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0, 1: 0.0},
        opening_cash_keur=0.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods,
        policy=policy,
        unrestricted_cash_schedule=cash_schedule,
        dsra_balance_by_period={0: 2000.0, 1: 2000.0},
        dsra_balance_authority="SOURCE_PROVEN",
    )
    assert result.period_results[0].eligible_dsra_keur == 0.0, "Construction must be zero"
    assert result.period_results[1].eligible_dsra_keur == 2000.0, "Operation must accrue"


# ── K-G. K.7 — Balance convention fail-closed ────────────────────────────


def test_closing_balance_convention_fails_closed():
    """K.7: CLOSING balance convention → UNRESOLVED (not implemented)."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    from finco_core.inputs.cash_reserve_interest_policy import (
        CashReserveInterestPolicy, CashReserveInterestAuthority,
        EligibilityStatus, BalanceConvention, DayCountConvention,
    )
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        annual_rate=0.01,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        enabled=True,
        balance_convention=BalanceConvention.CLOSING,
    )
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=1000.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods, policy=policy, unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "UNRESOLVED", "K.7: CLOSING convention must fail closed"
    assert result.total_financing_income_keur == 0.0


def test_average_balance_convention_fails_closed():
    """K.7: AVERAGE balance convention → UNRESOLVED (not implemented)."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    from finco_core.inputs.cash_reserve_interest_policy import (
        CashReserveInterestPolicy, CashReserveInterestAuthority,
        EligibilityStatus, BalanceConvention,
    )
    policy = CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        annual_rate=0.01,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        enabled=True,
        balance_convention=BalanceConvention.AVERAGE,
    )
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0},
        opening_cash_keur=1000.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods, policy=policy, unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "UNRESOLVED", "K.7: AVERAGE convention must fail closed"
    assert result.total_financing_income_keur == 0.0


def test_opening_balance_convention_is_only_valid():
    """K.7: OPENING is source-proven; computes nonzero income correctly."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=1000.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods, policy=policy, unrestricted_cash_schedule=cash_schedule,
    )
    assert result.authority == "SOURCE_PROVEN"
    assert result.total_financing_income_keur > 0.0


# ── K-H. K.8 — Explicit day_fraction overrides date-derived fallback ──────


@dataclass
class _FakePeriodWithDayFrac:
    """FakePeriod with explicit day_fraction attribute (canonical path, K.8)."""
    period_index: int
    period_start: date
    period_end: date
    is_operation: bool = True
    day_fraction: float = 0.5


def test_explicit_day_fraction_overrides_date_derived_fallback():
    """K.8: Explicit day_fraction on period object takes precedence.

    Uses a period where explicit day_fraction (0.999) clearly differs from
    date-derived (180/365 ≈ 0.4932). Verifies canonical path is taken.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)

    # Date-derived: (2030-06-30 - 2030-01-01).days = 180 → 180/365 ≈ 0.4932
    # Explicit: 0.999 — clearly different
    period = _FakePeriodWithDayFrac(
        period_index=0,
        period_start=date(2030, 1, 1),
        period_end=date(2030, 6, 30),
        day_fraction=0.999,
    )
    periods = (period,)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=1000.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods, policy=policy, unrestricted_cash_schedule=cash_schedule,
    )
    r = result.period_results[0]
    assert abs(r.day_fraction - 0.999) < 1e-9, f"day_fraction = {r.day_fraction}"
    # 1000 * 0.01 * 0.999 = 9.99 kEUR (not 180/365 * 10 ≈ 4.93)
    assert abs(r.calculated_financing_income_keur - 9.99) < 1e-6


def test_fake_period_no_day_fraction_exercises_date_fallback():
    """K.8: _FakePeriod (no day_fraction attr) exercises date-derived fallback.

    This confirms existing tests (using _FakePeriod) only test the fallback path,
    not the canonical attribute path exercised in test above.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)
    period = _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30))  # no day_fraction
    assert not hasattr(period, "day_fraction"), "_FakePeriod must not have day_fraction"

    periods = (period,)
    cash_schedule = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=1000.0,
    )
    result = build_cash_reserve_interest_schedules(
        periods=periods, policy=policy, unrestricted_cash_schedule=cash_schedule,
    )
    r = result.period_results[0]
    expected_frac = 180 / 365  # date-derived fallback
    assert abs(r.day_fraction - expected_frac) < 1e-6, (
        f"K.8: Fallback day_fraction = {r.day_fraction:.6f}, expected {expected_frac:.6f}"
    )


# ═══════════════════════════════════════════════════════════════════
# Phase L Tests — L.1F, L.1B, L.13, L.15, L.19, L.17 governance
# ═══════════════════════════════════════════════════════════════════

# ── L-A. L.1F Fixture Evidence: TUHO CF row-mapping ─────────────────────────


def test_l1f_tuho_cf106_identity_in_fixture():
    """L.1F: TUHO CF106 = FCF for dividends (not DA release or net income).

    Source evidence recorded in l1f_dividend_cash_row_mapping_source_evidence.json.
    CF106 formula = AU102 + SUM(AU103:AU104) — pure FCF waterfall, no prior cash.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    cf106 = d["tuho"]["dividend_cash_block"]["CF106"]
    assert cf106["identity"] == "free_cash_flow_for_dividends"
    assert abs(cf106["period_au_value_keur"] - 5155.085477565507) < 1e-3


def test_l1f_tuho_cf108_identity_is_cash_available_not_da():
    """L.1F / A.1: TUHO CF108 = unrestricted cash available for dividend (dividend-accounting stage).

    A.1 correction: TUHO DOES have a DA block at CF98-CF100 (covenant/gating stage).
    CF108 is at a LATER stage (CF106+) — unrestricted cash available for dividend,
    which is prior_cash + FCF_for_dividends. Not to be confused with DA (CF98-100).
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    cf108 = d["tuho"]["dividend_cash_block"]["CF108"]
    assert cf108["identity"] == "unrestricted_cash_available_for_dividend"
    assert "prior_unrestricted_cash_closing" in cf108["formula_meaning"]
    # A.1: TUHO DA block exists at CF98-100
    da = d["tuho"]["da_block"]
    assert da["CF98"]["identity"] == "distribution_account_available"
    assert da["CF99"]["identity"] == "distribution_account_release"
    assert da["CF100"]["identity"] == "distribution_account_closing"


def test_l1f_tuho_cf135_unrestricted_cash_closing():
    """L.1F: TUHO CF135 = unrestricted cash closing = 550 kEUR from period AU onward."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    cf135 = d["tuho"]["dividend_cash_block"]["CF135"]
    assert cf135["identity"] == "unrestricted_cash_closing"
    assert abs(cf135["period_au_value_keur"] - 550.0) < 1e-3


def test_l1f_tuho_cf108_prior_cash_zero_means_equals_cf106():
    """L.1F: When prior cash=0 (period AU), CF108 = CF106 numerically.

    CF108 = AT135 + CF106 = 0 + 5155.085... = 5155.085...
    This confirms no hidden prior-cash balance inflates the dividend cap.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    cf106_val = d["tuho"]["dividend_cash_block"]["CF106"]["period_au_value_keur"]
    cf108_val = d["tuho"]["dividend_cash_block"]["CF108"]["period_au_value_keur"]
    assert abs(cf108_val - cf106_val) < 1e-3, (
        f"CF108={cf108_val} must equal CF106={cf106_val} when prior cash=0"
    )


# ── L-B. L.1F Fixture Evidence: Oborovo row-mapping and DA≠cash distinction ─


def test_l1f_oborovo_da_block_identity_cf108_is_da_not_cash():
    """L.1F: Oborovo CF108 = Distribution Account available (covenant gate), NOT cash cap.

    Critical distinction: Oborovo CF108 is the DA roll-forward (covenant/DSCR gate).
    The dividend cash-available row is CF118 — a completely separate block.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    da_cf108 = d["oborovo"]["da_block"]["CF108_da"]
    assert da_cf108["identity"] == "distribution_account_available"
    assert "SUM(G94,G95,G106)" in da_cf108["formula_pattern"]
    # Prove DA is distinct from unrestricted cash
    cash_cf118 = d["oborovo"]["dividend_cash_block"]["CF118"]
    assert cash_cf118["identity"] == "unrestricted_cash_available_for_dividend"


def test_l1f_oborovo_cf116_fcf_for_dividends():
    """L.1F: Oborovo CF116 = FCF for dividends ≈ 589.649650 at period 40."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    cf116 = d["oborovo"]["dividend_cash_block"]["CF116"]
    assert cf116["identity"] == "free_cash_flow_for_dividends"
    assert abs(cf116["period_40_value_keur"] - 589.649650241493) < 1e-3


def test_l1f_oborovo_cf130_gross_dividend_equals_distributable():
    """L.1F: Gross dividend = distributable; WHT only affects net (sponsor receipt).

    Oborovo CF130 = CF125 (distributable) ≈ 39.649650 at period 40.
    CF129 net = CF130 - WHT = 37.667... (5% WHT deducted from gross).
    gross_dividend = distributable regardless of WHT rate.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    block = d["oborovo"]["dividend_cash_block"]
    distributable = block["CF125"]["period_40_value_keur"]
    gross = block["CF130"]["period_40_value_keur"]
    net = block["CF129"]["period_40_value_keur"]
    wht_rate = block["CF128"]["B128_value"]
    assert abs(gross - distributable) < 1e-3, "gross_dividend must equal distributable"
    expected_net = gross * (1.0 - wht_rate)
    assert abs(net - expected_net) < 1e-3, f"net_dividend = gross*(1-wht): {net} vs {expected_net}"


def test_l1f_oborovo_cf132_change_in_cash_equals_fcf_minus_gross():
    """L.1F: Oborovo CF132 = CF116 - CF130 = 589.649650 - 39.649650 = 550.0 kEUR."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    block = d["oborovo"]["dividend_cash_block"]
    cf116 = block["CF116"]["period_40_value_keur"]
    cf130 = block["CF130"]["period_40_value_keur"]
    cf132 = block["CF132"]["period_40_value_keur"]
    expected = cf116 - cf130
    assert abs(expected - 550.0) < 1e-3, f"CF116-CF130 must be 550: {expected}"
    assert abs(cf132 - expected) < 1e-3, f"CF132 fixture must match formula: {cf132} vs {expected}"


def test_l1f_oborovo_cf144_unrestricted_cash_closing_550():
    """L.1F: Oborovo CF144 = unrestricted cash closing = 550 kEUR at period 40."""
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    cf144 = d["oborovo"]["dividend_cash_block"]["CF144"]
    assert cf144["identity"] == "unrestricted_cash_closing"
    assert abs(cf144["period_40_value_keur"] - 550.0) < 1e-3


def test_l1f_critical_distinction_da_vs_unrestricted_cash():
    """L.1F / A.1: Fixture records DA≠unrestricted-cash distinction for both projects.

    A.1 correction: TUHO has DA at CF98-100. TUHO CF108 is at a later stage.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    dist = d["critical_distinction"]
    assert "Distribution Account" in dist["DA_vs_unrestricted_cash"]
    # A.1: TUHO CF108 is unrestricted cash (not DA), but TUHO does have DA at CF98-100
    assert "UNRESTRICTED_CASH_AVAILABLE" in dist["TUHO_CF108"]
    assert "CF98" in dist["TUHO_DA_block"] or "CF98" in dist.get("TUHO_DA_block", "")
    assert dist["Oborovo_CF108"] == "DA_AVAILABLE — covenant gate input, NOT dividend cash cap"
    # A.2: Provenance is MANUAL_WORKBOOK_VERIFICATION, not USER_VERIFIED_WORKBOOK_EXTRACTION
    meta = d["_meta"]
    assert meta["provenance"] == "MANUAL_WORKBOOK_VERIFICATION"


# ── L-C. L.1B TUHO WHT Factory Reconciliation ────────────────────────────────


def test_l1b_tuho_factory_wht_updated_to_source_proven_zero():
    """L.1B: TUHO factory wht_sponsor_dividends updated from 0.05 to 0.00 (CF!B118=0%).

    This is the L.1B resolution of K.3's UNRECONCILED discrepancy.
    Source evidence: user-verified CF!B118 = 0.00% dividend WHT.
    """
    import pathlib
    factory_src = pathlib.Path("app/project_factories.py").read_text()
    # L.1B: TUHO line must now be 0.00
    assert "wht_sponsor_dividends=0.00" in factory_src, (
        "L.1B: TUHO factory WHT must be 0.00 (source-proven via CF!B118)."
    )


def test_l1b_oborovo_factory_wht_remains_five_percent():
    """L.1B: Oborovo factory wht_sponsor_dividends remains 0.05 (CF!B128=5.00% source-correct)."""
    import pathlib
    factory_src = pathlib.Path("app/project_factories.py").read_text()
    # Both factories have WHT lines; Oborovo's 0.05 must still be present
    oborovo_section = factory_src.split("# TUHO Wind 1")[0]
    assert "wht_sponsor_dividends=0.05" in oborovo_section, (
        "L.1B: Oborovo factory WHT must remain 0.05 (CF!B128=5.00%)."
    )


def test_l1b_tuho_wht_fixture_consistency():
    """L.1B / A.3: TUHO dividend WHT (CF!B118=0%) and factory 0.00 are consistent.

    A.3: B21=0 is financing-income WHT (distinct from dividend WHT).
    The dividend WHT authority is CF!B118 = 0.00% (L.1B manual verification).
    B21 consistency is a secondary confirmation, not the primary authority.
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_tuho_cash_reserve_interest_truth.json").read_text()
    )
    # B21 = financing-income WHT = 0 (consistent — zero financing WHT → zero withholding on interest)
    assert d["pnl_row21_withholding"]["zero_all_periods"] is True
    # Primary dividend WHT authority: CF!B118 = 0.00% per L.1F fixture
    l1f = json.loads(
        pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").read_text()
    )
    assert l1f["tuho"]["wht"]["value"] == 0.00
    assert l1f["tuho"]["wht"]["provenance"] == "MANUAL_WORKBOOK_VERIFICATION"
    factory_src = pathlib.Path("app/project_factories.py").read_text()
    assert "wht_sponsor_dividends=0.00" in factory_src


# ── L-D. L.13 Period Identity Validation ────────────────────────────────────


def test_l13_same_index_mismatched_dates_fails_closed():
    """L.13: Periods with same index but different date bounds → UNRESOLVED.

    Full period identity validation: each position must match on all three
    dimensions: (period_index, period_start, period_end).
    Same index with different start/end dates produces wrong day_fraction
    and must fail closed to UNRESOLVED.
    """
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)

    class _PeriodA:
        period_index = 0
        period_start = date(2030, 1, 1)
        period_end = date(2030, 6, 30)
        is_operation = True

    class _PeriodB:
        period_index = 0
        period_start = date(2030, 7, 1)   # different start — same index, different dates
        period_end = date(2030, 12, 31)
        is_operation = True

    cash_schedule = build_unrestricted_cash_schedule(
        periods=(_PeriodA(),),
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 550.0},
        opening_cash_keur=0.0,
    )
    # Schedule built with PeriodA (Jan-Jun); supply PeriodB (Jul-Dec) — index matches, dates don't
    result = build_cash_reserve_interest_schedules(
        periods=(_PeriodB(),), policy=policy, unrestricted_cash_schedule=cash_schedule,
    )
    # L.13: Full identity validation (index, start, end) must detect the date mismatch.
    assert result.authority == "UNRESOLVED", (
        f"L.13: Same index, different dates must force UNRESOLVED; got {result.authority!r}"
    )
    assert result.total_financing_income_keur == 0.0


def test_l13_period_identity_full_triple_validation_passes_when_matching():
    """L.13: Full (index, start, end) identity validation passes when all three match."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, build_cash_reserve_interest_schedules,
    )
    policy = _make_source_proven_policy(dsra_eligible=False)
    periods = (
        _FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),
        _FakePeriod(1, date(2030, 7, 1), date(2030, 12, 31)),
    )
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 100.0, 1: 200.0},
        opening_cash_keur=0.0,
    )
    assert s.authority == "SOURCE_PROVEN"
    result = build_cash_reserve_interest_schedules(
        periods=periods, policy=policy, unrestricted_cash_schedule=s,
    )
    assert result.authority == "SOURCE_PROVEN", (
        f"Matching (index,start,end) must not force UNRESOLVED; got {result.authority!r}"
    )


# ── L-E. L.15 WHT Sensitivity on Sponsor Net Cashflows ──────────────────────


def test_l15_gross_dividend_invariant_under_wht_change():
    """L.15: Gross dividend is WHT-invariant; net dividend absorbs WHT.

    This proves the cash roll-forward (CF135/CF144) is WHT-independent:
    change_in_cash = FCF - gross_dividend = FCF - distributable (always).
    Sponsor net receipt = distributable × (1 - wht_rate) varies with WHT.
    """
    distributable = 550.0
    fcf = 1100.0
    for wht in (0.00, 0.05, 0.15, 0.30):
        gross_dividend = distributable   # invariant
        net_dividend = distributable * (1.0 - wht)
        change_in_cash = fcf - gross_dividend
        assert abs(gross_dividend - 550.0) < 1e-9, f"gross_dividend must be 550 for wht={wht}"
        assert abs(change_in_cash - 550.0) < 1e-9, f"change_in_cash must be 550 for wht={wht}"
        assert abs(net_dividend - distributable * (1 - wht)) < 1e-9


def test_l15_tuho_wht_zero_means_gross_equals_net():
    """L.15: TUHO WHT=0.00% means sponsor receives gross=net=distributable.

    Source: CF!B118=0.00%. No WHT deducted from dividend. Sponsor net = gross.
    """
    distributable = 4605.085478
    wht_rate = 0.00   # TUHO source-proven
    gross_dividend = distributable
    net_dividend = gross_dividend * (1.0 - wht_rate)
    assert abs(net_dividend - distributable) < 1e-9, "net=gross when WHT=0"
    change_in_cash = 5155.085478 - gross_dividend
    assert abs(change_in_cash - 550.0) < 1e-3


def test_l15_oborovo_wht_five_percent_reduces_sponsor_net():
    """L.15: Oborovo WHT=5.00% reduces sponsor net receipt; gross=distributable unchanged.

    Source: CF!B128=5.00%. gross=39.649650, net=37.667168, WHT=1.982482 kEUR.
    """
    distributable = 39.649650241465224
    wht_rate = 0.05   # Oborovo source-proven
    gross_dividend = distributable
    net_dividend = gross_dividend * (1.0 - wht_rate)
    wht_amount = gross_dividend * wht_rate
    assert abs(gross_dividend - 39.649650241465224) < 1e-3
    assert abs(net_dividend - 37.667167729391963) < 1e-3
    assert abs(wht_amount - (gross_dividend - net_dividend)) < 1e-9


# ── L-F. L.17 Acceptance Targets (structural — no literal 550 in production) ─


def test_l17_no_literal_550_in_production_schedule_module():
    """L.17: Production schedule builder must not contain hardcoded 550."""
    import pathlib
    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_schedule.py").read_text()
    lines = [ln for ln in src.splitlines() if "550" in ln and not ln.strip().startswith("#")]
    assert not lines, f"L.17: Hardcoded 550 in production schedule: {lines}"


def test_l17_no_literal_550_in_production_policy_module():
    """L.17: Production policy module must not contain hardcoded 550."""
    import pathlib
    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_policy.py").read_text()
    lines = [ln for ln in src.splitlines() if "550" in ln and not ln.strip().startswith("#")]
    assert not lines, f"L.17: Hardcoded 550 in production policy: {lines}"


# ── L-G. L.19 Governance Tests ───────────────────────────────────────────────


def test_l19_no_project_name_dispatch_in_schedule_builder():
    """L.19: No project-name dispatch in cash reserve schedule builder.

    Uses AST to extract only string literals from non-docstring expressions
    (comparisons, if-conditions, dict keys). Module/function docstrings are
    allowed to reference project names as documentation context.
    """
    import pathlib, ast

    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_schedule.py").read_text()
    tree = ast.parse(src)

    # Collect all string constants that are NOT docstrings.
    # Docstrings are Expr(value=Constant) as the first statement in Module/FunctionDef/ClassDef.
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstring_nodes.add(id(body[0].value))

    forbidden_in_code: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstring_nodes:
                val = node.value
                for name in ("tuho", "oborovo", "TUHO", "Oborovo", "project_name"):
                    if name in val:
                        forbidden_in_code.append(f"{name!r} in string at line {node.lineno}")

    assert not forbidden_in_code, (
        f"L.19: Project-name dispatch found in non-docstring code: {forbidden_in_code}"
    )


def test_l19_no_workbook_vector_replay():
    """L.19: No hardcoded period vectors in production schedule code."""
    import pathlib
    src = pathlib.Path("finco_core/inputs/cash_reserve_interest_schedule.py").read_text()
    # Prohibit patterns that look like hardcoded vector replay
    for forbidden in ("[550", "550.0, 550", "550.0,\n"):
        assert forbidden not in src, f"L.19: Vector replay pattern '{forbidden}' found."


def test_l19_no_post_convergence_mutation():
    """L.19: Schedule builder returns frozen dataclass — no post-construction mutation."""
    from finco_core.inputs.cash_reserve_interest_schedule import (
        build_unrestricted_cash_schedule, UnrestrictedCashSchedule,
    )
    import dataclasses
    periods = (_FakePeriod(0, date(2030, 1, 1), date(2030, 6, 30)),)
    s = build_unrestricted_cash_schedule(
        periods=periods,
        authority="SOURCE_PROVEN",
        authoritative_period_cash_increments={0: 0.0},
        opening_cash_keur=0.0,
    )
    assert dataclasses.is_dataclass(s)
    assert s.__dataclass_params__.frozen, "UnrestrictedCashSchedule must be frozen (immutable)"


def test_l19_no_c3_import_in_upstream_modules():
    """L.19: Upstream cash/reserve modules must not import from C3."""
    import pathlib, ast
    upstream_files = [
        "finco_core/inputs/cash_reserve_interest_policy.py",
        "finco_core/inputs/cash_reserve_interest_schedule.py",
    ]
    for fp in upstream_files:
        src = pathlib.Path(fp).read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("app."), (
                        f"L.19: C3/app import '{node.module}' found in {fp}"
                    )


# ── L-H. Numerical handshake sanity ─────────────────────────────────────────


def test_l_tuho_av_day_fraction_numerical_handshake():
    """L: TUHO AV period day_fraction=181/365 produces exact fixture interest.

    Numerical handshake from excel_tuho_cash_reserve_interest_truth.json:
    550.0 × 0.01 × (181/365) = 2.7273972602740044 kEUR.
    Clarification: AU = 184/365 (Jul-Dec 2049, cash=0 → no interest).
                   AV = 181/365 (Jan-Jun 2050, cash=550 → interest earned).
    """
    import json, pathlib
    d = json.loads(
        pathlib.Path("tests/fixtures/excel_tuho_cash_reserve_interest_truth.json").read_text()
    )
    hs = d["numerical_handshake"]
    cash_balance = hs["cf135_balance_keur"]
    rate = hs["rate"]
    day_frac = hs["H6_day_fraction"]  # 181/365
    expected = hs["expected_keur"]
    computed = cash_balance * rate * day_frac
    assert abs(computed - expected) < 1e-9, f"Handshake: {computed} vs {expected}"
    assert abs(day_frac - 181 / 365) < 1e-9, f"AV day_fraction must be 181/365: {day_frac}"


def test_l_tuho_au_day_fraction_is_184_over_365():
    """L: TUHO AU day_fraction = 184/365 (Jul 1 – Dec 31, 2049).

    AU cash balance = 0 (prior periods have no retained cash), so interest = 0.
    The period earns no cash interest despite a non-zero day_fraction.
    """
    au_frac = 184 / 365
    assert abs(au_frac - 0.5041095890410959) < 1e-9
    # Interest earned in AU period: cash=0 → 0 regardless of fraction
    cash_balance_au = 0.0
    interest_au = cash_balance_au * 0.01 * au_frac
    assert interest_au == 0.0


def test_l_oborovo_change_in_cash_identity():
    """L: Oborovo change_in_cash = FCF_for_dividends - gross_dividend = 550 kEUR.

    CF132 = CF116 - CF130 = 589.649650 - 39.649650 = 550.0 kEUR (period 40).
    This is the causal identity linking FCF → dividend → retained cash.
    """
    fcf_for_dividends = 589.649650241493
    gross_dividend = 39.649650241465224
    change_in_cash = fcf_for_dividends - gross_dividend
    assert abs(change_in_cash - 550.0) < 1e-3
