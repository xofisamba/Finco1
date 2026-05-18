"""Offline P&L assembly from existing waterfall period outputs."""

from __future__ import annotations

from domain.depreciation import (
    AssetClassConfig,
    DepreciationLedgerInput,
    DepreciationPolicy,
    build_depreciation_ledger,
)
from domain.financial_statements.excel_mapping import PNL_ROW_MAPPINGS
from domain.financial_statements.retained_earnings import compute_retained_earnings_schedule
from domain.financial_statements.result import PnLPeriodResult, PnLStatementResult
from domain.waterfall.waterfall_engine import WaterfallPeriod, WaterfallResult

TUHO_BOOK_DEPRECIATION_TOTAL_KEUR = 72_993.7
TUHO_TAX_DEPRECIATION_TOTAL_KEUR = 70_691.5


def _assemble_pnl_period(
    period: WaterfallPeriod,
    retained_earnings_keur: float,
    *,
    use_shl_gross_accrued_for_pnl: bool = False,
    book_depreciation_keur: float | None = None,
    recompute_taxable_income_from_pnl: bool = False,
) -> PnLPeriodResult:
    revenues = period.revenue_keur
    operating_expenses = -period.opex_keur
    local_tax = 0.0
    wht_on_interests = 0.0
    depreciation_source = (
        book_depreciation_keur
        if book_depreciation_keur is not None
        else period.tax_depreciation_audit_keur
    )
    depreciation = -depreciation_source
    total_expenses = operating_expenses + local_tax + wht_on_interests + depreciation
    ebit = revenues + total_expenses

    interest_from_reserve_accounts = 0.0
    interest_from_cash = 0.0
    wht_on_financing_revenues = 0.0
    senior_interest_expense = -period.senior_interest_keur
    refinancing_interest = 0.0
    junior_interest = 0.0
    shl_interest_source = (
        period.shl_gross_accrued_interest_keur
        if use_shl_gross_accrued_for_pnl
        else period.shl_interest_keur
    )
    shl_interest_expense = -shl_interest_source
    interest_on_cash = 0.0
    financial_earnings = (
        interest_from_reserve_accounts
        + interest_from_cash
        + wht_on_financing_revenues
        + senior_interest_expense
        + refinancing_interest
        + junior_interest
        + shl_interest_expense
        + interest_on_cash
    )
    earnings_before_tax = ebit + financial_earnings

    fiscal_reintegration = period.fiscal_reintegration_audit_keur
    taxable_income_before_losses = (
        earnings_before_tax + fiscal_reintegration
        if recompute_taxable_income_from_pnl
        else period.taxable_income_before_losses_audit_keur
    )
    losses_n_1 = -period.tax_loss_opening_audit_keur
    allocated_losses = period.tax_loss_used_audit_keur
    losses_n = -period.tax_loss_closing_audit_keur
    carriable_losses = -period.tax_loss_closing_audit_keur
    taxable_profit_after_losses = period.taxable_profit_after_losses_audit_keur
    cit_accrual = -period.cit_accrual_audit_keur
    cash_tax_excel_style_h2_diagnostic = period.cash_tax_excel_style_h2_diagnostic_keur
    net_income = earnings_before_tax + cit_accrual
    legal_reserve = 0.0
    net_dividends = -period.distribution_keur

    return PnLPeriodResult(
        period=period.period,
        date=period.date,
        year_index=period.year_index,
        period_in_year=period.period_in_year,
        revenues_keur=revenues,
        operating_expenses_keur=operating_expenses,
        local_tax_keur=local_tax,
        wht_on_interests_keur=wht_on_interests,
        depreciation_keur=depreciation,
        total_expenses_keur=total_expenses,
        ebit_keur=ebit,
        interest_from_reserve_accounts_keur=interest_from_reserve_accounts,
        interest_from_cash_keur=interest_from_cash,
        wht_on_financing_revenues_keur=wht_on_financing_revenues,
        senior_interest_expense_keur=senior_interest_expense,
        refinancing_interest_keur=refinancing_interest,
        junior_interest_keur=junior_interest,
        shl_interest_expense_keur=shl_interest_expense,
        interest_on_cash_keur=interest_on_cash,
        financial_earnings_keur=financial_earnings,
        earnings_before_tax_keur=earnings_before_tax,
        fiscal_reintegration_keur=fiscal_reintegration,
        taxable_income_before_losses_keur=taxable_income_before_losses,
        losses_n_1_keur=losses_n_1,
        allocated_losses_keur=allocated_losses,
        losses_n_keur=losses_n,
        carriable_losses_keur=carriable_losses,
        taxable_profit_after_losses_keur=taxable_profit_after_losses,
        cit_accrual_keur=cit_accrual,
        cash_tax_excel_style_h2_diagnostic_keur=cash_tax_excel_style_h2_diagnostic,
        net_income_keur=net_income,
        legal_reserve_keur=legal_reserve,
        retained_earnings_keur=retained_earnings_keur,
        net_dividends_keur=net_dividends,
    )


def assemble_pnl(
    waterfall_result: WaterfallResult,
    opening_retained_earnings_keur: float = 0.0,
) -> PnLStatementResult:
    use_shl_gross_accrued_for_pnl = getattr(
        waterfall_result,
        "use_shl_gross_accrued_for_pnl",
        False,
    )
    project_code = getattr(waterfall_result, "project_code", "")
    if use_shl_gross_accrued_for_pnl and project_code != "TUHO-WIND-1":
        raise ValueError("Gross accrued SHL P&L bridge is currently supported only for TUHO-WIND-1")
    use_book_depreciation_for_pnl = getattr(
        waterfall_result,
        "use_book_depreciation_for_pnl",
        False,
    )
    if use_book_depreciation_for_pnl and project_code != "TUHO-WIND-1":
        raise ValueError("Book depreciation P&L bridge is currently supported only for TUHO-WIND-1")

    book_depreciation_schedule = (
        _tuho_book_depreciation_schedule(len(waterfall_result.periods))
        if use_book_depreciation_for_pnl
        else ()
    )

    periods_without_retained: list[PnLPeriodResult] = []
    net_income_schedule: list[float] = []
    dividends_paid_schedule: list[float] = []

    for idx, period in enumerate(waterfall_result.periods):
        provisional = _assemble_pnl_period(
            period,
            retained_earnings_keur=0.0,
            use_shl_gross_accrued_for_pnl=use_shl_gross_accrued_for_pnl,
            book_depreciation_keur=(
                book_depreciation_schedule[idx]
                if use_book_depreciation_for_pnl
                else None
            ),
            recompute_taxable_income_from_pnl=use_book_depreciation_for_pnl,
        )
        periods_without_retained.append(provisional)
        net_income_schedule.append(provisional.net_income_keur)
        dividends_paid_schedule.append(period.distribution_keur)

    retained_balances = compute_retained_earnings_schedule(
        tuple(net_income_schedule),
        tuple(dividends_paid_schedule),
        opening_retained_earnings_keur=opening_retained_earnings_keur,
    )

    periods = tuple(
        PnLPeriodResult(
            **{
                **period.__dict__,
                "retained_earnings_keur": retained_balance,
            }
        )
        for period, retained_balance in zip(periods_without_retained, retained_balances)
    )
    totals_by_row = {
        mapping.row_code: sum(period.row_values()[mapping.row_code] for period in periods)
        for mapping in PNL_ROW_MAPPINGS
    }
    return PnLStatementResult(
        periods=periods,
        row_mapping=PNL_ROW_MAPPINGS,
        totals_by_row=totals_by_row,
    )


def _tuho_book_depreciation_schedule(period_count: int) -> tuple[float, ...]:
    """Return the TUHO aggregate book depreciation fixture schedule.

    Category-level CAPEX mapping is intentionally not inferred here. This
    default-off bridge uses the committed aggregate Dep R30 / P&L R13 fixture
    as an attribution harness until category fixtures are available.
    """

    ledger = build_depreciation_ledger(
        DepreciationLedgerInput(
            asset_classes=(
                AssetClassConfig(
                    asset_class="tuho_aggregate_fixture",
                    gross_asset_basis_keur=TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
                    book_depreciable_basis_keur=TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
                    tax_depreciable_basis_keur=TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
                    placed_in_service_period=0,
                    depreciation_start_period=0,
                    source_label="TUHO aggregate Dep R30/R31 fixture",
                ),
            ),
            policies={
                "tuho_aggregate_fixture": DepreciationPolicy(
                    useful_life_book_periods=period_count,
                    useful_life_tax_periods=period_count,
                    period_frequency="semiannual",
                )
            },
            period_count=period_count,
            period_frequency="semiannual",
            cod_period=0,
        )
    )
    return tuple(period.book_depreciation_keur for period in ledger.aggregate_periods())
