"""Base-performance reconciliation helpers for C3B3D2B6.

This module is diagnostics-only. Source fixtures are accepted as test/review
oracles and never become runtime calculation inputs.
"""
from __future__ import annotations

from typing import Any
from finco_core.engine.period_engine import map_period_vector


def _delta_pct(delta: float, excel: float) -> float | None:
    if abs(excel) < 1e-12:
        return None
    return delta / excel


def _safe_price(revenue_keur: float, production_mwh: float) -> float:
    if abs(production_mwh) < 1e-12:
        return 0.0
    return revenue_keur * 1000.0 / production_mwh


def _shl_source_by_period(shl_source: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not shl_source:
        return {}
    return {
        int(row["ds_index"]): row
        for row in shl_source.get("periods", ())
        if "ds_index" in row
    }


def _source_value(
    source: dict[str, Any],
    line: str,
    idx: int,
    shl_by_idx: dict[int, dict[str, Any]] | None = None,
) -> float | None:
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
    if line == "EBIT":
        return source["pl"]["ebit_keur"][idx]
    if line == "Senior Opening":
        return ds["sd_beginning_keur"][idx]
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
    if line == "SHL Opening":
        return ds["shl_beginning_keur"][idx]
    if line == "SHL Cash Interest":
        row = (shl_by_idx or {}).get(idx)
        return row["cash_interest_keur"] if row else None
    if line == "SHL PIK":
        return ds["shl_interest_capitalised_keur"][idx]
    if line == "SHL Principal":
        row = (shl_by_idx or {}).get(idx)
        return row["principal_repaid_keur"] if row else None
    if line == "SHL Closing":
        return ds["shl_ending_keur"][idx]
    raise KeyError(line)


def _runtime_maps(result: Any) -> dict[str, dict[int, float]]:
    periods = {p.period_index: p for p in result.periods}
    ebit = {p.period_index: p.ebit_keur for p in result.periods}
    # Independently-derived canonical axes from model periods (Correction D / TASK 2).
    # These are derived from the canonical immutable model periods, NOT from the schedule
    # indices of the same schedule being validated (which would be self-validation).
    _full_axis: tuple[int, ...] = tuple(p.period_index for p in result.periods)
    _op_axis: tuple[int, ...] = tuple(p.period_index for p in result.periods if p.is_operation)
    _tax_axis: tuple[int, ...] = _full_axis   # tax/CFADS spans all model periods
    _shl_axis: tuple[int, ...] = _full_axis   # SHL schedule spans all model periods
    # Senior axis: use CanonicalAxisContract when present on the result (populated by
    # run_senior_debt_model from typed SeniorDebtPolicy bounds — NOT from solver indices).
    # Fall back to None only when axis_contract is absent (pre-Phase-2C or legacy results).
    _axis_contract = getattr(result, "axis_contract", None)
    _senior_axis: tuple[int, ...] | None = (
        _axis_contract.senior_axis if _axis_contract is not None else None
    )
    def mapped(indices, values, label, expected=None):
        return map_period_vector(indices, values, label=f"base_reconciliation.{label}", expected_indices=expected)

    senior_interest = mapped(result.senior_debt.period_indices, result.senior_debt.senior_interest_keur, "senior_interest", _senior_axis)
    shl_interest = (
        mapped(result.shareholder_loan.period_indices, result.shareholder_loan.shl_gross_interest_keur, "shl_gross_interest", _shl_axis)
        if result.shareholder_loan else {}
    )
    shl_cash_interest = (
        mapped(result.shareholder_loan.period_indices, result.shareholder_loan.shl_cash_interest_keur, "shl_cash_interest", _shl_axis)
        if result.shareholder_loan else {}
    )
    shl_pik = (
        mapped(result.shareholder_loan.period_indices, result.shareholder_loan.shl_pik_interest_keur, "shl_pik_interest", _shl_axis)
        if result.shareholder_loan else {}
    )
    shl_principal = (
        mapped(result.shareholder_loan.period_indices, result.shareholder_loan.shl_principal_keur, "shl_principal", _shl_axis)
        if result.shareholder_loan else {}
    )
    shl_closing = (
        mapped(result.shareholder_loan.period_indices, result.shareholder_loan.shl_closing_keur, "shl_closing", _shl_axis)
        if result.shareholder_loan else {}
    )
    # OperatingSchedules spans the FULL model axis (construction periods carry explicit
    # zero operating values). Validate against _full_axis, NOT _op_axis.
    operating = mapped(result.operating_schedules.period_indices, result.operating_schedules.production_mwh, "production", _full_axis)
    revenue = mapped(result.operating_schedules.period_indices, result.operating_schedules.revenue_keur, "revenue", _full_axis)
    price = {
        idx: _safe_price(revenue.get(idx, 0.0), production)
        for idx, production in operating.items()
    }
    return {
        "Production": operating,
        "Price": price,
        "Revenue": revenue,
        "OPEX": mapped(result.operating_schedules.period_indices, result.operating_schedules.opex_keur, "opex", _full_axis),
        "EBITDA": mapped(result.operating_schedules.period_indices, result.operating_schedules.ebitda_keur, "ebitda", _full_axis),
        "Book Dep": {idx: p.book_depreciation_keur for idx, p in periods.items()},
        "EBIT": ebit,
        "Senior Opening": mapped(result.senior_debt.period_indices, result.senior_debt.senior_debt_opening_keur, "senior_opening", _senior_axis),
        "Senior Interest": senior_interest,
        "SHL Gross Interest": shl_interest,
        "SHL Interest": shl_interest,
        "EBT": {
            idx: ebit.get(idx, 0.0) - senior_interest.get(idx, 0.0) - shl_interest.get(idx, 0.0)
            for idx in periods
        },
        "Fiscal Reintegration": mapped(result.tax_and_cfads.period_indices, result.tax_and_cfads.fiscal_reintegration_audit_keur, "fiscal_reintegration", _tax_axis),
        "Taxable Income": mapped(result.tax_and_cfads.period_indices, result.tax_and_cfads.taxable_income_before_losses_audit_keur, "taxable_income", _tax_axis),
        "Loss Utilisation": mapped(result.tax_and_cfads.period_indices, result.tax_and_cfads.tax_loss_used_audit_keur, "loss_utilisation", _tax_axis),
        "CIT": mapped(result.tax_and_cfads.period_indices, result.tax_and_cfads.tax_keur, "cit", _tax_axis),
        "Cash Tax": mapped(result.tax_and_cfads.period_indices, result.tax_and_cfads.corporate_tax_cash_keur, "cash_tax", _tax_axis),
        "Base CFADS": mapped(result.tax_and_cfads.period_indices, result.tax_and_cfads.cfads_keur, "base_cfads", _tax_axis),
        "Senior Principal": mapped(result.senior_debt.period_indices, result.senior_debt.senior_principal_keur, "senior_principal", _senior_axis),
        "Senior Debt Service": mapped(result.senior_debt.period_indices, result.senior_debt.senior_debt_service_keur, "senior_debt_service", _senior_axis),
        "Senior Closing": mapped(result.senior_debt.period_indices, result.senior_debt.senior_debt_closing_keur, "senior_closing", _senior_axis),
        "Post-Senior Cash": mapped(result.post_senior_cash.period_indices, result.post_senior_cash.cash_after_senior_before_reserves_keur, "post_senior_cash", _full_axis),
        "Cash Available for SHL": mapped(result.post_senior_cash.period_indices, result.post_senior_cash.cash_available_for_shl_before_reserves_keur, "cash_available_for_shl", _full_axis),
        "SHL Opening": (
            mapped(result.shareholder_loan.period_indices, result.shareholder_loan.shl_opening_keur, "shl_opening", _shl_axis)
            if result.shareholder_loan else {}
        ),
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
    "EBIT",
    "Senior Opening",
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
    "SHL Opening",
    "SHL Cash Interest",
    "SHL PIK",
    "SHL Principal",
    "SHL Closing",
)


def build_base_performance_reconciliation(
    result: Any,
    source: dict[str, Any],
    *,
    shl_source_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = _runtime_maps(result)
    shl_by_idx = _shl_source_by_period(shl_source_truth)
    period_by_idx = {p.period_index: p for p in result.periods}
    rows: list[dict[str, Any]] = []
    for idx in sorted(period_by_idx):
        if idx == 0:
            continue
        period = period_by_idx[idx]
        for line in LINES:
            excel = (
                _source_value(source, line, idx, shl_by_idx)
                if idx < len(source["cf"]["eop_date"])
                else None
            )
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
    first_material_divergence = next(
        (
            row for row in rows
            if row["period"] >= 1 and abs(row["delta"]) > 0.1
        ),
        None,
    )
    return {
        "classification": "BASE_CASE_RECONCILIATION_DIAGNOSTIC_ONLY",
        "source_usage": (
            "Excel source fixtures are diagnostics-only review oracles; "
            "they are never runtime calculation inputs."
        ),
        "rows": rows,
        "max_by_line": max_by_line,
        "first_divergence": first_divergence,
        "first_material_divergence": first_material_divergence,
    }
