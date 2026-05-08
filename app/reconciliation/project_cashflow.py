"""Project cashflow bridge helper."""
from typing import Any


def build_project_cf_rows(result: Any) -> list[dict]:
    """Build project cashflow bridge rows from a DemoResult or WaterfallResult.

    Returns list of dicts with columns:
        period, date, revenue, opex, ebitda, depreciation,
        unlevered_tax, project_free_cf, cumulative_project_cf

    Project free CF = EBITDA - tax (capex is already in CF after tax via construction-period flows).
    Construction periods: capex flows, no revenue.
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
    cumulative = 0.0

    for p in periods:
        if p.is_operation:
            rev = p.revenue_keur
            opex = p.opex_keur
            ebitda = p.ebitda_keur
            dep = p.depreciation_keur
            tax = p.tax_keur
            pcf = ebitda - tax
            cumulative += pcf
        else:
            rev = 0.0
            opex = 0.0
            ebitda = 0.0
            dep = 0.0
            tax = 0.0
            pcf = p.cf_after_tax_keur
            cumulative += pcf

        rows.append({
            "period": p.period,
            "date": p.date,
            "revenue": round(rev, 1),
            "opex": round(opex, 1),
            "ebitda": round(ebitda, 1),
            "depreciation": round(dep, 1),
            "unlevered_tax": round(tax, 1),
            "project_free_cf": round(pcf, 1),
            "cumulative_project_cf": round(cumulative, 1),
        })

    return rows