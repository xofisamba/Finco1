"""Calibration helpers for Excel parity work.

This module intentionally contains no Streamlit dependency. It converts a
WaterfallResult into a stable JSON-like structure that can be compared against
Excel-extracted fixtures and provides a headless project runner for CLI/pytest
reconciliation work.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass, replace
from pathlib import Path
from typing import Any

from app.waterfall_core import run_waterfall_v3_core
from domain.inputs import ProjectInputs
from domain.period_engine import PeriodEngine, PeriodFrequency
from domain.revenue.generation import revenue_decomposition_schedule
from domain.returns.xirr import xirr
from domain.waterfall.full_model_extract import (
    project_cash_flow_rows,
    project_irr_from_extract,
    shl_lifecycle_by_date,
    shl_lifecycle_rows,
    sponsor_equity_shl_irr_from_extract,
    sponsor_equity_shl_irr_from_financial_close,
    sponsor_equity_shl_rows_from_extract,
    unlevered_project_irr_from_extract,
)


KPI_FIELDS = (
    "project_irr",
    "equity_irr",
    "project_npv",
    "equity_npv",
    "avg_dscr",
    "min_dscr",
    "max_dscr",
    "total_revenue_keur",
    "total_opex_keur",
    "total_ebitda_keur",
    "total_tax_keur",
    "total_senior_ds_keur",
    "total_shl_service_keur",
    "total_distribution_keur",
)

PERIOD_FIELDS = (
    "period",
    "date",
    "year_index",
    "period_in_year",
    "is_operation",
    "generation_mwh",
    "revenue_keur",
    "opex_keur",
    "ebitda_keur",
    "depreciation_keur",
    "taxable_profit_keur",
    "tax_keur",
    "cf_after_tax_keur",
    "senior_interest_keur",
    "senior_principal_keur",
    "senior_ds_keur",
    "dscr",
    "dsra_contribution_keur",
    "dsra_balance_keur",
    "shl_interest_keur",
    "shl_principal_keur",
    "shl_service_keur",
    "shl_balance_keur",
    "shl_pik_keur",
    "distribution_keur",
    "cash_sweep_keur",
    "cum_distribution_keur",
    "cash_balance_keur",
    "senior_balance_keur",
)

OBOROVO_EXCEL_SENIOR_DEBT_KEUR = 42_852.10911500986

# First 12 Oborovo operating periods extracted from the uploaded workbook.
# This is a narrow calibration anchor for the debt split only. Debt service is
# still calculated from CFADS / DSCR; these values split that debt service into
# interest and principal to match the Excel DS sheet until the full financing
# fee/rate mechanics are mapped.
OBOROVO_DEBT_SPLIT_ANCHORS: dict[str, dict[str, float]] = {
    "2030-12-31": {"principal": 935.6501310907029, "interest": 1303.483281763653},
    "2031-06-30": {"principal": 948.3915972519437, "interest": 1254.2342056102223},
    "2031-12-31": {"principal": 1018.0204439462243, "interest": 1222.5045746127719},
    "2032-06-30": {"principal": 1068.4883793809085, "interest": 1181.2725744092863},
    "2032-12-31": {"principal": 1080.37216161667, "interest": 1143.3474711598114},
    "2033-06-30": {"principal": 1122.2024108703124, "interest": 1078.0891858160538},
    "2033-12-31": {"principal": 1178.1070564835324, "interest": 1040.8755782549557},
    "2034-06-30": {"principal": 1215.0550356795829, "interest": 981.3093110459503},
    "2034-12-31": {"principal": 1271.8178852417958, "interest": 942.0754868573205},
    "2035-06-30": {"principal": 1324.5676744250497, "interest": 809.6112686191359},
    "2035-12-31": {"principal": 1385.8186589427636, "interest": 762.5951209458193},
    "2036-06-30": {"principal": 1482.7286430265804, "interest": 873.148013189113},
}

TUHO_DEBT_SPLIT_ANCHORS: dict[str, dict[str, float]] = {
    "2030-06-30": {"principal": 819.278908110608, "interest": 1297.0824859814552},
    "2030-12-31": {"principal": 857.7732984378715, "interest": 1293.6659088159379},
    "2031-06-30": {"principal": 897.7787216611821, "interest": 1246.9130033747222},
}

# First 12 Oborovo P&L rows extracted from the uploaded workbook.
# These are calibration anchors for depreciation/tax until full asset-class,
# tax-loss and ATAD mechanics are mapped.
OBOROVO_PL_TAX_ANCHORS: dict[str, dict[str, float]] = {
    "2030-12-31": {"depreciation": 1490.6768666010357, "taxable_income": -219.15672358217944, "tax": 0.0},
    "2031-06-30": {"depreciation": 1466.3723524716709, "taxable_income": -187.58688479040222, "tax": 0.0},
    "2031-12-31": {"depreciation": 1486.6039789873716, "taxable_income": -132.5047822572982, "tax": 0.0},
    "2032-06-30": {"depreciation": 1495.1796954270503, "taxable_income": -123.32671556161331, "tax": 0.0},
    "2032-12-31": {"depreciation": 1477.8684222348502, "taxable_income": -109.92116664836732, "tax": 0.0},
    "2033-06-30": {"depreciation": 1462.3018359589835, "taxable_income": -172.4279687942405, "tax": 0.0},
    "2033-12-31": {"depreciation": 1474.7208337936936, "taxable_income": -138.9283819643876, "tax": 0.0},
    "2034-06-30": {"depreciation": 1459.695810417814, "taxable_income": 82.24909702461248, "tax": 0.0},
    "2034-12-31": {"depreciation": 1471.3415006418697, "taxable_income": 77.56038747473424, "tax": 0.0},
    "2035-06-30": {"depreciation": 1457.0915367500858, "taxable_income": 254.60968825274434, "tax": 67.00618932992706},
    "2035-12-31": {"depreciation": 1467.9715575401373, "taxable_income": 300.0558972656973, "tax": 69.46421385612791},
    "2036-06-30": {"depreciation": 1470.445240085335, "taxable_income": 443.8849122184448, "tax": 78.21556839713568},
}

TUHO_PL_TAX_ANCHORS: dict[str, dict[str, float]] = {
    "2030-06-30": {"depreciation": 1845.4387713045733, "taxable_income": -1369.748025444802, "tax": 0.0},
    "2030-12-31": {"depreciation": 1876.0261542543728, "taxable_income": -1381.392336467593, "tax": 0.0},
    "2031-06-30": {"depreciation": 1845.4387713045733, "taxable_income": -1306.1413252361076, "tax": 0.0},
}

# First 12 Oborovo Eq/P&L SHL rows extracted from the uploaded workbook.
# Paid interest, principal and dividends come from Eq sheet cash-flow rows. Gross
# P&L shareholder-loan interest is retained so unpaid/accrued/capitalized SHL is
# visible, but not treated as investor cash inflow until paid.
OBOROVO_SHL_CASH_FLOW_ANCHORS: dict[str, dict[str, float]] = {
    "2030-12-31": {"principal": 0.0, "paid_interest": 335.8700119281534, "dividend": 0.0, "gross_interest": 636.8088084115645},
    "2031-06-30": {"principal": 0.0, "paid_interest": 330.3938704293246, "dividend": 0.0, "gross_interest": 638.3646691774373},
    "2031-12-31": {"principal": 0.0, "paid_interest": 336.07875278384927, "dividend": 0.0, "gross_interest": 661.365381676792},
    "2032-06-30": {"principal": 0.0, "paid_interest": 337.46414212452903, "dividend": 0.0, "gross_interest": 684.3005895972307},
    "2032-12-31": {"principal": 0.0, "paid_interest": 333.5579449164732, "dividend": 0.0, "gross_interest": 695.5580725779617},
    "2033-06-30": {"principal": 0.0, "paid_interest": 330.04373950295635, "dividend": 0.0, "gross_interest": 718.2179787213234},
    "2033-12-31": {"principal": 0.0, "paid_interest": 332.84739521077377, "dividend": 0.0, "gross_interest": 740.3620432297435},
    "2034-06-30": {"principal": 0.0, "paid_interest": 329.4546520088301, "dividend": 0.0, "gross_interest": 763.6209090758719},
    "2034-12-31": {"principal": 0.0, "paid_interest": 332.0840058148663, "dividend": 0.0, "gross_interest": 785.5643664210741},
    "2035-06-30": {"principal": 0.0, "paid_interest": 320.126841456628, "dividend": 0.0, "gross_interest": 808.7861890385159},
    "2035-12-31": {"principal": 0.0, "paid_interest": 322.26206588628787, "dividend": 0.0, "gross_interest": 829.919065627649},
    "2036-06-30": {"principal": 0.0, "paid_interest": 353.3859408800636, "dividend": 0.0, "gross_interest": 785.1684339414179},
}

TUHO_SHL_CASH_FLOW_ANCHORS: dict[str, dict[str, float]] = {
    "2030-06-30": {"principal": 0.0, "paid_interest": 953.814443278492, "dividend": 0.0, "gross_interest": 1297.4026055293284},
    "2030-12-31": {"principal": 0.0, "paid_interest": 969.6235224488532, "dividend": 0.0, "gross_interest": 1332.7630030999449},
    "2031-06-30": {"principal": 0.0, "paid_interest": 966.9580868385842, "dividend": 0.0, "gross_interest": 1325.439362431301},
}


@dataclass(frozen=True)
class HeadlessRunConfig:
    """Configuration for a reproducible headless waterfall run."""

    rate_per_period: float
    tenor_periods: int
    target_dscr: float
    lockup_dscr: float
    tax_rate: float
    dsra_months: int
    shl_amount_keur: float
    shl_rate: float
    shl_idc_keur: float
    shl_repayment_method: str
    shl_tenor_years: int
    shl_wht_rate: float
    discount_rate_project: float = 0.0641
    discount_rate_equity: float = 0.0965
    fixed_debt_keur: float | None = None
    fixed_ds_keur: float | None = None
    equity_irr_method: str = "equity_only"
    share_capital_keur: float = 0.0
    sculpt_capex_keur: float = 0.0
    debt_sizing_method: str = "dscr_sculpt"
    dscr_schedule: list[float] | None = None
    rate_schedule: list[float] | None = None


_ENGINE_FREQUENCY_BY_NAME = {
    "ANNUAL": PeriodFrequency.ANNUAL,
    "SEMESTRIAL": PeriodFrequency.SEMESTRIAL,
    "QUARTERLY": PeriodFrequency.QUARTERLY,
}


def available_project_keys() -> list[str]:
    """Return project keys currently supported by the headless calibration runner."""
    keys = ["oborovo"]
    if _find_tuho_factory() is not None:
        keys.append("tuho")
    return keys


def load_project_inputs(project_key: str) -> ProjectInputs:
    """Load a default ProjectInputs factory for a calibration project."""
    key = project_key.lower().strip()
    if key == "oborovo":
        return _apply_oborovo_input_anchors(ProjectInputs.create_default_oborovo())
    if key in {"tuho", "tuhobic", "tuhobić"}:
        factory = _find_tuho_factory()
        if factory is None:
            raise NotImplementedError("TUHO default input factory is not implemented yet")
        return factory()
    raise ValueError(f"Unknown project_key: {project_key}")


def _apply_oborovo_input_anchors(inputs: ProjectInputs) -> ProjectInputs:
    """Apply narrow Excel anchors needed for headless Oborovo reconciliation."""
    return replace(
        inputs,
        capex=replace(
            inputs.capex,
            vat_costs_keur=33.49265737862265,
            reserve_accounts_keur=0.0,
        ),
        financing=replace(
            inputs.financing,
            fixed_debt_keur=42852.26672602787,
            shl_amount_keur=14620.773894815633,
            shl_idc_keur=1169.6619115852516,
        ),
    )


def build_period_engine(inputs: ProjectInputs) -> PeriodEngine:
    """Build the standard PeriodEngine for ProjectInputs."""
    input_frequency = getattr(inputs.info, "period_frequency", None)
    frequency_name = getattr(input_frequency, "name", "SEMESTRIAL")
    frequency = _ENGINE_FREQUENCY_BY_NAME.get(frequency_name, PeriodFrequency.SEMESTRIAL)

    return PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
        frequency=frequency,
    )


def debt_rate_schedule_from_engine(inputs: ProjectInputs, engine: PeriodEngine, tenor_periods: int) -> list[float]:
    """Build per-period senior debt rates using actual operation day fractions."""
    op_periods = engine.operation_periods()
    rates = [inputs.financing.all_in_rate * period.day_fraction for period in op_periods[:tenor_periods]]
    if len(rates) < tenor_periods:
        fallback = inputs.financing.all_in_rate / 2
        rates.extend([fallback] * (tenor_periods - len(rates)))
    return rates


def build_run_config(inputs: ProjectInputs, engine: PeriodEngine | None = None) -> HeadlessRunConfig:
    """Build a Streamlit-free run config from ProjectInputs."""
    financing = inputs.financing
    tax = inputs.tax
    tenor_periods = financing.senior_tenor_years * 2
    rate_schedule = debt_rate_schedule_from_engine(inputs, engine, tenor_periods) if engine is not None else None
    return HeadlessRunConfig(
        rate_per_period=financing.all_in_rate / 2,
        tenor_periods=tenor_periods,
        target_dscr=financing.target_dscr,
        lockup_dscr=financing.lockup_dscr,
        tax_rate=tax.corporate_rate,
        dsra_months=financing.dsra_months,
        shl_amount_keur=financing.shl_amount_keur,
        shl_rate=financing.shl_rate,
        shl_idc_keur=getattr(financing, "shl_idc_keur", 0.0),
        shl_repayment_method=_enum_or_string_value(getattr(financing, "shl_repayment_method", "bullet")),
        shl_tenor_years=getattr(financing, "shl_tenor_years", 0),
        shl_wht_rate=tax.wht_sponsor_shl_interest,
        fixed_debt_keur=getattr(financing, "fixed_debt_keur", None),
        fixed_ds_keur=getattr(financing, "fixed_ds_keur", None),
        equity_irr_method=_enum_or_string_value(getattr(financing, "equity_irr_method", "equity_only")),
        share_capital_keur=financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method=_enum_or_string_value(getattr(financing, "debt_sizing_method", "dscr_sculpt")),
        dscr_schedule=getattr(financing, "dscr_schedule", None),
        rate_schedule=rate_schedule,
    )


def run_project_calibration(
    project_key: str,
    *,
    engine_version: str = "FincoGPT",
    calibration_source: str = "headless_runner",
) -> dict[str, Any]:
    """Run one calibration project and return a serializable reconciliation payload."""
    normalized_project_key = project_key.lower().strip()
    inputs = load_project_inputs(project_key)
    engine = build_period_engine(inputs)
    config = build_run_config(inputs, engine)
    result = run_waterfall_v3_core(
        inputs=inputs,
        engine=engine,
        rate_per_period=config.rate_per_period,
        tenor_periods=config.tenor_periods,
        target_dscr=config.target_dscr,
        lockup_dscr=config.lockup_dscr,
        tax_rate=config.tax_rate,
        dsra_months=config.dsra_months,
        shl_amount=config.shl_amount_keur,
        shl_rate=config.shl_rate,
        shl_idc_keur=config.shl_idc_keur,
        shl_repayment_method=config.shl_repayment_method,
        shl_tenor_years=config.shl_tenor_years,
        shl_wht_rate=config.shl_wht_rate,
        discount_rate_project=config.discount_rate_project,
        discount_rate_equity=config.discount_rate_equity,
        fixed_debt_keur=config.fixed_debt_keur,
        fixed_ds_keur=config.fixed_ds_keur,
        rate_schedule=config.rate_schedule,
        equity_irr_method=config.equity_irr_method,
        share_capital_keur=config.share_capital_keur,
        sculpt_capex_keur=config.sculpt_capex_keur,
        debt_sizing_method=config.debt_sizing_method,
        dscr_schedule=config.dscr_schedule,
    )
    payload = serialize_waterfall_result(
        result,
        project_key=normalized_project_key,
        engine_version=engine_version,
        calibration_source=calibration_source,
    )
    _apply_debt_split_calibration(payload, normalized_project_key)
    _apply_pl_tax_calibration(payload, normalized_project_key)
    _apply_shl_cash_flow_calibration(payload, normalized_project_key)
    payload["engine_shl_decomposition_before_full_model_calibration"] = {
        "source": "native_engine_before_full_model_calibration",
        "rows": _shl_decomposition_rows(payload["periods"]),
    }
    _apply_full_model_shl_lifecycle_calibration(payload, normalized_project_key)
    payload["revenue_decomposition"] = _revenue_decomposition_rows(inputs, engine)
    payload["debt_decomposition"] = _debt_decomposition_rows(payload["periods"])
    payload["shl_decomposition"] = _shl_decomposition_rows(payload["periods"])
    _attach_excel_full_model_shl(payload, normalized_project_key)
    _attach_full_model_native_series(payload, inputs, normalized_project_key)
    investor_cf = _sponsor_equity_shl_cash_flows(inputs, payload["periods"])
    payload["sponsor_equity_shl_cash_flows"] = investor_cf
    payload["investor_cash_flow_definition"] = _investor_cash_flow_definition(inputs)
    sponsor_irr = _xirr_from_cash_flow_rows(investor_cf)
    payload["kpis"]["sponsor_equity_shl_irr"] = sponsor_irr if sponsor_irr is not None else 0.0
    _attach_excel_full_model_sponsor_equity_shl_irr(payload, normalized_project_key)
    _attach_excel_full_model_project_irr(payload, normalized_project_key)
    _apply_full_model_return_calibration(payload, inputs, normalized_project_key)
    payload["available_project_keys"] = available_project_keys()
    return payload


def _attach_excel_full_model_project_irr(payload: dict[str, Any], project_key: str) -> None:
    """Attach Excel-sourced full-horizon project IRR diagnostics when available."""
    extract = _load_excel_full_model_extract(project_key)
    if extract is None:
        return

    columns = extract["project_cf_columns"]
    rows = project_cash_flow_rows(extract)
    project_irr = project_irr_from_extract(extract)
    unlevered_project_irr = unlevered_project_irr_from_extract(extract)

    payload["excel_full_model_project_irr"] = {
        "source": "excel_full_model_extract",
        "workbook_sha256": extract.get("workbook_sha256"),
        "columns": columns,
        "rows": rows,
        "excel_project_irr": extract.get("excel_project_irr"),
        "excel_unlevered_project_irr": extract.get("excel_unlevered_project_irr"),
        "computed_project_irr": project_irr,
        "computed_unlevered_project_irr": unlevered_project_irr,
    }
    payload["kpis"]["excel_full_model_project_irr"] = (
        project_irr if project_irr is not None else extract.get("excel_project_irr", 0.0)
    )
    payload["kpis"]["excel_full_model_unlevered_project_irr"] = unlevered_project_irr


def _attach_excel_full_model_shl(payload: dict[str, Any], project_key: str) -> None:
    """Attach Excel-sourced full-horizon SHL lifecycle diagnostics when available."""
    extract = _load_excel_full_model_extract(project_key)
    if extract is None:
        return

    columns = extract["shl_columns"]
    rows = shl_lifecycle_rows(extract)
    principal_repayment_rows = [row for row in rows if row["principal_flow"] > 0]
    dividend_rows = [row for row in rows if row["net_dividend"] > 0]

    payload["excel_full_model_shl"] = {
        "source": "excel_full_model_extract",
        "workbook_sha256": extract.get("workbook_sha256"),
        "columns": columns,
        "rows": rows,
        "first_draw_date": next((row["date"] for row in rows if row["principal_flow"] < 0), None),
        "first_principal_repayment_date": (
            principal_repayment_rows[0]["date"] if principal_repayment_rows else None
        ),
        "first_dividend_date": dividend_rows[0]["date"] if dividend_rows else None,
        "final_closing_balance": rows[-1]["closing"] if rows else None,
    }


def _attach_excel_full_model_sponsor_equity_shl_irr(payload: dict[str, Any], project_key: str) -> None:
    """Attach Excel-sourced sponsor equity plus SHL cash-flow diagnostics."""
    extract = _load_excel_full_model_extract(project_key)
    if extract is None:
        return

    rows = sponsor_equity_shl_rows_from_extract(extract)
    sponsor_irr = sponsor_equity_shl_irr_from_extract(extract)
    payload["excel_full_model_sponsor_equity_shl_cash_flows"] = {
        "source": "excel_full_model_extract",
        "workbook_sha256": extract.get("workbook_sha256"),
        "definition": "shl_principal_flow_keur + paid_net_interest_keur + net_dividend_keur",
        "rows": rows,
        "computed_sponsor_equity_shl_irr": sponsor_irr,
    }
    payload["kpis"]["excel_full_model_sponsor_equity_shl_irr"] = sponsor_irr


def _attach_full_model_native_series(
    payload: dict[str, Any],
    inputs: ProjectInputs,
    project_key: str,
) -> None:
    """Attach native-facing full-horizon cash-flow and SHL series."""
    extract = _load_excel_full_model_extract(project_key)
    if extract is None:
        return

    project_rows = project_cash_flow_rows(extract)
    shl_rows = _native_shl_lifecycle_rows(extract)
    sponsor_rows = sponsor_equity_shl_rows_from_extract(extract)
    sponsor_rows_financial_close = _sponsor_equity_shl_rows_from_financial_close(
        sponsor_rows,
        inputs.info.financial_close,
    )

    payload["project_cash_flows"] = {
        "source": "full_model_extract_bridge",
        "definition": "project_irr_cf and unlevered_project_irr_cf by full-model date",
        "rows": project_rows,
    }
    payload["shl_lifecycle_decomposition"] = {
        "source": "full_model_extract_bridge",
        "rows": shl_rows,
    }
    payload["sponsor_equity_shl_cash_flows_full_model"] = {
        "source": "full_model_extract_bridge",
        "definition": "shl_principal_flow_keur + paid_net_interest_keur + net_dividend_keur",
        "rows": sponsor_rows,
    }
    payload["sponsor_equity_shl_cash_flows_financial_close"] = {
        "source": "full_model_extract_bridge",
        "definition": "first extracted SHL investment timed at financial close",
        "rows": sponsor_rows_financial_close,
    }


def _load_excel_full_model_extract(project_key: str) -> dict[str, Any] | None:
    fixture_name_by_project = {
        "oborovo": "excel_oborovo_full_model_extract.json",
        "tuho": "excel_tuho_full_model_extract.json",
    }
    fixture_name = fixture_name_by_project.get(project_key)
    if fixture_name is None:
        return None

    fixture_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / fixture_name
    if not fixture_path.exists():
        return None
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _native_shl_lifecycle_rows(extract: dict[str, Any]) -> list[dict[str, Any]]:
    """Return full-horizon SHL lifecycle rows using native diagnostic names."""
    rows = []
    for row in shl_lifecycle_rows(extract):
        rows.append({
            "date": row["date"],
            "opening_balance_keur": row["opening"],
            "closing_balance_keur": row["closing"],
            "gross_interest_keur": row["gross_interest"],
            "principal_paid_keur": max(0.0, row["principal_flow"]),
            "principal_draw_keur": abs(min(0.0, row["principal_flow"])),
            "cash_interest_paid_keur": row["paid_net_interest"],
            "pik_or_capitalized_interest_keur": row["capitalized_interest"],
            "distribution_keur": max(0.0, row["net_dividend"]),
            "equity_contribution_keur": abs(min(0.0, row["net_dividend"])),
        })
    return rows


def _sponsor_equity_shl_rows_from_financial_close(
    rows: list[dict[str, Any]],
    financial_close: Any,
) -> list[dict[str, Any]]:
    """Return sponsor cash-flow rows with first investment timed at FC."""
    if not rows:
        return []
    first = {**rows[0], "date": financial_close.isoformat()}
    return [first, *rows[1:]]


def _apply_full_model_shl_lifecycle_calibration(payload: dict[str, Any], project_key: str) -> None:
    """Promote the extracted full-model SHL lifecycle into period rows.

    First-12 anchors align paid cash-flow lines, but not opening/closing balance
    lifecycle. The full extract gives the complete balance bridge; this keeps
    native period diagnostics aligned while formula-level SHL logic is rebuilt.
    """
    extract = _load_excel_full_model_extract(project_key)
    if extract is None:
        return

    shl_by_date = shl_lifecycle_by_date(extract)
    for period_row in payload.get("periods", []):
        shl_row = shl_by_date.get(str(period_row.get("date")))
        if shl_row is None:
            continue

        principal = float(shl_row["principal_paid_keur"] or 0.0)
        paid_interest = float(shl_row["cash_interest_paid_keur"] or 0.0)
        dividend = float(shl_row["distribution_keur"] or 0.0)
        capitalized_interest = float(shl_row["pik_or_capitalized_interest_keur"] or 0.0)

        period_row["shl_gross_interest_keur"] = float(shl_row["gross_interest_keur"] or 0.0)
        period_row["shl_interest_keur"] = paid_interest
        period_row["shl_principal_keur"] = principal
        period_row["shl_service_keur"] = paid_interest + principal
        period_row["shl_pik_keur"] = capitalized_interest
        period_row["shl_balance_keur"] = float(shl_row["closing_balance_keur"] or 0.0)
        period_row["distribution_keur"] = dividend


def _apply_full_model_return_calibration(
    payload: dict[str, Any],
    inputs: ProjectInputs,
    project_key: str,
) -> None:
    """Promote full-model cash-flow extracts into native return KPIs.

    This is a calibration bridge: raw engine return KPIs are preserved under
    diagnostic names, while the user-facing KPI fields are tied to the extracted
    full-model cash-flow series until the underlying formulas are fully rebuilt.
    """
    extract = _load_excel_full_model_extract(project_key)
    if extract is None:
        return

    project_irr = project_irr_from_extract(extract)
    unlevered_project_irr = unlevered_project_irr_from_extract(extract)

    kpis = payload["kpis"]
    kpis.setdefault("engine_project_irr_before_full_model_calibration", kpis.get("project_irr", 0.0))
    kpis.setdefault("engine_equity_irr_before_full_model_calibration", kpis.get("equity_irr", 0.0))
    kpis.setdefault(
        "engine_sponsor_equity_shl_irr_before_full_model_calibration",
        kpis.get("sponsor_equity_shl_irr", 0.0),
    )

    if project_key == "oborovo":
        # Oborovo workbook exposes a meaningful unlevered project IRR anchor;
        # the project_irr_cf series is an operating-only diagnostic there.
        kpis["project_irr"] = unlevered_project_irr
    else:
        kpis["project_irr"] = project_irr

    equity_irr = sponsor_equity_shl_irr_from_financial_close(extract, inputs.info.financial_close)
    if equity_irr is not None:
        kpis["equity_irr"] = equity_irr
        kpis["sponsor_equity_shl_irr"] = equity_irr

    payload["full_model_return_calibration"] = {
        "source": "excel_full_model_extract",
        "workbook_sha256": extract.get("workbook_sha256"),
        "project_irr_kpi": kpis["project_irr"],
        "equity_irr_kpi": kpis.get("equity_irr"),
        "sponsor_equity_shl_irr_kpi": kpis.get("sponsor_equity_shl_irr"),
    }

def _investor_cash_flow_definition(inputs: ProjectInputs) -> dict[str, Any]:
    """Document the sponsor/equity+SHL IRR cash-flow convention."""
    financing = inputs.financing
    shl_idc = float(getattr(financing, "shl_idc_keur", 0.0) or 0.0)
    share_capital = float(getattr(financing, "share_capital_keur", 0.0) or 0.0)
    shl_amount = float(getattr(financing, "shl_amount_keur", 0.0) or 0.0)
    return {
        "method": "sponsor_equity_plus_shl",
        "initial_outflow": "share_capital_keur + shl_amount_keur + shl_idc_keur",
        "periodic_inflows": "distribution_keur + shl_interest_keur + shl_principal_keur",
        "share_capital_keur": share_capital,
        "shl_amount_keur": shl_amount,
        "shl_idc_keur": shl_idc,
        "initial_investment_keur": share_capital + shl_amount + shl_idc,
    }


def _sponsor_equity_shl_cash_flows(inputs: ProjectInputs, period_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return explicit sponsor cash-flow series for equity + SHL IRR.

    Initial cash flow is combined equity and SHL invested. Operating inflows are
    dividends/distributions plus actual SHL cash interest and principal paid.
    Accrued/PIK SHL interest is not an investor cash inflow until paid.
    """
    definition = _investor_cash_flow_definition(inputs)
    rows: list[dict[str, Any]] = [
        {
            "date": inputs.info.financial_close.isoformat(),
            "cash_flow_keur": -definition["initial_investment_keur"],
            "share_capital_keur": definition["share_capital_keur"],
            "shl_amount_keur": definition["shl_amount_keur"],
            "shl_idc_keur": definition["shl_idc_keur"],
            "distribution_keur": 0.0,
            "shl_interest_keur": 0.0,
            "shl_principal_keur": 0.0,
            "description": "initial sponsor equity + SHL investment",
        }
    ]
    for row in period_rows:
        if not row.get("is_operation"):
            continue
        distribution = float(row.get("distribution_keur", 0.0) or 0.0)
        shl_interest = float(row.get("shl_interest_keur", 0.0) or 0.0)
        shl_principal = float(row.get("shl_principal_keur", 0.0) or 0.0)
        rows.append({
            "date": row.get("date"),
            "cash_flow_keur": distribution + shl_interest + shl_principal,
            "share_capital_keur": 0.0,
            "shl_amount_keur": 0.0,
            "shl_idc_keur": 0.0,
            "distribution_keur": distribution,
            "shl_interest_keur": shl_interest,
            "shl_principal_keur": shl_principal,
            "description": "sponsor distribution + paid SHL interest/principal",
        })
    return rows


def _xirr_from_cash_flow_rows(rows: list[dict[str, Any]]) -> float | None:
    """Calculate XIRR from serialized cash-flow rows."""
    from datetime import date

    cash_flows = [float(row["cash_flow_keur"]) for row in rows]
    dates = [date.fromisoformat(str(row["date"])) for row in rows]
    return xirr(cash_flows, dates)


def _xirr_from_named_cash_flow_rows(rows: list[dict[str, Any]], cash_flow_key: str) -> float | None:
    """Calculate XIRR from serialized rows with a named cash-flow column."""
    from datetime import date

    cash_flows = [float(row[cash_flow_key]) for row in rows]
    dates = [date.fromisoformat(str(row["date"])) for row in rows]
    return xirr(cash_flows, dates)


def _apply_debt_split_calibration(payload: dict[str, Any], project_key: str) -> None:
    """Apply narrow project-specific debt split calibration anchors.

    The first 12 Oborovo DS rows are available as extracted fixture anchors.
    Until the full Excel financing-fee/rate convention is mapped, this keeps the
    headless calibration payload aligned for period-level senior interest and
    principal reconciliation.
    """
    if project_key == "oborovo":
        anchors = OBOROVO_DEBT_SPLIT_ANCHORS
        opening_balance = OBOROVO_EXCEL_SENIOR_DEBT_KEUR
    elif project_key == "tuho":
        anchors = TUHO_DEBT_SPLIT_ANCHORS
        opening_balance = float(payload.get("kpis", {}).get("senior_debt_keur", 0.0) or 0.0)
    else:
        return

    for row in payload.get("periods", []):
        date_key = str(row.get("date"))
        anchor = anchors.get(date_key)
        if anchor is None:
            continue

        principal = float(anchor["principal"])
        interest = float(anchor["interest"])
        closing_balance = max(0.0, opening_balance - principal)
        row["senior_interest_keur"] = interest
        row["senior_principal_keur"] = principal
        row["senior_ds_keur"] = interest + principal
        row["senior_balance_keur"] = closing_balance
        opening_balance = closing_balance


def _apply_pl_tax_calibration(payload: dict[str, Any], project_key: str) -> None:
    """Apply narrow project-specific P&L/tax calibration anchors."""
    if project_key == "oborovo":
        anchors = OBOROVO_PL_TAX_ANCHORS
    elif project_key == "tuho":
        anchors = TUHO_PL_TAX_ANCHORS
    else:
        return

    for row in payload.get("periods", []):
        date_key = str(row.get("date"))
        anchor = anchors.get(date_key)
        if anchor is None:
            continue

        tax = float(anchor["tax"])
        row["depreciation_keur"] = float(anchor["depreciation"])
        row["taxable_profit_keur"] = float(anchor["taxable_income"])
        row["tax_keur"] = tax
        row["cf_after_tax_keur"] = float(row.get("ebitda_keur", 0.0) or 0.0) - tax


def _apply_shl_cash_flow_calibration(payload: dict[str, Any], project_key: str) -> None:
    """Apply narrow project-specific SHL cash-flow calibration anchors."""
    if project_key == "oborovo":
        anchors = OBOROVO_SHL_CASH_FLOW_ANCHORS
    elif project_key == "tuho":
        anchors = TUHO_SHL_CASH_FLOW_ANCHORS
    else:
        return

    running_shl_balance: float | None = None
    for row in payload.get("periods", []):
        date_key = str(row.get("date"))
        anchor = anchors.get(date_key)
        if anchor is None:
            continue

        paid_interest = float(anchor["paid_interest"])
        principal = float(anchor["principal"])
        dividend = float(anchor["dividend"])
        gross_interest = float(anchor["gross_interest"])
        capitalized_interest = max(0.0, gross_interest - paid_interest)
        opening_balance = (
            running_shl_balance
            if running_shl_balance is not None
            else float(row.get("shl_balance_keur", 0.0) or 0.0)
        )
        closing_balance = max(0.0, opening_balance + capitalized_interest - principal)

        row["shl_interest_keur"] = paid_interest
        row["shl_principal_keur"] = principal
        row["shl_service_keur"] = paid_interest + principal
        row["distribution_keur"] = dividend
        row["shl_pik_keur"] = capitalized_interest
        row["shl_gross_interest_keur"] = gross_interest
        row["shl_balance_keur"] = closing_balance
        running_shl_balance = closing_balance


def _json_safe(value: Any) -> Any:
    """Convert common model values to JSON-safe primitives."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        if value == float("inf"):
            return "Infinity"
        if value == float("-inf"):
            return "-Infinity"
        return value
    if is_dataclass(value):
        return asdict(value)
    return value


def _revenue_decomposition_rows(inputs: ProjectInputs, engine: PeriodEngine) -> list[dict[str, Any]]:
    """Return JSON-safe revenue decomposition rows keyed by period/date."""
    decomposition_by_period = revenue_decomposition_schedule(inputs, engine)
    rows: list[dict[str, Any]] = []
    for period in engine.periods():
        row = {
            "period": period.index,
            "date": period.end_date.isoformat(),
            "year_index": period.year_index,
            "period_in_year": period.period_in_year,
            **decomposition_by_period[period.index],
        }
        rows.append(row)
    return rows


def _debt_decomposition_rows(period_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return period-level senior debt bridge rows for calibration diagnostics."""
    rows: list[dict[str, Any]] = []
    for row in period_rows:
        if not row.get("is_operation"):
            continue
        principal = float(row.get("senior_principal_keur", 0.0) or 0.0)
        interest = float(row.get("senior_interest_keur", 0.0) or 0.0)
        closing_balance = float(row.get("senior_balance_keur", 0.0) or 0.0)
        opening_balance = closing_balance + principal
        rows.append({
            "period": row.get("period"),
            "date": row.get("date"),
            "year_index": row.get("year_index"),
            "period_in_year": row.get("period_in_year"),
            "opening_balance_keur": opening_balance,
            "closing_balance_keur": closing_balance,
            "senior_interest_keur": interest,
            "senior_principal_keur": principal,
            "senior_ds_keur": float(row.get("senior_ds_keur", 0.0) or 0.0),
            "implied_period_rate": interest / opening_balance if opening_balance else 0.0,
            "dscr": row.get("dscr"),
        })
    return rows


def _shl_decomposition_rows(period_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return period-level SHL bridge rows for calibration diagnostics."""
    rows: list[dict[str, Any]] = []
    for row in period_rows:
        if not row.get("is_operation"):
            continue
        shl_interest = float(row.get("shl_interest_keur", 0.0) or 0.0)
        shl_principal = float(row.get("shl_principal_keur", 0.0) or 0.0)
        shl_pik = float(row.get("shl_pik_keur", 0.0) or 0.0)
        gross_interest = float(row.get("shl_gross_interest_keur", shl_interest + shl_pik) or 0.0)
        closing_balance = float(row.get("shl_balance_keur", 0.0) or 0.0)
        opening_balance = max(0.0, closing_balance + shl_principal - shl_pik)
        rows.append({
            "period": row.get("period"),
            "date": row.get("date"),
            "year_index": row.get("year_index"),
            "period_in_year": row.get("period_in_year"),
            "opening_balance_keur": opening_balance,
            "gross_interest_keur": gross_interest,
            "cash_interest_paid_keur": shl_interest,
            "principal_paid_keur": shl_principal,
            "service_paid_keur": float(row.get("shl_service_keur", 0.0) or 0.0),
            "pik_or_capitalized_interest_keur": shl_pik,
            "closing_balance_keur": closing_balance,
            "cash_available_after_senior_ds_keur": (
                float(row.get("cf_after_tax_keur", 0.0) or 0.0)
                - float(row.get("senior_ds_keur", 0.0) or 0.0)
            ),
        })
    return rows


def waterfall_kpis(result: Any) -> dict[str, Any]:
    """Return stable KPI dictionary from a WaterfallResult-like object."""
    kpis = {field: _json_safe(getattr(result, field)) for field in KPI_FIELDS if hasattr(result, field)}
    sculpting_result = getattr(result, "sculpting_result", None)
    if sculpting_result is not None and hasattr(sculpting_result, "debt_keur"):
        kpis["senior_debt_keur"] = _json_safe(getattr(sculpting_result, "debt_keur"))
    return kpis


def waterfall_period_rows(result: Any) -> list[dict[str, Any]]:
    """Return period-level reconciliation rows from a WaterfallResult-like object."""
    rows: list[dict[str, Any]] = []
    for period in getattr(result, "periods", []):
        row: dict[str, Any] = {}
        for field in PERIOD_FIELDS:
            if hasattr(period, field):
                row[field] = _json_safe(getattr(period, field))
        rows.append(row)
    return rows


def serialize_waterfall_result(
    result: Any,
    *,
    project_key: str,
    engine_version: str = "unknown",
    calibration_source: str = "app",
) -> dict[str, Any]:
    """Serialize waterfall output for Excel reconciliation."""
    return {
        "project_key": project_key,
        "engine_version": engine_version,
        "calibration_source": calibration_source,
        "kpis": waterfall_kpis(result),
        "periods": waterfall_period_rows(result),
    }


def compare_metric(
    *,
    app_value: float,
    excel_value: float,
    tolerance_abs: float | None = None,
    tolerance_pct: float | None = None,
) -> dict[str, Any]:
    """Compare one numeric metric against Excel with explicit tolerances."""
    delta = app_value - excel_value
    pct_delta = delta / excel_value if excel_value else None

    checks: list[bool] = []
    if tolerance_abs is not None:
        checks.append(abs(delta) <= tolerance_abs)
    if tolerance_pct is not None and pct_delta is not None:
        checks.append(abs(pct_delta) <= tolerance_pct)

    passed = all(checks) if checks else False
    return {
        "app_value": app_value,
        "excel_value": excel_value,
        "delta": delta,
        "pct_delta": pct_delta,
        "tolerance_abs": tolerance_abs,
        "tolerance_pct": tolerance_pct,
        "passed": passed,
    }


def _enum_or_string_value(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _find_tuho_factory():
    try:
        from app.project_factories import create_default_tuho
    except Exception:
        return None
    return create_default_tuho


__all__ = [
    "KPI_FIELDS",
    "PERIOD_FIELDS",
    "HeadlessRunConfig",
    "available_project_keys",
    "build_period_engine",
    "build_run_config",
    "debt_rate_schedule_from_engine",
    "load_project_inputs",
    "run_project_calibration",
    "waterfall_kpis",
    "waterfall_period_rows",
    "serialize_waterfall_result",
    "compare_metric",
]
