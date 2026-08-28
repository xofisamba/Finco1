"""Decision-complete downstream returns and maturity authority.

This module consumes one already-computed clean G2C financing/waterfall result.
It never sizes financing, changes upstream schedules, or manufactures terminal
cash. Project tax is recomputed on the canonical operating periods with zero
financing interest so Project XIRR remains genuinely unlevered.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING

from finco_core.sponsor.xirr import robust_xirr

from financial_engine.project_returns.contracts import (
    CashAccountTerminalState,
    CashAccountTerminalStatus,
    DebtTerminalState,
    DebtTerminalStatus,
    DecisionCompleteReturnSummary,
    ProjectReturnCashFlow,
    ProjectReturnResult,
    ReturnMetricSummary,
    ShlTerminalState,
    ShlTerminalStatus,
    TerminalFinancialState,
)
from financial_engine.sponsor_returns.contracts import ReturnMetricStatus

if TYPE_CHECKING:
    from finco_core.inputs import ProjectInputs
    from financial_engine.financing.contracts import ProjectFinancingResult
    from financial_engine.shareholder_waterfall.contracts import (
        CovenantGatedWaterfallPeriod,
    )


_TOL = 1e-7
_PROJECT_RETURN_AUTHORITY = (
    "C1_UNLEVERED_HARD_CAPEX_PLUS_EBITDA_MINUS_ZERO_FINANCING_INTEREST_CASH_TAX"
)


def _status(cashflows: list[float], xirr: float | None) -> ReturnMetricStatus:
    if not any(value < -_TOL for value in cashflows):
        return ReturnMetricStatus.NO_NEGATIVE_CASHFLOW
    if not any(value > _TOL for value in cashflows):
        return ReturnMetricStatus.NO_POSITIVE_CASHFLOW
    if xirr is None:
        return ReturnMetricStatus.NON_CONVERGENT
    return ReturnMetricStatus.OK


def _construction_investment_rows(
    project_inputs: "ProjectInputs",
    financing: "ProjectFinancingResult",
) -> tuple[tuple[date, float], ...]:
    """Return authoritative hard-CAPEX timing without financing uses."""
    construction = financing.construction_financing
    hard_capex = financing.project_uses.hard_project_capex_keur
    if construction is not None:
        dates = construction.period_end_dates
        amounts = construction.hard_capex_uses_keur
        if len(dates) != len(amounts):
            raise ValueError("C1_PROJECT_RETURN_CONSTRUCTION_AXIS_LENGTH_MISMATCH")
        if abs(sum(amounts) - hard_capex) > _TOL:
            raise ValueError("C1_PROJECT_RETURN_HARD_CAPEX_TIMING_DOES_NOT_RECONCILE")
        return tuple((cash_date, float(amount)) for cash_date, amount in zip(dates, amounts))

    periods = financing.construction_funding.periods
    period_uses = tuple(float(period.project_cash_uses_keur) for period in periods)
    if periods and abs(sum(period_uses) - hard_capex) <= _TOL:
        financial_close = project_inputs.info.financial_close
        from financial_engine.sponsor_returns.model import _construction_period_date

        return tuple(
            (_construction_period_date(financial_close, period.period_index), amount)
            for period, amount in zip(periods, period_uses)
        )

    # No authoritative hard-CAPEX timing exists. The typed financial-close date
    # is the conservative single-date authority; financing-use timing is not reused.
    return ((project_inputs.info.financial_close, float(hard_capex)),)


def _unlevered_cash_tax_by_period(
    project_inputs: "ProjectInputs",
    financing: "ProjectFinancingResult",
) -> dict[int, float]:
    from financial_engine.adapters.tax_inputs import (
        build_tax_contract_from_project_inputs,
    )
    from financial_engine.tax.engine import calculate_tax

    tax_contract = build_tax_contract_from_project_inputs(
        project_inputs,
        complete_financing_interest_will_be_injected=True,
    )
    if tax_contract.period_interest:
        raise ValueError("C1_PROJECT_RETURN_FINANCING_INTEREST_LEAK")
    model = financing.project_model_result
    tax_result = calculate_tax(model.periods, tax_contract)
    return {
        period.period_index: float(period.cash_tax_keur)
        for period in tax_result.period_results
    }


def _project_return(
    project_inputs: "ProjectInputs",
    financing: "ProjectFinancingResult",
) -> ProjectReturnResult:
    model = financing.project_model_result
    cash_tax = _unlevered_cash_tax_by_period(project_inputs, financing)
    by_date: dict[date, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])

    for cash_date, amount in _construction_investment_rows(project_inputs, financing):
        by_date[cash_date][0] += amount

    for period in model.periods:
        if not period.is_operation:
            continue
        values = by_date[period.period_end]
        values[1] += float(period.ebitda_keur)
        values[2] += cash_tax.get(period.period_index, 0.0)

    rows: list[ProjectReturnCashFlow] = []
    for cash_date in sorted(by_date):
        investment, operating, tax, terminal = by_date[cash_date]
        rows.append(ProjectReturnCashFlow(
            cashflow_date=cash_date,
            project_investment_outflow_keur=investment,
            project_operating_inflow_keur=operating,
            project_tax_outflow_keur=tax,
            terminal_component_keur=terminal,
            net_unlevered_project_cashflow_keur=(
                operating - tax + terminal - investment
            ),
        ))

    values = [row.net_unlevered_project_cashflow_keur for row in rows]
    dates = [row.cashflow_date for row in rows]
    xirr = robust_xirr(values, dates)
    return ProjectReturnResult(
        cashflows=tuple(rows),
        project_xirr=xirr,
        project_xirr_status=_status(values, xirr),
        total_hard_capex_investment_keur=sum(
            row.project_investment_outflow_keur for row in rows
        ),
        excluded_financing_cost_uses_keur=(
            financing.project_uses.explicit_financing_cost_uses_keur
        ),
        excluded_reserve_funding_keur=(
            financing.project_uses.reserve_account_funding_keur
        ),
        total_operating_inflow_keur=sum(
            row.project_operating_inflow_keur for row in rows
        ),
        total_project_tax_outflow_keur=sum(
            row.project_tax_outflow_keur for row in rows
        ),
        terminal_component_keur=0.0,
        methodology_authority=_PROJECT_RETURN_AUTHORITY,
    )


def _date_for_period(
    periods: tuple["CovenantGatedWaterfallPeriod", ...],
    period_index: int | None,
) -> date | None:
    if period_index is None:
        return None
    return next(
        (period.cashflow_date for period in periods if period.period_index == period_index and not period.is_construction),
        None,
    )


def _terminal_state(
    financing: "ProjectFinancingResult",
    periods: tuple["CovenantGatedWaterfallPeriod", ...],
    *,
    shl_repayment_mode: str | None,
    shl_maturity_period_index: int | None,
) -> TerminalFinancialState:
    model = financing.project_model_result
    senior = model.senior_debt
    senior_axis = tuple(getattr(model.axis_contract, "senior_axis", ()))
    senior_maturity = senior_axis[-1] if senior_axis else None
    senior_terminal = (
        float(senior.senior_debt_closing_keur[-1])
        if senior is not None and senior.senior_debt_closing_keur else 0.0
    )
    senior_applicable = senior is not None and float(senior.debt_size_keur) > _TOL
    senior_status = (
        DebtTerminalStatus.NOT_APPLICABLE if not senior_applicable
        else DebtTerminalStatus.REPAID if senior_terminal <= _TOL
        else DebtTerminalStatus.OUTSTANDING_AT_MATURITY
    )

    shl_contract = financing.shareholder_loan_model_input
    shl_maturity = shl_maturity_period_index
    shl_mode = shl_repayment_mode
    maturity_row = next(
        (period for period in periods if not period.is_construction and period.period_index == shl_maturity),
        None,
    )
    terminal_row = periods[-1] if periods else None
    shl_terminal = float(terminal_row.shl_closing_balance_keur) if terminal_row else 0.0
    shl_applicable = shl_contract is not None and (
        float(getattr(shl_contract, "initial_principal_keur", 0.0)) > _TOL
    )
    last_period_index = max(
        (period.period_index for period in periods if not period.is_construction),
        default=-1,
    )
    if not shl_applicable:
        shl_status = ShlTerminalStatus.NOT_APPLICABLE
    elif shl_terminal <= _TOL:
        shl_status = ShlTerminalStatus.REPAID
    elif shl_maturity is not None and last_period_index >= shl_maturity:
        shl_status = ShlTerminalStatus.UNPAID_AT_CONTRACTUAL_MATURITY
    else:
        shl_status = ShlTerminalStatus.OUTSTANDING_WITHIN_CONTRACTUAL_TERM

    da_terminal = float(terminal_row.distribution_account_closing_keur) if terminal_row else 0.0
    da_status = (
        CashAccountTerminalStatus.STRANDED_CASH if da_terminal > _TOL
        else CashAccountTerminalStatus.CASH_SHORTFALL if da_terminal < -_TOL
        else CashAccountTerminalStatus.RELEASED
    )
    dsra = model.cash_dsra
    dsra_applicable = dsra is not None and (
        str(getattr(dsra.mode, "value", dsra.mode)) == "CASH_DSRA"
    )
    dsra_terminal = float(dsra.final_closing_balance_keur) if dsra is not None else 0.0
    dsra_status = (
        CashAccountTerminalStatus.NOT_APPLICABLE if not dsra_applicable
        else CashAccountTerminalStatus.RELEASED if abs(dsra_terminal) <= _TOL
        else CashAccountTerminalStatus.REMAINING_BALANCE
    )

    return TerminalFinancialState(
        senior=DebtTerminalState(
            contractual_maturity_period_index=senior_maturity,
            contractual_maturity_date=_date_for_period(periods, senior_maturity),
            terminal_balance_keur=senior_terminal,
            status=senior_status,
        ),
        shareholder_loan=ShlTerminalState(
            repayment_mode=shl_mode,
            contractual_maturity_period_index=shl_maturity,
            contractual_maturity_date=_date_for_period(periods, shl_maturity),
            contractual_amount_due_at_maturity_keur=(
                float(maturity_row.contractual_shl_principal_due_keur) if maturity_row else 0.0
            ),
            amount_paid_at_maturity_keur=(
                float(maturity_row.actual_shl_principal_paid_keur) if maturity_row else 0.0
            ),
            unpaid_at_maturity_keur=(
                float(maturity_row.unpaid_shl_principal_keur) if maturity_row else 0.0
            ),
            terminal_balance_keur=shl_terminal,
            status=shl_status,
        ),
        distribution_account=CashAccountTerminalState(
            terminal_closing_balance_keur=da_terminal,
            status=da_status,
        ),
        senior_dsra=CashAccountTerminalState(
            terminal_closing_balance_keur=dsra_terminal,
            status=dsra_status,
        ),
    )


def build_decision_complete_return_summary(
    *,
    project_inputs: "ProjectInputs",
    financing: "ProjectFinancingResult",
    waterfall_periods: tuple["CovenantGatedWaterfallPeriod", ...],
    pure_equity_xirr: float | None,
    pure_equity_xirr_status: ReturnMetricStatus,
    pure_equity_moic: float | None,
    pure_equity_moic_status: ReturnMetricStatus,
    total_sponsor_xirr: float | None,
    total_sponsor_xirr_status: ReturnMetricStatus,
    total_sponsor_moic: float | None,
    total_sponsor_moic_status: ReturnMetricStatus,
    total_legal_equity_contributed_keur: float,
    total_legal_equity_distributions_keur: float,
    total_sponsor_contributed_keur: float,
    total_sponsor_receipts_keur: float,
    deductible_shl_covenant_feedback_status: str | None,
    shl_repayment_mode: str | None,
    shl_maturity_period_index: int | None,
) -> DecisionCompleteReturnSummary:
    """Build one immutable downstream summary from already-authoritative values."""
    return DecisionCompleteReturnSummary(
        project=_project_return(project_inputs, financing),
        legal_equity=ReturnMetricSummary(
            xirr=pure_equity_xirr,
            xirr_status=pure_equity_xirr_status,
            moic=pure_equity_moic,
            moic_status=pure_equity_moic_status,
            total_contributions_keur=total_legal_equity_contributed_keur,
            total_receipts_keur=total_legal_equity_distributions_keur,
            net_cashflow_keur=(
                total_legal_equity_distributions_keur
                - total_legal_equity_contributed_keur
            ),
        ),
        total_sponsor=ReturnMetricSummary(
            xirr=total_sponsor_xirr,
            xirr_status=total_sponsor_xirr_status,
            moic=total_sponsor_moic,
            moic_status=total_sponsor_moic_status,
            total_contributions_keur=total_sponsor_contributed_keur,
            total_receipts_keur=total_sponsor_receipts_keur,
            net_cashflow_keur=total_sponsor_receipts_keur - total_sponsor_contributed_keur,
        ),
        terminal=_terminal_state(
            financing,
            waterfall_periods,
            shl_repayment_mode=shl_repayment_mode,
            shl_maturity_period_index=shl_maturity_period_index,
        ),
        deductible_shl_covenant_feedback_status=(
            deductible_shl_covenant_feedback_status
        ),
    )
