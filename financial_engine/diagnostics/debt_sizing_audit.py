"""Debt-sizing audit helpers for C3B3D2B7.

This module is diagnostics-only. Source vectors are accepted as caller-supplied
review oracles and never become runtime calculation inputs.
"""
from __future__ import annotations

from typing import Any


def _delta(actual: float | None, expected: float | None) -> float | None:
    if actual is None or expected is None:
        return None
    return actual - expected


def _safe_price(revenue_keur: float, production_mwh: float) -> float:
    if abs(production_mwh) < 1e-12:
        return 0.0
    return revenue_keur * 1000.0 / production_mwh


def _vector_value(values: list | tuple | None, period_index: int) -> float | None:
    if values is None or period_index >= len(values):
        return None
    value = values[period_index]
    return None if value is None else float(value)


def build_debt_sizing_audit(
    result: Any,
    *,
    source_debt_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return period-by-period debt-sizing evidence.

    The audit is intentionally separate from the Base Performance reconciliation:
    bank production, bank CFADS, sizing DSCR and debt service capacity are lender
    sizing evidence, not Base/equity performance lines.
    """
    if result.debt_sizing is None or result.senior_debt is None:
        raise ValueError("DEBT_SIZING_AUDIT_REQUIRES_DEBT_SIZING_AND_SENIOR_DEBT")

    source_period_vectors = (
        source_debt_truth.get("workstream_b", {}).get("period_vectors", {})
        if source_debt_truth
        else {}
    )
    source_ds20 = (
        source_debt_truth.get("workstream_a", {}).get("ds_row20_cfads", {}).get("period_values_keur")
        if source_debt_truth
        else None
    )
    source_target_dscr = source_period_vectors.get("row22_dscr", {}).get("period_values")
    source_day_fraction = source_period_vectors.get("row6_day_frac", {}).get("period_values")
    source_debt_capacity = source_period_vectors.get("row23_avail", {}).get("period_values")
    source_actual_service = source_period_vectors.get("row46_sd_service", {}).get("period_values")
    if source_actual_service is None:
        source_actual_service = source_debt_capacity
    source_opening = source_period_vectors.get("row61_opening", {}).get("period_values")
    source_principal = source_period_vectors.get("row63_principal", {}).get("period_values")
    source_interest = source_period_vectors.get("row64_interest", {}).get("period_values")
    source_closing = source_period_vectors.get("row67_closing", {}).get("period_values")
    source_total_debt = (
        source_debt_truth.get("workstream_b", {}).get("ds_d51_total_debt", {}).get("value_keur")
        if source_debt_truth
        else None
    )
    source_components = (
        source_debt_truth.get("workstream_a", {}).get("components", {})
        if source_debt_truth
        else {}
    )
    source_cf_row79 = (
        source_debt_truth.get("workstream_a", {})
        .get("cf_row79_free_cash_flow_for_banks", {})
        .get("period_values_keur")
        if source_debt_truth
        else None
    )
    source_cf_revenue = source_components.get("cf_row23_revenues", {}).get("period_values_keur")
    source_cf_opex = source_components.get("cf_row49_opex", {}).get("period_values_keur")
    source_cf_interest_income = source_components.get("cf_row76_interest_income", {}).get("period_values_keur")
    source_cf_cit = source_components.get("cf_row77_cit", {}).get("period_values_keur")

    periods_by_idx = {p.period_index: p for p in result.periods}
    debt_sizing_by_idx = {
        idx: pos for pos, idx in enumerate(result.debt_sizing.period_indices)
    }
    senior_by_idx = {
        idx: pos for pos, idx in enumerate(result.senior_debt.period_indices)
    }

    rows: list[dict[str, Any]] = []
    for idx in result.debt_sizing.period_indices:
        ds_pos = debt_sizing_by_idx[idx]
        sd_pos = senior_by_idx.get(idx)
        period = periods_by_idx[idx]
        has_senior_schedule = sd_pos is not None
        finco_bank_production = result.debt_sizing.bank_production_mwh[ds_pos]
        finco_bank_revenue = result.debt_sizing.bank_revenue_keur[ds_pos]
        finco_bank_opex = result.debt_sizing.bank_opex_keur[ds_pos]
        finco_bank_ebitda = result.debt_sizing.bank_ebitda_keur[ds_pos]
        finco_bank_cit = result.debt_sizing.bank_cash_tax_keur[ds_pos]
        finco_bank_cfads = result.debt_sizing.bank_cfads_keur[ds_pos]
        finco_bank_price = _safe_price(finco_bank_revenue, finco_bank_production)
        finco_target_dscr = result.debt_sizing.bank_sizing_dscr[ds_pos]
        finco_allowed_capacity = (
            finco_bank_cfads / finco_target_dscr
            if finco_target_dscr and finco_target_dscr > 0.0
            else None
        )
        finco_debt_service = (
            result.senior_debt.senior_debt_service_keur[sd_pos]
            if sd_pos is not None
            else 0.0
        )
        source_cfads = _vector_value(source_ds20, idx)
        source_base_cfads = _vector_value(source_cf_row79, idx)
        source_dscr = _vector_value(source_target_dscr, idx)
        source_capacity = _vector_value(source_debt_capacity, idx)
        source_revenue = _vector_value(source_cf_revenue, idx)
        source_opex_signed = _vector_value(source_cf_opex, idx)
        source_opex_abs = -source_opex_signed if source_opex_signed is not None else None
        source_interest_income = _vector_value(source_cf_interest_income, idx)
        source_cit_signed = _vector_value(source_cf_cit, idx)
        source_cash_tax_abs = -source_cit_signed if source_cit_signed is not None else None
        rows.append(
            {
                "period": idx,
                "date": str(period.period_end),
                "excel_bank_production": None,
                "finco_bank_production": finco_bank_production,
                "bank_production_delta": None,
                "excel_bank_price": None,
                "finco_bank_price": finco_bank_price,
                "bank_price_delta": None,
                "excel_cf_row23_base_revenue": source_revenue,
                "excel_bank_revenue": None,
                "finco_bank_revenue": finco_bank_revenue,
                "bank_revenue_delta": None,
                "excel_cf_row49_base_opex_abs": source_opex_abs,
                "excel_bank_opex": None,
                "finco_bank_opex": finco_bank_opex,
                "bank_opex_delta": None,
                "excel_bank_ebitda": None,
                "finco_bank_ebitda": finco_bank_ebitda,
                "bank_ebitda_delta": None,
                "excel_cf_row77_base_cash_tax_abs": source_cash_tax_abs,
                "excel_bank_cit": None,
                "finco_bank_cit": finco_bank_cit,
                "bank_cit_delta": None,
                "excel_cf_row76_interest_income": source_interest_income,
                "excel_cf_row79_base_cfads": source_base_cfads,
                "base_vs_bank_source_cfads_delta": _delta(source_base_cfads, source_cfads),
                "excel_bank_cfads": source_cfads,
                "finco_bank_cfads": finco_bank_cfads,
                "bank_cfads_delta": _delta(finco_bank_cfads, source_cfads),
                "excel_target_dscr": source_dscr,
                "finco_target_dscr": finco_target_dscr,
                "target_dscr_delta": _delta(finco_target_dscr, source_dscr),
                "excel_day_fraction": _vector_value(source_day_fraction, idx),
                "finco_day_fraction": period.day_fraction,
                "day_fraction_delta": _delta(period.day_fraction, _vector_value(source_day_fraction, idx)),
                "excel_annual_senior_rate": None,
                "finco_annual_senior_rate": None,
                "annual_senior_rate_delta": None,
                "excel_allowed_debt_service_capacity": source_capacity,
                "finco_allowed_debt_service_capacity": finco_allowed_capacity,
                "allowed_debt_service_capacity_delta": _delta(finco_allowed_capacity, source_capacity),
                "excel_actual_senior_debt_service": _vector_value(source_actual_service, idx),
                "finco_actual_senior_debt_service": finco_debt_service,
                "actual_senior_debt_service_delta": _delta(
                    finco_debt_service, _vector_value(source_actual_service, idx)
                ),
                "excel_senior_opening": (
                    _vector_value(source_opening, idx) if has_senior_schedule else None
                ),
                "finco_senior_opening": (
                    result.senior_debt.senior_debt_opening_keur[sd_pos]
                    if sd_pos is not None
                    else 0.0
                ),
                "excel_senior_interest": (
                    _vector_value(source_interest, idx) if has_senior_schedule else None
                ),
                "finco_senior_interest": (
                    result.senior_debt.senior_interest_keur[sd_pos]
                    if sd_pos is not None
                    else 0.0
                ),
                "excel_senior_principal": (
                    _vector_value(source_principal, idx) if has_senior_schedule else None
                ),
                "finco_senior_principal": (
                    result.senior_debt.senior_principal_keur[sd_pos]
                    if sd_pos is not None
                    else 0.0
                ),
                "excel_senior_closing": (
                    _vector_value(source_closing, idx) if has_senior_schedule else None
                ),
                "finco_senior_closing": (
                    result.senior_debt.senior_debt_closing_keur[sd_pos]
                    if sd_pos is not None
                    else 0.0
                ),
            }
        )

    first_divergence = next(
        (
            row for row in rows
            if row["excel_bank_cfads"] is not None
            and abs(row["bank_cfads_delta"] or 0.0) > 1e-6
        ),
        None,
    )
    max_bank_cfads = max(
        (
            row for row in rows
            if row["bank_cfads_delta"] is not None
        ),
        key=lambda row: abs(row["bank_cfads_delta"]),
        default=None,
    )
    return {
        "classification": "DEBT_SIZING_AUDIT_DIAGNOSTIC_ONLY",
        "rows": rows,
        "late_horizon_residual_classification": (
            "BANK_DS_ROW20_REMAINS_SOURCE_CFADS_AUTHORITY; "
            "CF_ROW79_COMPONENTS_ARE_BASE_CASE_EVIDENCE_NOT_BANK_COMPONENT_REPLAY"
        ),
        "source_unavailable_components": (
            "Excel Bank Production",
            "Excel Bank Price",
            "Excel Bank Revenue",
            "Excel Bank OPEX",
            "Excel Bank EBITDA",
            "Excel Bank CIT",
            "Excel Annual Senior Rate",
        ),
        "source_available_components": (
            "Excel Bank CFADS / DS row20 / Macro50 authority",
            "Excel CF row79 Base CFADS",
            "Excel CF row23/49/76/77 Base components",
            "Excel Target DSCR",
            "Excel Day Fraction",
            "Excel Debt Service Capacity",
            "Excel Senior Opening",
            "Excel Senior Interest",
            "Excel Senior Principal",
            "Excel Senior Closing",
        ),
        "excel_senior_debt_keur": source_total_debt,
        "finco_senior_debt_keur": result.senior_debt.debt_size_keur,
        "debt_residual_keur": _delta(result.senior_debt.debt_size_keur, source_total_debt),
        "first_bank_case_causal_divergence": (
            {
                "period": first_divergence["period"],
                "line": "Bank CFADS / late-horizon source residual boundary",
                "cause": "BANK_TAX_LOSS_COMPATIBILITY_PROVEN_LATE_HORIZON_CFADS_RESIDUAL_REMAINS",
                "excel": first_divergence["excel_bank_cfads"],
                "finco": first_divergence["finco_bank_cfads"],
                "delta": first_divergence["bank_cfads_delta"],
            }
            if first_divergence
            else None
        ),
        "max_bank_case_causal_divergence": (
            {
                "period": max_bank_cfads["period"],
                "line": "Bank CFADS / DS row20 late-horizon residual",
                "cause": (
                    "SOURCE_BANK_COMPONENTS_BEYOND_DS_ROW20_NOT_EXTRACTED; "
                    "PRODUCTION_CHANGE_NOT_JUSTIFIED_WITHOUT_UPSTREAM_BANK_COMPONENT_SOURCE_BRIDGE"
                ),
                "excel": max_bank_cfads["excel_bank_cfads"],
                "finco": max_bank_cfads["finco_bank_cfads"],
                "delta": max_bank_cfads["bank_cfads_delta"],
            }
            if max_bank_cfads
            else None
        ),
    }
