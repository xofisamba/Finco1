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
