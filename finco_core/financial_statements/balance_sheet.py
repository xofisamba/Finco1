"""Balance sheet aggregation from WaterfallPeriod outputs."""
from finco_core.financial_statements.statement_models import BalanceSheetPeriod
from finco_core.financial_statements.income_statement import generate_income_statement


def generate_balance_sheet(
    periods,
    total_capex_keur: float,
    share_capital_keur: float,
    share_premium_keur: float,
) -> list[BalanceSheetPeriod]:
    """Aggregate balance sheet from WaterfallPeriod list.

    NFA: total_capex less accumulated depreciation (straight-line, no revaluations).
    Equity: share_capital + share_premium + cumulative net income - cumulative distributions.
    All other lines: closing balances from WaterfallPeriod.

    A = L + E closes algebraically when the waterfall is internally consistent.
    """
    is_periods = generate_income_statement(periods)

    result = []
    cum_depreciation = 0.0
    cum_distribution = 0.0

    # Reconstruct opening accumulated deficit at COD from first-period WaterfallPeriod data.
    # During construction, SHL may have accrued PIK before the first operational period.
    # That PIK is already in shl_balance_keur[0] but was never in any operational IS period.
    # The opening deficit = total_capex - opening_senior - opening_shl - SC - SP,
    # where opening values are reverse-computed from the first period's closing balances.
    if periods:
        p0 = periods[0]
        senior_at_cod = p0.senior_balance_keur + p0.senior_principal_keur
        shl_at_cod = p0.shl_balance_keur + p0.shl_principal_keur - p0.shl_pik_keur
        opening_deficit = total_capex_keur - senior_at_cod - shl_at_cod - share_capital_keur - share_premium_keur
    else:
        opening_deficit = 0.0

    cum_net_income = opening_deficit  # start with accumulated deficit from construction phase

    for p, isp in zip(periods, is_periods):
        cum_depreciation += p.depreciation_keur
        cum_net_income += isp.net_income_keur
        cum_distribution += p.distribution_keur

        nfa = total_capex_keur - cum_depreciation
        dsra = p.dsra_balance_keur
        mra = p.mra_balance_keur
        cash = p.cash_balance_keur
        total_assets = nfa + dsra + mra + cash

        senior = p.senior_balance_keur
        shl = p.shl_balance_keur
        total_liabilities = senior + shl

        retained = cum_net_income - cum_distribution
        total_equity = share_capital_keur + share_premium_keur + retained

        check = total_assets - total_liabilities - total_equity

        result.append(BalanceSheetPeriod(
            period=p.period,
            date=p.date,
            net_fixed_assets_keur=nfa,
            dsra_balance_keur=dsra,
            mra_balance_keur=mra,
            cash_balance_keur=cash,
            total_assets_keur=total_assets,
            senior_balance_keur=senior,
            shl_balance_keur=shl,
            total_liabilities_keur=total_liabilities,
            share_capital_keur=share_capital_keur,
            share_premium_keur=share_premium_keur,
            retained_earnings_keur=retained,
            total_equity_keur=total_equity,
            check_keur=check,
        ))

    return result
