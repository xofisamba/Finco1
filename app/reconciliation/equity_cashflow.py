"""Equity cashflow bridge helper."""
from typing import Any


def build_equity_cf_rows(result: Any) -> list[dict]:
    """Build equity cashflow bridge rows from a DemoResult or WaterfallResult.

    Returns list of dicts with columns:
        period, date, equity_investment, shl_interest, shl_principal,
        distributions, dsra_movement, equity_cash_flow

    Equity cash flow = -equity_investment - shl_interest - shl_principal + distributions + dsra_movement
    (Sign: negative = cash out, positive = cash in)
    """
    wf = None
    if hasattr(result, "result") and hasattr(result, "waterfall_result"):
        wf = result.waterfall_result
    elif hasattr(result, "periods"):
        wf = result

    if wf is None:
        return []

    periods = wf.periods if hasattr(wf, "periods") else []
    if not periods:
        return []

    rows = []

    for p in periods:
        is_constr = not p.is_operation

        if is_constr:
            eq_invest = p.cf_after_tax_keur
            shl_int = 0.0
            shl_principal = 0.0
            dist = 0.0
            dsra_mov = 0.0
            equity_cf = eq_invest
        else:
            eq_invest = 0.0
            shl_int = p.shl_interest_keur
            shl_principal = p.shl_principal_keur
            dist = p.distribution_keur
            dsra_mov = p.dsra_contribution_keur
            equity_cf = dist - shl_int - shl_principal - dsra_mov

        rows.append({
            "period": p.period,
            "date": p.date,
            "equity_investment": round(eq_invest, 1),
            "shl_interest": round(shl_int, 1),
            "shl_principal": round(shl_principal, 1),
            "distributions": round(dist, 1),
            "dsra_movement": round(dsra_mov, 1),
            "equity_cash_flow": round(equity_cf, 1),
        })

    return rows