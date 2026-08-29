"""financial_engine.financial_statements.assembly — Phase C3 statement assembly.

Clean sources → statement assembly → presentation. STRICTLY DOWNSTREAM:
consumes only already-authoritative clean-engine results attached to the
G2C result; performs roll-forwards and identity checks; never recomputes
tax, debt, SHL or distributions; never feeds back into the engine.

Canonical axis: the model period grid (model.periods). G2C waterfall
periods live on their own 1-based construction+operating axis and are
joined by cashflow_date == period_end (date join, validated — mismatch
fails closed with STATEMENT_PERIOD_AXIS_MISMATCH).
"""
from __future__ import annotations

from datetime import date

from financial_engine.financial_statements.contracts import (
    AccountingPolicies,
    BalanceSheetPeriod,
    FixedAssetRollForwardPeriod,
    FinancialStatementsResult,
    IncomeStatementPeriod,
    LineAuthority,
    PFCashWaterfallPeriod,
    RetainedEarningsPeriod,
    StatementStatus,
    TaxBridgePeriod,
)

_TOLERANCE_KEUR = 1e-6


def _at(vector, position: int):
    try:
        value = vector[position]
    except (IndexError, TypeError, KeyError):
        return None
    return None if value is None else float(value)


def _is_finite(value) -> bool:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return f == f and abs(f) != float("inf")


def _join_waterfall_by_date(model_periods, waterfall_periods):
    """Join G2C waterfall periods onto the model grid by period END date.

    Returns (by_date, matched_count). Raises typed mismatch if fewer than
    half of model periods find a dated waterfall counterpart (the grids are
    different axes, but every OPERATING model period must have one).
    """
    by_date: dict = {}
    for w in waterfall_periods:
        wp_date = getattr(w, "cashflow_date", None)
        if wp_date is not None:
            by_date.setdefault(wp_date, w)
    operating = [p for p in model_periods if getattr(p, "is_operation", False)]
    matched = sum(1 for p in operating if getattr(p, "period_end", None) in by_date)
    if operating and matched < len(operating):
        missing = [p.period_index for p in operating
                   if getattr(p, "period_end", None) not in by_date]
        raise _AxisMismatch(missing)
    return by_date, matched


class _AxisMismatch(ValueError):
    def __init__(self, missing_indices):
        super().__init__(
            f"STATEMENT_PERIOD_AXIS_MISMATCH: operating model periods with no "
            f"dated G2C waterfall counterpart: {missing_indices[:10]}"
        )
        self.missing_indices = missing_indices


def assemble_decision_complete_financial_statements(
    g2c_result,
    project_inputs=None,
) -> FinancialStatementsResult:
    """Assemble decision-complete financial statements from clean results.

    Assembly only: every value is either a direct clean vector element or a
    causal roll-forward/identity of clean vectors. No engine execution, no
    recomputation of tax/debt/SHL/distributions, no residual-cash insert.
    """
    fin = g2c_result.financing_result
    model = fin.project_model_result
    op = model.operating_schedules
    tax = model.tax_and_cfads
    senior = model.senior_debt
    shl = model.shareholder_loan
    dsra = getattr(model, "cash_dsra", None)
    wps = g2c_result.waterfall_periods

    model_periods = list(model.periods)
    try:
        wp_by_date, _matched = _join_waterfall_by_date(model_periods, wps)
    except _AxisMismatch:
        return FinancialStatementsResult(
            status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            project_inputs_summary={},
            income_statement_status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            income_statement_periods=(),
            tax_bridge_status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            tax_bridge_periods=(),
            terminal_unpaid_tax_keur=None,
            cash_flow_status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            pf_cash_waterfall_periods=(),
            fixed_asset_status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            fixed_asset_periods=(),
            retained_earnings_status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            retained_earnings_periods=(),
            balance_sheet_status=StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH,
            balance_sheet_periods=(),
            accounting_policies=AccountingPolicies(),
            unavailable_reasons={},
        )

    op_by_idx = dict(zip(op.period_indices, range(len(op.period_indices))))
    tax_by_idx = dict(zip(tax.period_indices, range(len(tax.period_indices))))
    senior_by_idx = dict(zip(senior.period_indices, range(len(senior.period_indices))))
    shl_by_idx = dict(zip(shl.period_indices, range(len(shl.period_indices))))
    dsra_by_idx = {}
    if dsra is not None:
        dsra_by_idx = {pr.period_index: pr for pr in dsra.period_results}

    pnl_periods: list[IncomeStatementPeriod] = []
    tax_periods: list[TaxBridgePeriod] = []
    pf_periods: list[PFCashWaterfallPeriod] = []
    fa_periods: list[FixedAssetRollForwardPeriod] = []
    re_periods: list[RetainedEarningsPeriod] = []
    bs_periods: list[BalanceSheetPeriod] = []

    cumulative_book_dep = 0.0
    cumulative_share_capital = 0.0
    cumulative_share_premium = 0.0
    axis_ok = True
    non_finite = False

    for mp in model_periods:
        idx = mp.period_index
        oi = op_by_idx.get(idx)
        ti = tax_by_idx.get(idx)
        si = senior_by_idx.get(idx)
        shi = shl_by_idx.get(idx)
        wp = wp_by_date.get(getattr(mp, "period_end", None))
        dpr = dsra_by_idx.get(idx)

        revenue = float(getattr(mp, "revenue_keur", 0.0) or 0.0)
        opex = float(getattr(mp, "opex_keur", 0.0) or 0.0)
        ebitda = float(getattr(mp, "ebitda_keur", 0.0) or 0.0)
        book_dep = float(getattr(mp, "book_depreciation_keur", 0.0) or 0.0)
        ebit = float(getattr(mp, "ebit_keur", 0.0) or 0.0)

        senior_int = _at(senior.senior_interest_keur, si) if si is not None else 0.0
        senior_int = senior_int or 0.0
        # P&L SHL interest = gross accrued (cash + PIK) — never cash-only.
        shl_gross = _at(shl.shl_gross_interest_keur, shi) if shi is not None else 0.0
        shl_gross = shl_gross or 0.0
        net_financial = -(senior_int + shl_gross)
        ebt = ebit + net_financial
        cit_accrual = _at(tax.tax_keur, ti) if ti is not None else 0.0
        cit_accrual = cit_accrual or 0.0
        net_income = ebt - cit_accrual

        for v in (revenue, opex, ebitda, book_dep, ebit, senior_int, shl_gross,
                  ebt, cit_accrual, net_income):
            if not _is_finite(v):
                non_finite = True

        pnl_periods.append(IncomeStatementPeriod(
            period_index=int(idx),
            period_start=getattr(mp, "period_start", None),
            period_end=getattr(mp, "period_end", None),
            is_construction=bool(getattr(mp, "is_construction", False)),
            revenue_keur=revenue,
            opex_keur=opex,
            ebitda_keur=ebitda,
            book_depreciation_keur=book_dep,
            ebit_keur=ebit,
            senior_interest_expense_keur=senior_int,
            shl_interest_expense_keur=shl_gross,
            net_financial_result_keur=net_financial,
            earnings_before_tax_keur=ebt,
            cit_accrual_keur=cit_accrual,
            net_income_keur=net_income,
            authority={
                "revenue": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "opex": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "ebitda": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "book_depreciation": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "senior_interest": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "shl_interest": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "cit_accrual": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "ebit_ebt_net_income": LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value,
            },
        ))

        tax_periods.append(TaxBridgePeriod(
            period_index=int(idx),
            taxable_income_before_losses_keur=_at(tax.taxable_income_before_losses_audit_keur, ti),
            taxable_profit_after_losses_keur=_at(tax.taxable_profit_after_losses_audit_keur, ti),
            fiscal_reintegration_keur=_at(tax.fiscal_reintegration_audit_keur, ti),
            tax_loss_opening_keur=_at(tax.tax_loss_opening_audit_keur, ti),
            tax_loss_used_keur=_at(tax.tax_loss_used_audit_keur, ti),
            tax_loss_closing_keur=_at(tax.tax_loss_closing_audit_keur, ti),
            tax_depreciation_keur=_at(tax.tax_depreciation_audit_keur, ti),
            cit_accrual_keur=_at(tax.cit_accrual_audit_keur, ti),
            cash_tax_current_period_keur=_at(tax.cash_tax_current_period_audit_keur, ti),
            corporate_tax_cash_keur=_at(tax.corporate_tax_cash_keur, ti),
            cash_tax_bridge_reconciliation_keur=_at(tax.cash_tax_bridge_reconciliation_keur, ti),
        ))

        wp = wp if wp is not None else type("EmptyWp", (), {})()  # attribute-safe empty
        senior_draw = None
        pf_periods.append(PFCashWaterfallPeriod(
            period_index=int(idx),
            cashflow_date=getattr(mp, "period_end", None),
            is_construction=bool(getattr(mp, "is_construction", False)),
            revenue_cash_keur=revenue,
            opex_cash_keur=opex,
            ebitda_keur=ebitda,
            cash_tax_keur=_at(tax.corporate_tax_cash_keur, ti) or 0.0,
            fcf_banks_keur=float(getattr(wp, "signed_post_senior_keur", 0.0) or 0.0),
            senior_cash_interest_keur=senior_int,
            senior_principal_keur=_at(senior.senior_principal_keur, si) or 0.0,
            senior_debt_service_keur=_at(senior.senior_debt_service_keur, si) or 0.0,
            dsra_top_up_keur=float(getattr(wp, "dsra_top_up_keur", 0.0) or 0.0),
            dsra_draw_keur=float(getattr(wp, "dsra_draw_keur", 0.0) or 0.0),
            dsra_release_keur=float(getattr(wp, "dsra_release_keur", 0.0) or 0.0),
            distribution_account_inflow_keur=float(
                getattr(wp, "distribution_account_inflow_keur", 0.0) or 0.0),
            distribution_account_release_keur=float(
                getattr(wp, "distribution_account_release_keur", 0.0) or 0.0),
            distribution_account_closing_keur=float(
                getattr(wp, "distribution_account_closing_keur", 0.0) or 0.0),
            shl_cash_interest_keur=float(getattr(wp, "shl_cash_interest_receipt_keur", 0.0) or 0.0),
            shl_pik_keur=float(getattr(wp, "shl_pik_keur", 0.0) or 0.0),
            shl_principal_paid_keur=float(
                getattr(wp, "actual_shl_principal_paid_keur", 0.0) or 0.0),
            shl_unpaid_principal_keur=float(
                getattr(wp, "unpaid_shl_principal_keur", 0.0) or 0.0),
            legal_equity_distribution_keur=float(
                getattr(wp, "legal_equity_distribution_keur", 0.0) or 0.0),
            equity_contributions_keur=float(
                (getattr(wp, "share_capital_contribution_keur", 0.0) or 0.0)
                + (getattr(wp, "share_premium_contribution_keur", 0.0) or 0.0)
                + (getattr(wp, "other_committed_equity_contribution_keur", 0.0) or 0.0)
                + (getattr(wp, "additional_equity_contribution_keur", 0.0) or 0.0)),
            senior_draw_keur=senior_draw,
        ))

        # Fixed assets: accumulated BOOK depreciation roll-forward is causal;
        # gross/NFA basis requires a book-capitalization authority that clean
        # results do not expose — truthfully unavailable.
        cumulative_book_dep += book_dep
        fa_periods.append(FixedAssetRollForwardPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            book_depreciation_keur=book_dep,
            accumulated_book_depreciation_keur=cumulative_book_dep,
            gross_fixed_assets_keur=None,
            accumulated_depreciation_on_disposals_keur=0.0,
            net_fixed_assets_keur=None,
        ))

        # Retained earnings: NI - legal distributions; opening requires a
        # construction-equity accounting authority (unavailable — no residual-cash insert).
        legal_dist = float(getattr(wp, "legal_equity_distribution_keur", 0.0) or 0.0)
        re_periods.append(RetainedEarningsPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            opening_retained_earnings_keur=None,
            net_income_keur=net_income,
            legal_equity_distribution_keur=legal_dist,
            legal_reserve_allocation_keur=None,
            closing_retained_earnings_keur=None,
        ))

        # Balance sheet presentation: balances are clean closing authority;
        # unrestricted cash / gross FA / equity accounts are truthfully
        # unavailable → balance_check NOT claimed (no residual-cash insert).
        cumulative_share_capital += float(
            getattr(wp, "share_capital_contribution_keur", 0.0) or 0.0)
        cumulative_share_premium += float(
            getattr(wp, "share_premium_contribution_keur", 0.0) or 0.0)
        dsra_close = (
            float(dpr.closing_balance_keur) if dpr is not None else None
        )
        bs_periods.append(BalanceSheetPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            senior_debt_balance_keur=_at(senior.senior_debt_closing_keur, si),
            shl_balance_keur=(
                float(getattr(wp, "actual_shl_closing_balance_keur", 0.0) or 0.0)
                if wp is not None else None
            ),
            shl_unpaid_principal_keur=(
                float(getattr(wp, "unpaid_shl_principal_keur", 0.0) or 0.0)
                if wp is not None else None
            ),
            distribution_account_balance_keur=(
                float(getattr(wp, "distribution_account_closing_keur", 0.0) or 0.0)
                if wp is not None else None
            ),
            dsra_balance_keur=dsra_close,
            unrestricted_cash_keur=None,
            gross_fixed_assets_keur=None,
            accumulated_book_depreciation_keur=cumulative_book_dep,
            share_capital_keur=cumulative_share_capital,
            share_premium_keur=cumulative_share_premium,
            retained_earnings_keur=None,
            balance_check_keur=None,
        ))

    if non_finite or not axis_ok:
        overall = StatementStatus.NON_FINITE_RESULT
    else:
        # Honest partial availability: P&L / tax bridge / PF waterfall are
        # complete authorities; balance sheet, unrestricted cash, gross FA
        # basis and opening equity are not yet authoritative.
        overall = StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE

    unavailable = {
        "balance_sheet": (
            "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE: closing unrestricted "
            "cash requires a causal unrestricted-cash roll-forward that the "
            "clean runtime does not yet provide; no residual-cash insert applied."
        ),
        "gross_fixed_assets": (
            "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE: the book fixed-asset "
            "capitalization basis is not exposed on clean results; only the "
            "accumulated book depreciation roll-forward is causal."
        ),
        "opening_retained_earnings": (
            "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE: construction-"
            "period equity accounting authority is not yet typed; the "
            "operating-period NI/distribution movements are shown with an "
            "explicitly unavailable opening."
        ),
        "tax_payable": (
            "TAX_PAYABLE_AUTHORITY_UNAVAILABLE: a CIT payable roll-forward "
            "is not part of the clean tax timing contract; terminal unpaid "
            "tax is surfaced directly."
        ),
    }

    return FinancialStatementsResult(
        status=overall,
        project_inputs_summary={
            "model_period_count": len(model_periods),
            "waterfall_period_count": len(wps),
            "g2c_dscr_authority": senior.binding_constraint,
        },
        income_statement_status=StatementStatus.OK,
        income_statement_periods=tuple(pnl_periods),
        tax_bridge_status=StatementStatus.OK,
        tax_bridge_periods=tuple(tax_periods),
        terminal_unpaid_tax_keur=float(getattr(tax, "terminal_unpaid_tax_keur", 0.0) or 0.0),
        cash_flow_status=StatementStatus.OK,
        pf_cash_waterfall_periods=tuple(pf_periods),
        fixed_asset_status=StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE,
        fixed_asset_periods=tuple(fa_periods),
        retained_earnings_status=StatementStatus.OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE,
        retained_earnings_periods=tuple(re_periods),
        balance_sheet_status=StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE,
        balance_sheet_periods=tuple(bs_periods),
        accounting_policies=AccountingPolicies(provenance={
            "baseline": "clean-engine results only (no legacy statement modules)",
            "axis": "model.periods; G2C joined by cashflow_date == period_end",
        }),
        unavailable_reasons=unavailable,
        authority_labels={
            "pnl": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "tax_bridge": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "pf_cash_waterfall": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "accumulated_book_depreciation": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value),
            "retained_earnings_movements": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value),
            "gross_fixed_assets": LineAuthority.UNRESOLVED.value,
            "unrestricted_cash": LineAuthority.UNRESOLVED.value,
            "opening_retained_earnings": LineAuthority.UNRESOLVED.value,
        },
    )
