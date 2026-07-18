"""financial_engine.tax.engine — Phase 2B annual tax calculation engine.

Pure function. No imports from app, finco_core or any framework.

Calculation order:
  1. Aggregate period operating results into annual TaxYearCalculationBasis.
  2. Per tax year: annual ATAD → annual taxable income → annual FIFO LCF → annual CIT.
  3. Allocate cash tax payments to model periods (TAX_YEAR_LAST_PERIOD timing).
  4. Compute canonical CFADS = EBITDA - cash_tax_paid per period.

Taxable income formula (CORRECT):
    taxable_income_before_lcf = EBITDA - tax_dep - deductible_interest
                                + other_fiscal_reintegration

  deductible_interest is the ATAD-limited amount (gross - disallowed).
  disallowed_interest is NOT added back separately — it simply is not deducted.

  Example:
    EBITDA = 10 000, tax_dep = 2 000, gross_interest = 4 000,
    deductible_interest = 3 000, disallowed = 1 000, other_reint = 0
    → taxable = 10 000 - 2 000 - 3 000 + 0 = 5 000   ✓
"""
from __future__ import annotations

from collections import defaultdict

from financial_engine.inputs import TaxCalculationInput, PeriodInterestInput
from financial_engine.policies.tax import CashTaxTiming, TaxPolicy
from financial_engine.tax.atad import calculate_annual_atad, allocate_atad_to_periods
from financial_engine.tax.loss_ledger import run_annual_fifo_ledger
from financial_engine.tax.models import (
    PeriodCashTaxResult,
    TaxAndCfadsResult,
    TaxAnnualResult,
    TaxYearCalculationBasis,
)


def _build_interest_map(
    period_interest: tuple[PeriodInterestInput, ...],
) -> dict[int, PeriodInterestInput]:
    return {pi.period_index: pi for pi in period_interest}


def _build_adj_map(period_adjustments: tuple) -> dict[int, float]:
    return {adj.period_index: adj.other_fiscal_reintegration_keur for adj in period_adjustments}


def _aggregate_tax_years(
    periods: tuple,  # tuple[OperatingPeriodResult]
    interest_map: dict[int, PeriodInterestInput],
    adj_map: dict[int, float],
) -> tuple[list[TaxYearCalculationBasis], dict[int, tuple[int, float, float, float]]]:
    """Aggregate period results into per-tax-year bases.

    Returns:
        bases : list of TaxYearCalculationBasis, one per unique (tax_year, construction_group)
        per_period_meta : dict period_index → (tax_year, interest, adj, period_in_year)
    """
    # Group periods by tax_year (year_index rounded to nearest int, 0-based)
    # year_index from PeriodEngine is 1-based for operating, 0 for construction
    # We use year_index directly as the tax-year grouping key
    year_to_period_indices: dict[float, list[int]] = defaultdict(list)
    year_to_ebitda: dict[float, float] = defaultdict(float)
    year_to_tax_dep: dict[float, float] = defaultdict(float)
    year_to_interest: dict[float, float] = defaultdict(float)
    year_to_reint: dict[float, float] = defaultdict(float)
    year_to_per_period_interest: dict[float, list[float]] = defaultdict(list)
    year_to_per_period_pin: dict[float, list[float]] = defaultdict(list)

    for p in periods:
        idx = p.period_index  # type: ignore[attr-defined]
        yi = p.year_index  # type: ignore[attr-defined]
        pi_obj = interest_map.get(idx)
        gross_int = pi_obj.total_interest_keur if pi_obj else 0.0
        reint = adj_map.get(idx, 0.0)

        year_to_period_indices[yi].append(idx)
        year_to_ebitda[yi] += p.ebitda_keur  # type: ignore[attr-defined]
        year_to_tax_dep[yi] += p.tax_depreciation_keur  # type: ignore[attr-defined]
        year_to_interest[yi] += gross_int
        year_to_reint[yi] += reint
        year_to_per_period_interest[yi].append(gross_int)
        year_to_per_period_pin[yi].append(p.period_in_year)  # type: ignore[attr-defined]

    # Build bases in chronological order
    sorted_years = sorted(year_to_period_indices.keys())
    bases: list[TaxYearCalculationBasis] = []
    # Tax year index: construction year gets tax_year=-1 (if year_index=0), else year_index-1 (0-based)
    for yi in sorted_years:
        tax_year = int(yi) - 1 if yi > 0 else -1
        bases.append(TaxYearCalculationBasis(
            tax_year=tax_year,
            period_indices=tuple(year_to_period_indices[yi]),
            ebitda_keur=year_to_ebitda[yi],
            tax_depreciation_keur=year_to_tax_dep[yi],
            total_interest_keur=year_to_interest[yi],
            other_fiscal_reintegration_keur=year_to_reint[yi],
        ))

    # Build per-period metadata: period_index → (tax_year, gross_interest, reint, period_in_year)
    per_period_meta: dict[int, tuple[int, float, float, float]] = {}
    for yi in sorted_years:
        tax_year = int(yi) - 1 if yi > 0 else -1
        for idx, gross_int, reint_val, pin in zip(
            year_to_period_indices[yi],
            year_to_per_period_interest[yi],
            [adj_map.get(i, 0.0) for i in year_to_period_indices[yi]],
            year_to_per_period_pin[yi],
        ):
            per_period_meta[idx] = (tax_year, gross_int, reint_val, pin)

    return bases, per_period_meta


def calculate_tax(
    periods: tuple,  # tuple[OperatingPeriodResult]
    tax_input: TaxCalculationInput,
) -> TaxAndCfadsResult:
    """Calculate Phase 2B annual tax and canonical CFADS.

    Parameters
    ----------
    periods : OperatingPeriodResult tuple from run_operating_model()
    tax_input : TaxCalculationInput with policy, interest, and adjustments

    Returns
    -------
    TaxAndCfadsResult with annual_results, period_results, terminal_unpaid_tax_keur
    """
    policy: TaxPolicy = tax_input.policy  # type: ignore[assignment]
    interest_map = _build_interest_map(tax_input.period_interest)
    adj_map = _build_adj_map(tax_input.period_adjustments)

    # Step 1: Aggregate into annual bases
    bases, per_period_meta = _aggregate_tax_years(periods, interest_map, adj_map)

    # Step 2: Annual ATAD + taxable income + LCF + CIT
    # Collect per-period interests in the order periods appear in each basis
    atad_results: list = []
    for basis in bases:
        period_interests = tuple(
            (interest_map.get(idx).total_interest_keur if interest_map.get(idx) else 0.0)
            for idx in basis.period_indices
        )
        annual_atad = calculate_annual_atad(basis, policy)
        annual_atad = allocate_atad_to_periods(annual_atad, period_interests)
        atad_results.append(annual_atad)

    # Build per-year taxable income before LCF
    taxable_before_lcf: list[float] = []
    for basis, atad in zip(bases, atad_results):
        ti = (
            basis.ebitda_keur
            - basis.tax_depreciation_keur
            - atad.deductible_interest_keur
            + basis.other_fiscal_reintegration_keur
        )
        taxable_before_lcf.append(ti)

    # Step 3: Annual LCF
    # Only run LCF over years with year_index > 0 (operating years)
    # Construction year (year_index=0, tax_year=-1) participates in LCF with losses
    tax_year_indices = tuple(b.tax_year for b in bases)
    lcf_entries = run_annual_fifo_ledger(
        taxable_income_before_lcf=tuple(taxable_before_lcf),
        tax_year_indices=tax_year_indices,
        opening_inputs=tax_input.opening_loss_vintages,
        loss_carryforward_years=policy.loss_carryforward_years,
    )

    # Step 4: Annual CIT
    annual_results: list[TaxAnnualResult] = []
    for basis, atad, ti_before, lcf in zip(
        bases, atad_results, taxable_before_lcf, lcf_entries
    ):
        ti_after = lcf.taxable_income_after_lcf_keur
        liability = policy.corporate_rate * max(0.0, ti_after)
        annual_results.append(TaxAnnualResult(
            tax_year=basis.tax_year,
            period_indices=basis.period_indices,
            total_interest_keur=atad.total_interest_keur,
            deduction_capacity_keur=atad.deduction_capacity_keur,
            deductible_interest_keur=atad.deductible_interest_keur,
            disallowed_interest_keur=atad.disallowed_interest_keur,
            atad_binding_rule=atad.binding_rule,
            ebitda_keur=basis.ebitda_keur,
            tax_depreciation_keur=basis.tax_depreciation_keur,
            other_fiscal_reintegration_keur=basis.other_fiscal_reintegration_keur,
            taxable_income_before_lcf_keur=ti_before,
            loss_opening_keur=lcf.opening_loss_keur,
            loss_expired_keur=lcf.loss_expired_keur,
            loss_used_keur=lcf.loss_used_keur,
            loss_generated_keur=lcf.loss_generated_keur,
            loss_closing_keur=lcf.closing_loss_keur,
            taxable_income_after_lcf_keur=ti_after,
            current_tax_liability_keur=liability,
            period_atad_deductible=atad.period_deductible_keur,
            period_atad_disallowed=atad.period_disallowed_keur,
        ))

    # Step 5: Allocate cash tax payments to periods
    # Build index: period_index → annual_result
    period_to_annual: dict[int, TaxAnnualResult] = {}
    for ar in annual_results:
        for idx in ar.period_indices:
            period_to_annual[idx] = ar

    # Build map: annual_result.tax_year → payment_period_index
    # For TAX_YEAR_LAST_PERIOD: last period of the tax year, shifted by lag
    # Build map: tax_year → last_period_in_year
    tax_year_to_last_period: dict[int, int] = {}
    for ar in annual_results:
        if ar.period_indices:
            tax_year_to_last_period[ar.tax_year] = ar.period_indices[-1]

    all_period_indices = sorted(p.period_index for p in periods)  # type: ignore[attr-defined]
    max_period_idx = max(all_period_indices) if all_period_indices else -1

    # Payment period: last_period_of_year + lag
    terminal_unpaid = 0.0
    tax_year_cash_period: dict[int, int | None] = {}
    for ar in annual_results:
        if not ar.period_indices:
            continue
        base_payment_period = ar.period_indices[-1]
        if policy.cash_tax_timing == CashTaxTiming.TAX_YEAR_LAST_PERIOD:
            payment_period = base_payment_period + policy.cash_tax_payment_lag_periods
        else:
            # SAME_PERIOD: accrue in the period of liability (H2 for last-period, prorated)
            payment_period = base_payment_period
        if payment_period > max_period_idx:
            terminal_unpaid += ar.current_tax_liability_keur
            tax_year_cash_period[ar.tax_year] = None
        else:
            tax_year_cash_period[ar.tax_year] = payment_period

    # Cash tax per model period
    cash_tax_by_period: dict[int, float] = {idx: 0.0 for idx in all_period_indices}
    for ar in annual_results:
        payment_period = tax_year_cash_period.get(ar.tax_year)
        if payment_period is not None:
            cash_tax_by_period[payment_period] = (
                cash_tax_by_period[payment_period] + ar.current_tax_liability_keur
            )

    # Step 6: Build per-period results
    # Build ATAD per-period lookup from the period_indices in each annual result
    period_ded_lookup: dict[int, float] = {}
    period_dis_lookup: dict[int, float] = {}
    for ar in annual_results:
        for idx, ded, dis in zip(
            ar.period_indices,
            ar.period_atad_deductible,  # type: ignore[attr-defined]
            ar.period_atad_disallowed,  # type: ignore[attr-defined]
        ):
            period_ded_lookup[idx] = ded
            period_dis_lookup[idx] = dis

    period_results: list[PeriodCashTaxResult] = []
    for p in periods:  # type: ignore[assignment]
        idx = p.period_index  # type: ignore[attr-defined]
        ar = period_to_annual[idx]
        n_periods_in_year = len(ar.period_indices)
        # Prorated accrual share: annual liability / number of periods
        cit_share = ar.current_tax_liability_keur / n_periods_in_year if n_periods_in_year else 0.0
        ti_share = ar.taxable_income_before_lcf_keur / n_periods_in_year if n_periods_in_year else 0.0
        ebitda = p.ebitda_keur  # type: ignore[attr-defined]
        cash_tax = cash_tax_by_period.get(idx, 0.0)
        cfads = ebitda - cash_tax
        period_results.append(PeriodCashTaxResult(
            period_index=idx,
            is_operation=p.is_operation,  # type: ignore[attr-defined]
            ebitda_keur=ebitda,
            tax_year=ar.tax_year,
            deductible_interest_keur=period_ded_lookup.get(idx, 0.0),
            disallowed_interest_keur=period_dis_lookup.get(idx, 0.0),
            other_fiscal_reintegration_keur=adj_map.get(idx, 0.0),
            taxable_income_before_lcf_share_keur=ti_share,
            cit_accrual_share_keur=cit_share,
            cash_tax_keur=cash_tax,
            cfads_keur=cfads,
        ))

    return TaxAndCfadsResult(
        annual_results=tuple(annual_results),
        period_results=tuple(period_results),
        terminal_unpaid_tax_keur=terminal_unpaid,
    )
