"""financial_engine.tax.engine — Phase 2B annual tax calculation engine.

Pure function.  No imports from app, finco_core or any framework.

Calculation order
-----------------
1.  Split every model period into calendar-year fragments (crosses 31 Dec).
2.  Aggregate fragments → ``TaxYearCalculationBasis`` per calendar year.
3.  Per tax year: annual ATAD → annual taxable income → annual FIFO LCF → CIT.
4.  Allocate cash tax payments to periods.

    * ``TAX_YEAR_LAST_PERIOD``: full annual CIT in the last period of the year
      (determined by the latest fragment end-date) plus the configured lag.
    * ``SAME_PERIOD``: each period pays its own prorated CIT accrual share.

5.  Record ``terminal_unpaid_tax_keur`` for liabilities outside the horizon.

Taxable income formula (correct — no double ATAD addback)::

    taxable_income_before_lcf = EBITDA
                                − tax_depreciation
                                − deductible_interest   ← ATAD-limited
                                + other_fiscal_reintegration

Example:
    EBITDA=10 000, tax_dep=2 000, gross_interest=4 000,
    deductible_interest=3 000 → taxable = 10 000 − 2 000 − 3 000 = 5 000  ✓
    (disallowed_interest is NOT added back separately)
"""
from __future__ import annotations

from financial_engine.inputs import TaxCalculationInput, PeriodInterestInput
from financial_engine.policies.tax import CashTaxTiming, TaxPolicy
from financial_engine.tax.atad import calculate_annual_atad, allocate_atad_to_periods
from financial_engine.tax.loss_ledger import run_annual_fifo_ledger
from financial_engine.tax.models import (
    PeriodCashTaxResult,
    TaxAndCfadsResult,
    TaxAnnualResult,
)
from financial_engine.tax.tax_year import build_tax_year_bases


def _build_interest_map(
    period_interest: tuple[PeriodInterestInput, ...],
) -> dict[int, PeriodInterestInput]:
    return {pi.period_index: pi for pi in period_interest}


def _build_adj_map(period_adjustments: tuple) -> dict[int, float]:
    return {
        adj.period_index: adj.other_fiscal_reintegration_keur
        for adj in period_adjustments
    }


def calculate_tax(
    periods: tuple,             # tuple[OperatingPeriodResult]
    tax_input: TaxCalculationInput,
) -> TaxAndCfadsResult:
    """Calculate Phase 2B annual tax and return period cash-tax assignments.

    Parameters
    ----------
    periods:
        OperatingPeriodResult tuple from ``run_operating_model()``.
    tax_input:
        TaxCalculationInput with policy, interest schedule and adjustments.

    Returns
    -------
    TaxAndCfadsResult containing per-annual and per-period results plus
    ``terminal_unpaid_tax_keur`` for liabilities outside the model horizon.
    """
    policy: TaxPolicy = tax_input.policy  # type: ignore[assignment]
    interest_map = _build_interest_map(tax_input.period_interest)
    adj_map = _build_adj_map(tax_input.period_adjustments)

    # ── Step 1-2: Build calendar-year bases ───────────────────────────────────
    bases = build_tax_year_bases(periods, interest_map, adj_map)

    # ── Step 3: ATAD + taxable income + LCF + CIT per tax year ───────────────
    atad_results = []
    for basis in bases:
        # Per-period interest in the order the fragments appear within the year
        # (chronological by source period index).
        seen: dict[int, float] = {}
        for frag in basis.fragments:
            pi_obj = interest_map.get(frag.source_period_index)
            gross = pi_obj.total_interest_keur if pi_obj else 0.0
            if frag.source_period_index not in seen:
                seen[frag.source_period_index] = 0.0
            seen[frag.source_period_index] += gross * frag.allocation_fraction

        period_interests: tuple[float, ...] = tuple(
            seen.get(idx, 0.0) for idx in basis.period_indices
        )

        annual_atad = calculate_annual_atad(basis, policy)
        annual_atad = allocate_atad_to_periods(annual_atad, period_interests)
        atad_results.append(annual_atad)

    # Annual taxable income before LCF
    taxable_before_lcf = [
        (
            basis.ebitda_keur
            - basis.tax_depreciation_keur
            - atad.deductible_interest_keur
            + basis.other_fiscal_reintegration_keur
        )
        for basis, atad in zip(bases, atad_results)
    ]

    # Annual FIFO LCF
    tax_year_indices = tuple(b.tax_year for b in bases)
    lcf_entries = run_annual_fifo_ledger(
        taxable_income_before_lcf=tuple(taxable_before_lcf),
        tax_year_indices=tax_year_indices,
        opening_inputs=tax_input.opening_loss_vintages,
        loss_carryforward_years=policy.loss_carryforward_years,
    )

    # Annual CIT + build TaxAnnualResult
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
            loss_opening_keur=lcf.opening_loss_pre_expiry_keur,
            loss_expired_keur=lcf.loss_expired_keur,
            loss_used_keur=lcf.loss_used_keur,
            loss_generated_keur=lcf.loss_generated_keur,
            loss_closing_keur=lcf.closing_loss_keur,
            taxable_income_after_lcf_keur=ti_after,
            ledger_entry=lcf,
            current_tax_liability_keur=liability,
            period_atad_deductible=atad.period_deductible_keur,
            period_atad_disallowed=atad.period_disallowed_keur,
        ))

    # ── Step 4: Allocate cash tax to periods ──────────────────────────────────
    # Build lookup period_index → annual_result
    period_to_annual: dict[int, TaxAnnualResult] = {}
    for ar in annual_results:
        for idx in ar.period_indices:
            period_to_annual[idx] = ar

    all_period_indices = sorted(p.period_index for p in periods)  # type: ignore[attr-defined]
    max_period_idx = max(all_period_indices) if all_period_indices else -1

    terminal_unpaid = 0.0
    tax_year_cash_period: dict[int, int | None] = {}

    # Build map from tax_year → basis (for payment_period_index lookup)
    basis_by_tax_year: dict[int, object] = {b.tax_year: b for b in bases}

    for ar in annual_results:
        if not ar.period_indices:
            continue

        if policy.cash_tax_timing == CashTaxTiming.TAX_YEAR_LAST_PERIOD:
            basis = basis_by_tax_year.get(ar.tax_year)
            base = (
                basis.payment_period_index  # type: ignore[union-attr]
                if basis is not None
                else ar.period_indices[-1]
            )
            payment_period = base + policy.cash_tax_payment_lag_periods
            if payment_period > max_period_idx:
                terminal_unpaid += ar.current_tax_liability_keur
                tax_year_cash_period[ar.tax_year] = None
            else:
                tax_year_cash_period[ar.tax_year] = payment_period
        else:
            # SAME_PERIOD: handled per-period below; mark sentinel
            tax_year_cash_period[ar.tax_year] = -1  # sentinel = distribute

    # Build cash_tax_by_period
    cash_tax_by_period: dict[int, float] = {idx: 0.0 for idx in all_period_indices}

    if policy.cash_tax_timing == CashTaxTiming.TAX_YEAR_LAST_PERIOD:
        for ar in annual_results:
            payment_period = tax_year_cash_period.get(ar.tax_year)
            if payment_period is not None:
                cash_tax_by_period[payment_period] = (
                    cash_tax_by_period[payment_period] + ar.current_tax_liability_keur
                )
    else:
        # SAME_PERIOD: each period pays its own prorated CIT accrual share
        for ar in annual_results:
            n_in_year = len(ar.period_indices)
            if n_in_year == 0:
                continue
            share = ar.current_tax_liability_keur / n_in_year
            for idx in ar.period_indices:
                cash_tax_by_period[idx] = cash_tax_by_period.get(idx, 0.0) + share

    # ── Step 5: Build per-period results ──────────────────────────────────────
    period_ded_lookup: dict[int, float] = {}
    period_dis_lookup: dict[int, float] = {}
    for ar in annual_results:
        for idx, ded, dis in zip(
            ar.period_indices,
            ar.period_atad_deductible,
            ar.period_atad_disallowed,
        ):
            period_ded_lookup[idx] = ded
            period_dis_lookup[idx] = dis

    period_results: list[PeriodCashTaxResult] = []
    for p in periods:
        idx = p.period_index   # type: ignore[attr-defined]
        ar = period_to_annual[idx]
        n_in_year = len(ar.period_indices)
        cit_share = ar.current_tax_liability_keur / n_in_year if n_in_year else 0.0
        ti_share = ar.taxable_income_before_lcf_keur / n_in_year if n_in_year else 0.0
        period_results.append(PeriodCashTaxResult(
            period_index=idx,
            is_operation=p.is_operation,    # type: ignore[attr-defined]
            ebitda_keur=p.ebitda_keur,      # type: ignore[attr-defined]
            tax_year=ar.tax_year,
            deductible_interest_keur=period_ded_lookup.get(idx, 0.0),
            disallowed_interest_keur=period_dis_lookup.get(idx, 0.0),
            other_fiscal_reintegration_keur=adj_map.get(idx, 0.0),
            taxable_income_before_lcf_share_keur=ti_share,
            cit_accrual_share_keur=cit_share,
            cash_tax_keur=cash_tax_by_period.get(idx, 0.0),
        ))

    return TaxAndCfadsResult(
        annual_results=tuple(annual_results),
        period_results=tuple(period_results),
        terminal_unpaid_tax_keur=terminal_unpaid,
    )
