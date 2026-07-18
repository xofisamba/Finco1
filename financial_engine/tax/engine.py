"""financial_engine.tax.engine — Phase 2B tax calculation engine.

Pure function. No imports from app, finco_core or any framework.

Calculation order per period:
  1. Gross interest from exogenous PeriodInterestInput
  2. ATAD: compute deductible interest and disallowed addback
  3. Taxable income before losses = EBITDA - tax_dep - deductible_interest
                                   + disallowed_addback + other_reintegration
  4. FIFO loss ledger → taxable profit after losses
  5. CIT accrual = corporate_rate × max(0, taxable_profit)
  6. Cash tax = CIT accrual for H2 periods (TAX_YEAR_LAST_PERIOD timing),
               0 for H1 periods
"""
from __future__ import annotations

from financial_engine.policies.tax import CashTaxTiming, TaxPolicy
from financial_engine.tax.atad import calculate_atad_schedule
from financial_engine.tax.loss_ledger import run_fifo_loss_ledger
from financial_engine.tax.models import (
    PeriodTaxResult,
    TaxLossVintage,
    TaxSchedules,
)


def _build_loss_vintages(
    opening_vintages_raw: tuple[object, ...],
) -> tuple[TaxLossVintage, ...]:
    """Convert OpeningTaxLossVintageInput to internal TaxLossVintage."""
    result = []
    for v in opening_vintages_raw:
        result.append(TaxLossVintage(
            amount_keur=v.amount_keur,  # type: ignore[attr-defined]
            periods_remaining=v.periods_remaining,  # type: ignore[attr-defined]
            source_period_index=None,
            source_label=getattr(v, "source_label", "opening"),
        ))
    return tuple(result)


def calculate_tax(
    periods: tuple[object, ...],  # tuple[OperatingPeriodResult]
    tax_input: object,            # TaxCalculationInput
) -> tuple[PeriodTaxResult, ...]:
    """Calculate full tax schedule for all model periods.

    Parameters
    ----------
    periods : OperatingPeriodResult tuple from the Phase 2A orchestrator
    tax_input : TaxCalculationInput

    Returns
    -------
    tuple[PeriodTaxResult] — one entry per model period
    """
    policy: TaxPolicy = tax_input.policy  # type: ignore[attr-defined]
    n = len(periods)

    # Build interest lookup by period index
    interest_by_idx: dict[int, float] = {}
    for pi in tax_input.period_interest:  # type: ignore[attr-defined]
        interest_by_idx[pi.period_index] = pi.gross_interest_expense_keur

    # Build fiscal adjustment lookup
    adj_by_idx: dict[int, float] = {}
    for adj in tax_input.period_adjustments:  # type: ignore[attr-defined]
        adj_by_idx[adj.period_index] = adj.other_fiscal_reintegration_keur

    # Collect per-period inputs
    ebitda_arr = tuple(p.ebitda_keur for p in periods)  # type: ignore[attr-defined]
    tax_dep_arr = tuple(p.tax_depreciation_keur for p in periods)  # type: ignore[attr-defined]
    period_in_year_arr = tuple(p.period_in_year for p in periods)  # type: ignore[attr-defined]
    gross_interest_arr = tuple(interest_by_idx.get(i, 0.0) for i in range(n))
    reintegration_arr = tuple(adj_by_idx.get(i, 0.0) for i in range(n))

    # Step 1: ATAD
    if policy.atad_enabled:
        atad_results = calculate_atad_schedule(
            ebitda_by_period=ebitda_arr,
            gross_interest_by_period=gross_interest_arr,
            period_in_year_by_period=period_in_year_arr,
            atad_ebitda_limit=policy.atad_ebitda_limit,
            atad_de_minimis_threshold_keur_annual=policy.atad_de_minimis_threshold_keur_annual,
        )
        deductible_interest_arr = tuple(r.deductible_interest_keur for r in atad_results)
        disallowed_addback_arr = tuple(r.disallowed_addback_keur for r in atad_results)
    else:
        deductible_interest_arr = gross_interest_arr
        disallowed_addback_arr = tuple(0.0 for _ in range(n))

    # Step 2: taxable income before losses
    taxable_before_arr = tuple(
        ebitda - tax_dep - ded_int + disallowed + reint
        for ebitda, tax_dep, ded_int, disallowed, reint in zip(
            ebitda_arr,
            tax_dep_arr,
            deductible_interest_arr,
            disallowed_addback_arr,
            reintegration_arr,
        )
    )

    # Step 3: FIFO loss ledger
    opening_vintages = _build_loss_vintages(
        tax_input.opening_loss_vintages  # type: ignore[attr-defined]
    )
    ledger_periods = run_fifo_loss_ledger(
        taxable_income_before_losses=taxable_before_arr,
        opening_vintages=opening_vintages,
        loss_carryforward_years=policy.loss_carryforward_years,
        periods_per_tax_year=policy.periods_per_tax_year,
        expire_losses_before_use=policy.expire_losses_before_use,
    )

    # Step 4: CIT accrual and cash tax
    results: list[PeriodTaxResult] = []
    for i, (period, ledger) in enumerate(zip(periods, ledger_periods)):
        taxable_profit = ledger.taxable_profit_after_losses_keur
        cit_accrual = policy.corporate_rate * max(0.0, taxable_profit)

        is_h1 = (period.period_in_year <= 1.0)  # type: ignore[attr-defined]
        if policy.cash_tax_timing == CashTaxTiming.TAX_YEAR_LAST_PERIOD:
            # Cash tax crystallises in H2 (or last period of the tax year)
            # In H2 we pay the full-year accrual; track H1 accrual to carry
            # Here simplified: cash_tax = cit_accrual in H2, 0 in H1
            cash_tax = 0.0 if is_h1 else cit_accrual
        else:
            cash_tax = cit_accrual

        results.append(PeriodTaxResult(
            period_index=i,
            is_operation=period.is_operation,  # type: ignore[attr-defined]
            ebitda_keur=ebitda_arr[i],
            tax_depreciation_keur=tax_dep_arr[i],
            gross_interest_keur=gross_interest_arr[i],
            deductible_interest_keur=deductible_interest_arr[i],
            disallowed_addback_keur=disallowed_addback_arr[i],
            other_fiscal_reintegration_keur=reintegration_arr[i],
            taxable_income_before_losses_keur=taxable_before_arr[i],
            loss_opening_keur=ledger.opening_loss_keur,
            loss_used_keur=ledger.loss_used_keur,
            loss_generated_keur=ledger.loss_generated_keur,
            loss_expired_keur=ledger.loss_expired_keur,
            loss_closing_keur=ledger.closing_loss_keur,
            taxable_profit_after_losses_keur=taxable_profit,
            cit_accrual_keur=cit_accrual,
            cash_tax_keur=cash_tax,
        ))

    return tuple(results)


def build_tax_schedules(period_results: tuple[PeriodTaxResult, ...]) -> TaxSchedules:
    """Assemble parallel array schedules from per-period tax results."""
    def tup(fn: object) -> tuple[float, ...]:
        return tuple(fn(r) for r in period_results)  # type: ignore[operator]

    return TaxSchedules(
        period_indices=tuple(r.period_index for r in period_results),
        taxable_profit_keur=tup(lambda r: r.ebitda_keur - r.tax_depreciation_keur - r.deductible_interest_keur + r.disallowed_addback_keur + r.other_fiscal_reintegration_keur),
        taxable_income_before_losses_keur=tup(lambda r: r.taxable_income_before_losses_keur),
        taxable_profit_after_losses_keur=tup(lambda r: r.taxable_profit_after_losses_keur),
        tax_keur=tup(lambda r: r.cit_accrual_keur),
        corporate_tax_cash_keur=tup(lambda r: r.cash_tax_keur),
        cit_accrual_keur=tup(lambda r: r.cit_accrual_keur),
        tax_loss_opening_keur=tup(lambda r: r.loss_opening_keur),
        tax_loss_closing_keur=tup(lambda r: r.loss_closing_keur),
        tax_loss_used_keur=tup(lambda r: r.loss_used_keur),
        fiscal_reintegration_keur=tup(lambda r: r.disallowed_addback_keur + r.other_fiscal_reintegration_keur),
        tax_depreciation_audit_keur=tup(lambda r: r.tax_depreciation_keur),
        cf_after_tax_keur=tup(lambda r: r.ebitda_keur - r.cit_accrual_keur),
        cash_tax_current_period_keur=tup(lambda r: r.cash_tax_keur),
        cash_tax_bridge_reconciliation_keur=tup(lambda r: r.cit_accrual_keur - r.cash_tax_keur),
    )
