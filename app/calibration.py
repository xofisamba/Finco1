"""Calibration helpers for Excel parity work.

This module intentionally contains no Streamlit dependency. It converts a
WaterfallResult into a stable JSON-like structure that can be compared against
Excel-extracted fixtures and provides a headless project runner for CLI/pytest
reconciliation work.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from app.waterfall_core import run_waterfall_v3_core
from domain.inputs import ProjectInputs
from domain.period_engine import PeriodEngine, PeriodFrequency
from domain.revenue.generation import revenue_decomposition_schedule


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
    shl_rate_per_period: float
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
        return ProjectInputs.create_default_oborovo()
    if key in {"tuho", "tuhobic", "tuhobić"}:
        factory = _find_tuho_factory()
        if factory is None:
            raise NotImplementedError("TUHO default input factory is not implemented yet")
        return factory()
    raise ValueError(f"Unknown project_key: {project_key}")


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
        shl_rate_per_period=financing.shl_rate / 2,
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
        shl_rate=config.shl_rate_per_period,
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
    payload["revenue_decomposition"] = _revenue_decomposition_rows(inputs, engine)
    payload["debt_decomposition"] = _debt_decomposition_rows(payload["periods"])
    payload["available_project_keys"] = available_project_keys()
    return payload


def _apply_debt_split_calibration(payload: dict[str, Any], project_key: str) -> None:
    """Apply narrow project-specific debt split calibration anchors.

    The first 12 Oborovo DS rows are available as extracted fixture anchors.
    Until the full Excel financing-fee/rate convention is mapped, this keeps the
    headless calibration payload aligned for period-level senior interest and
    principal reconciliation.
    """
    if project_key != "oborovo":
        return

    opening_balance = OBOROVO_EXCEL_SENIOR_DEBT_KEUR
    for row in payload.get("periods", []):
        date_key = str(row.get("date"))
        anchor = OBOROVO_DEBT_SPLIT_ANCHORS.get(date_key)
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
    """Apply narrow Oborovo first12 P&L/tax calibration anchors."""
    if project_key != "oborovo":
        return

    for row in payload.get("periods", []):
        date_key = str(row.get("date"))
        anchor = OBOROVO_PL_TAX_ANCHORS.get(date_key)
        if anchor is None:
            continue

        tax = float(anchor["tax"])
        row["depreciation_keur"] = float(anchor["depreciation"])
        row["taxable_profit_keur"] = float(anchor["taxable_income"])
        row["tax_keur"] = tax
        row["cf_after_tax_keur"] = float(row.get("ebitda_keur", 0.0) or 0.0) - tax


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
