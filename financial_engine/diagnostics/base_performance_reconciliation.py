"""Base-performance reconciliation helpers for C3B3D2B6.

This module is diagnostics-only. Source fixtures are accepted as test/review
oracles and never become runtime calculation inputs.
"""
from __future__ import annotations

from typing import Any


def _delta_pct(delta: float, excel: float) -> float | None:
    if abs(excel) < 1e-12:
        return None
    return delta / excel


def _safe_price(revenue_keur: float, production_mwh: float) -> float:
    if abs(production_mwh) < 1e-12:
        return 0.0
    return revenue_keur * 1000.0 / production_mwh


def _source_value(source: dict[str, Any], line: str, idx: int) -> float | None:
    cf = source["cf"]
    ds = source["ds"]
    dep = source["dep"]
    tax_rows = source["tax"]["period_diagnostic"]
    if line == "Production":
        return cf["production_mwh"][idx]
    if line == "Price":
        production = cf["production_mwh"][idx]
        revenue = cf["operating_revenues_keur"][idx]
        if production is None or revenue is None:
            return None
        return _safe_price(revenue, production)
    if line == "Revenue":
        return cf["operating_revenues_keur"][idx]
    if line == "OPEX":
        value = cf["operating_expenses_keur"][idx]
        return -value if value is not None else None
    if line == "EBITDA":
        return cf["ebitda_keur"][idx]
    if line == "Book Dep":
        return dep["dep_total_keur"][idx]
    if line == "Senior Interest":
        return ds["sd_gross_interest_keur"][idx]
    if line in ("SHL Gross Interest", "SHL Interest"):
        return ds["shl_net_interest_keur"][idx]
    if line == "EBT":
        return source["pl"]["earnings_before_tax_keur"][idx]
    if line == "Fiscal Reintegration":
        return source["pl"]["fiscal_reintegration_keur"][idx]
    if line == "Taxable Income":
        return source["pl"]["taxable_income_keur"][idx]
    if line == "Loss Utilisation":
        return tax_rows[idx - 1]["excel_allocated_losses_keur"] if idx - 1 < len(tax_rows) else None
    if line == "CIT":
        return source["pl"]["corporate_income_tax_keur"][idx]
    if line == "Cash Tax":
        value = cf["corporate_income_tax_keur"][idx]
        return -value if value is not None else None
    if line == "Base CFADS":
        return cf["fcf_for_banks_keur"][idx]
    if line == "Senior Principal":
        return ds["sd_principal_keur"][idx]
    if line == "Senior Debt Service":
        return ds["sd_service_keur"][idx]
    if line == "Senior Closing":
        return ds["sd_ending_keur"][idx]
    if line == "Post-Senior Cash":
        cfads = cf["fcf_for_banks_keur"][idx]
        senior_service = cf["senior_debt_service_keur"][idx]
        if cfads is None or senior_service is None:
            return None
        return cfads + senior_service
    if line == "Cash Available for SHL":
        return cf["free_cash_flow_for_shl_keur"][idx]
    if line in ("SHL Cash Interest", "SHL PIK", "SHL Principal", "SHL Closing"):
        return None
    raise KeyError(line)


def _runtime_maps(result: Any) -> dict[str, dict[int, float]]:
    periods = {p.period_index: p for p in result.periods}
    ebit = {p.period_index: p.ebit_keur for p in result.periods}
    senior_interest = dict(zip(result.senior_debt.period_indices, result.senior_debt.senior_interest_keur))
    shl_interest = (
        dict(zip(result.shareholder_loan.period_indices, result.shareholder_loan.shl_gross_interest_keur))
        if result.shareholder_loan else {}
    )
    shl_cash_interest = (
        dict(zip(result.shareholder_loan.period_indices, result.shareholder_loan.shl_cash_interest_keur))
        if result.shareholder_loan else {}
    )
    shl_pik = (
        dict(zip(result.shareholder_loan.period_indices, result.shareholder_loan.shl_pik_interest_keur))
        if result.shareholder_loan else {}
    )
    shl_principal = (
        dict(zip(result.shareholder_loan.period_indices, result.shareholder_loan.shl_principal_keur))
        if result.shareholder_loan else {}
    )
    shl_closing = (
        dict(zip(result.shareholder_loan.period_indices, result.shareholder_loan.shl_closing_keur))
        if result.shareholder_loan else {}
    )
    operating = dict(zip(result.operating_schedules.period_indices, result.operating_schedules.production_mwh))
    revenue = dict(zip(result.operating_schedules.period_indices, result.operating_schedules.revenue_keur))
    price = {
        idx: _safe_price(revenue.get(idx, 0.0), production)
        for idx, production in operating.items()
    }
    return {
        "Production": operating,
        "Price": price,
        "Revenue": revenue,
        "OPEX": dict(zip(result.operating_schedules.period_indices, result.operating_schedules.opex_keur)),
        "EBITDA": dict(zip(result.operating_schedules.period_indices, result.operating_schedules.ebitda_keur)),
        "Book Dep": {idx: p.book_depreciation_keur for idx, p in periods.items()},
        "Senior Interest": senior_interest,
        "SHL Gross Interest": shl_interest,
        "SHL Interest": shl_interest,
        "EBT": {
            idx: ebit.get(idx, 0.0) - senior_interest.get(idx, 0.0) - shl_interest.get(idx, 0.0)
            for idx in periods
        },
        "Fiscal Reintegration": dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.fiscal_reintegration_audit_keur)),
        "Taxable Income": dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.taxable_income_before_losses_audit_keur)),
        "Loss Utilisation": dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.tax_loss_used_audit_keur)),
        "CIT": dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.tax_keur)),
        "Cash Tax": dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.corporate_tax_cash_keur)),
        "Base CFADS": dict(zip(result.tax_and_cfads.period_indices, result.tax_and_cfads.cfads_keur)),
        "Senior Principal": dict(zip(result.senior_debt.period_indices, result.senior_debt.senior_principal_keur)),
        "Senior Debt Service": dict(zip(result.senior_debt.period_indices, result.senior_debt.senior_debt_service_keur)),
        "Senior Closing": dict(zip(result.senior_debt.period_indices, result.senior_debt.senior_debt_closing_keur)),
        "Post-Senior Cash": dict(zip(result.post_senior_cash.period_indices, result.post_senior_cash.cash_after_senior_before_reserves_keur)),
        "Cash Available for SHL": dict(zip(result.post_senior_cash.period_indices, result.post_senior_cash.cash_available_for_shl_before_reserves_keur)),
        "SHL Cash Interest": shl_cash_interest,
        "SHL PIK": shl_pik,
        "SHL Principal": shl_principal,
        "SHL Closing": shl_closing,
    }


LINES: tuple[str, ...] = (
    "Production",
    "Price",
    "Revenue",
    "OPEX",
    "EBITDA",
    "Book Dep",
    "Senior Interest",
    "SHL Gross Interest",
    "EBT",
    "Fiscal Reintegration",
    "Taxable Income",
    "Loss Utilisation",
    "CIT",
    "Cash Tax",
    "Base CFADS",
    "Senior Principal",
    "Senior Debt Service",
    "Senior Closing",
    "Post-Senior Cash",
    "Cash Available for SHL",
    "SHL Cash Interest",
    "SHL PIK",
    "SHL Principal",
    "SHL Closing",
)


def build_base_performance_reconciliation(result: Any, source: dict[str, Any]) -> dict[str, Any]:
    runtime = _runtime_maps(result)
    period_by_idx = {p.period_index: p for p in result.periods}
    rows: list[dict[str, Any]] = []
    for idx in sorted(period_by_idx):
        if idx == 0:
            continue
        period = period_by_idx[idx]
        for line in LINES:
            excel = _source_value(source, line, idx) if idx < len(source["cf"]["eop_date"]) else None
            if excel is None:
                continue
            finco = runtime[line].get(idx, 0.0)
            delta = finco - excel
            rows.append(
                {
                    "period": idx,
                    "date": str(period.period_end),
                    "line": line,
                    "excel": excel,
                    "finco": finco,
                    "delta": delta,
                    "delta_pct": _delta_pct(delta, excel),
                }
            )
    max_by_line: dict[str, dict[str, Any]] = {}
    for line in LINES:
        line_rows = [row for row in rows if row["line"] == line]
        if not line_rows:
            continue
        max_by_line[line] = max(line_rows, key=lambda row: abs(row["delta"]))
    first_divergence = next(
        (
            row for row in rows
            if row["period"] >= 1 and abs(row["delta"]) > 1e-6
        ),
        None,
    )
    return {
        "classification": "BASE_CASE_RECONCILIATION_DIAGNOSTIC_ONLY",
        "rows": rows,
        "max_by_line": max_by_line,
        "first_divergence": first_divergence,
    }
