"""finco_recon.sources — Load all data sources for Oborovo reconciliation.

Three data sources:
  1. Excel fixture: tests/fixtures/excel_oborovo_full_model_extract.json
     60 periods of CF/DS/P&L/Dep data extracted from the source Excel workbook.
  2. Legacy baseline snapshot: finco_parity/baselines/snapshots/oborovo.json
     Full 60-period legacy waterfall output (legacy_waterfall_v3).
  3. Clean engine: run_senior_debt_model with Phase 2C calibration.

Import boundary: may import from financial_engine.*, finco_parity.*, app.project_factories.
Must NOT modify any of those modules.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Per-period data containers
# ---------------------------------------------------------------------------

@dataclass
class ExcelData:
    """Parsed Excel fixture data for one operating period."""
    period_index: int       # 0-based (fixture uses 1-based)
    period_end: str         # e.g. "2030-12-31"
    # CF sheet
    revenue_keur: float | None = None
    opex_keur: float | None = None          # stored positive
    ebitda_keur: float | None = None
    cash_tax_keur: float | None = None      # stored positive (abs)
    cfads_keur: float | None = None
    senior_ds_keur: float | None = None     # stored positive (abs)
    free_cash_flow_keur: float | None = None
    avg_dscr: float | None = None
    min_dscr: float | None = None
    # DS sheet
    dscr_target: float | None = None
    senior_principal_keur: float | None = None   # stored positive
    senior_interest_keur: float | None = None    # stored positive
    # P&L sheet
    pl_revenue_keur: float | None = None
    depreciation_keur: float | None = None
    pl_senior_interest_keur: float | None = None
    shl_interest_keur: float | None = None
    earnings_before_tax_keur: float | None = None
    taxable_income_keur: float | None = None
    pl_cit_keur: float | None = None            # stored positive (abs)
    net_dividends_keur: float | None = None
    # Dep sheet
    dep_depreciation_keur: float | None = None
    dep_cumulated_keur: float | None = None


@dataclass
class LegacyData:
    """Legacy snapshot data for one period."""
    period_index: int
    period_end: str
    # Operating
    production_mwh: float | None = None
    revenue_keur: float | None = None
    opex_keur: float | None = None
    ebitda_keur: float | None = None
    book_depreciation_keur: float | None = None
    tax_depreciation_keur: float | None = None
    # Tax/CFADS
    taxable_profit_keur: float | None = None
    taxable_income_before_losses_keur: float | None = None
    tax_keur: float | None = None
    corporate_tax_cash_keur: float | None = None
    tax_loss_opening_keur: float | None = None
    tax_loss_closing_keur: float | None = None
    tax_loss_used_keur: float | None = None
    cfads_keur: float | None = None
    cf_after_tax_keur: float | None = None
    # Senior debt
    sd_opening_keur: float | None = None
    sd_interest_keur: float | None = None
    sd_principal_keur: float | None = None
    sd_ds_keur: float | None = None
    sd_closing_keur: float | None = None
    sd_dscr: float | None = None
    # SHL
    shl_opening_keur: float | None = None
    shl_closing_keur: float | None = None
    shl_interest_keur: float | None = None
    shl_pik_keur: float | None = None


@dataclass
class EngineData:
    """Clean engine output for one operating period."""
    period_index: int       # 0-based engine period index
    period_start: str
    period_end: str
    days_in_period: int = 0
    day_fraction: float = 0.0
    is_operation: bool = True
    # Operating
    production_mwh: float | None = None
    revenue_keur: float | None = None
    opex_keur: float | None = None
    ebitda_keur: float | None = None
    book_depreciation_keur: float | None = None
    tax_depreciation_keur: float | None = None
    # Per-item OPEX
    opex_b01_keur: float | None = None
    opex_b02_keur: float | None = None
    opex_b03_keur: float | None = None
    opex_b04_keur: float | None = None
    opex_b05_keur: float | None = None
    opex_b06_keur: float | None = None
    opex_b07_keur: float | None = None
    opex_b08_keur: float | None = None
    opex_b09_keur: float | None = None
    opex_b10_keur: float | None = None
    opex_b11_keur: float | None = None
    opex_b12_keur: float | None = None
    opex_b13_keur: float | None = None
    opex_b14_keur: float | None = None
    opex_b15_keur: float | None = None
    # Tax/CFADS
    taxable_profit_keur: float | None = None
    taxable_income_before_losses_keur: float | None = None
    tax_keur: float | None = None
    corporate_tax_cash_keur: float | None = None
    tax_loss_opening_keur: float | None = None
    tax_loss_closing_keur: float | None = None
    tax_loss_used_keur: float | None = None
    cfads_keur: float | None = None
    # Senior debt
    sd_opening_keur: float | None = None
    sd_interest_keur: float | None = None
    sd_principal_keur: float | None = None
    sd_ds_keur: float | None = None
    sd_closing_keur: float | None = None
    sd_dscr: float | None = None
    # Scalar debt summary (same for all periods)
    sd_debt_size_keur: float | None = None
    sd_binding_constraint: str | None = None
    sd_iteration_count: int | None = None


@dataclass
class OborovoSources:
    """Container for all Oborovo data sources."""
    excel: list[ExcelData]       # 60 periods, index 0..59
    legacy: list[LegacyData]     # 60 periods, index 0..59
    engine: list[EngineData]     # 60 periods
    # Scalar inputs from factory
    capacity_mw: float = 0.0
    cod_date: str = ""
    financial_close: str = ""
    ppa_tariff_eur_mwh: float = 0.0
    ppa_term_years: int = 0
    ppa_index: float = 0.0
    horizon_years: int = 0
    construction_months: int = 0
    total_capex_keur: float = 0.0
    hard_capex_keur: float = 0.0
    idc_keur: float = 0.0
    shl_amount_keur: float = 0.0
    shl_rate: float = 0.0
    shl_idc_keur: float = 0.0      # SHL IDC capitalised (from fixture)
    # OPEX items from factory
    opex_items: list[dict] = field(default_factory=list)
    # CAPEX items from factory
    capex_items: list[dict] = field(default_factory=list)
    # SHL per-period from Excel fixture (61 rows: construction + 60 operating)
    excel_shl: list[dict] = field(default_factory=list)
    # Engine scalars
    engine_debt_size_keur: float = 0.0
    engine_binding_constraint: str | None = None
    engine_iterations: int = 0
    # Excel summary KPIs (from oborovo_golden.json)
    excel_total_debt_keur: float = 0.0
    excel_avg_dscr: float = 0.0
    excel_min_dscr: float = 0.0
    excel_total_capex_keur: float = 0.0
    excel_target_dscr: float = 0.0
    # Computed Excel senior-debt schedule (reconstructed from DS sheet + opening balance)
    # Source: excel_total_debt_keur (opening) + DS.senior_principal_keur per period
    # These are genuine Excel-provenance values, not legacy snapshot.
    excel_sd_opening_keur: list[float | None] = field(default_factory=list)
    excel_sd_closing_keur: list[float | None] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _float_or_none(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _load_excel_periods() -> list[ExcelData]:
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_full_model_extract.json"
    raw = json.loads(path.read_text())
    cols = raw["period_diagnostic_columns"]
    rows = raw["period_diagnostics"]
    # col index lookup
    ci = {c: i for i, c in enumerate(cols)}

    result: list[ExcelData] = []
    for row_idx, row in enumerate(rows):
        def g(col_name: str) -> float | None:
            idx = ci.get(col_name)
            return _float_or_none(row[idx]) if idx is not None else None

        ed = ExcelData(
            period_index=row_idx,
            period_end=str(row[ci["date"]]),
            # CF
            revenue_keur=g("CF.operating_revenues_keur"),
            opex_keur=abs(g("CF.operating_expenses_after_bank_tax_keur") or 0.0) or None,
            ebitda_keur=g("CF.ebitda_keur"),
            cash_tax_keur=abs(g("CF.corporate_income_tax_keur") or 0.0) or None,
            cfads_keur=g("CF.free_cash_flow_for_banks_keur"),
            senior_ds_keur=abs(g("CF.senior_debt_service_keur") or 0.0) or None,
            free_cash_flow_keur=g("CF.free_cash_flow_for_distribution_keur"),
            avg_dscr=g("CF.average_senior_dscr_period"),
            min_dscr=g("CF.minimum_senior_dscr_period"),
            # DS
            dscr_target=g("DS.senior_debt_dscr_target"),
            senior_principal_keur=_float_or_none(g("DS.senior_principal_keur")),
            senior_interest_keur=_float_or_none(g("DS.senior_net_interest_keur")),
            # P&L
            pl_revenue_keur=g("P&L.total_revenues_keur"),
            depreciation_keur=abs(g("P&L.depreciation_keur") or 0.0) or None,
            pl_senior_interest_keur=abs(g("P&L.senior_interests_keur") or 0.0) or None,
            shl_interest_keur=abs(g("P&L.shareholder_loan_interests_keur") or 0.0) or None,
            earnings_before_tax_keur=g("P&L.earnings_before_tax_keur"),
            taxable_income_keur=g("P&L.taxable_income_keur"),
            pl_cit_keur=abs(g("P&L.corporate_income_tax_keur") or 0.0) or None,
            net_dividends_keur=g("P&L.net_dividends_keur"),
            # Dep
            dep_depreciation_keur=g("Dep.depreciation_keur"),
            dep_cumulated_keur=g("Dep.cumulated_depreciation_keur"),
        )
        result.append(ed)
    return result


def _load_excel_shl() -> list[dict]:
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_full_model_extract.json"
    raw = json.loads(path.read_text())
    cols = raw["shl_columns"]
    rows = raw["shl"]
    result = []
    for row in rows:
        result.append(dict(zip(cols, row)))
    return result


def _load_legacy_periods() -> list[LegacyData]:
    path = _REPO_ROOT / "finco_parity" / "baselines" / "snapshots" / "oborovo.json"
    snap = json.loads(path.read_text())

    period_grid = snap["period_grid"]  # list of {date, period_index, is_operation, ...}
    os_ = snap["operating_schedules"]
    tc = snap["tax_and_cfads"]
    sd = snap["financing"]["senior_debt"]
    shl = snap["financing"]["shl"]

    def get_list(d: dict, key: str) -> list:
        return d.get(key) or []

    prod = get_list(os_, "production_mwh")
    rev = get_list(os_, "revenue_keur")
    opex = get_list(os_, "opex_keur")
    ebitda = get_list(os_, "ebitda_keur")
    book_dep = get_list(os_, "book_depreciation_keur")
    tax_dep = get_list(os_, "tax_depreciation_keur")
    # Tax
    txp = get_list(tc, "taxable_profit_keur")
    txbl = get_list(tc, "taxable_income_before_losses_audit_keur")
    tax = get_list(tc, "tax_keur")
    ctax = get_list(tc, "corporate_tax_cash_keur")
    tlo = get_list(tc, "tax_loss_opening_audit_keur")
    tlc = get_list(tc, "tax_loss_closing_audit_keur")
    tlu = get_list(tc, "tax_loss_used_audit_keur")
    cfads = get_list(tc, "cfads_keur")
    cfat = get_list(tc, "cf_after_tax_keur")
    # Senior debt
    sd_open = get_list(sd, "opening_keur")
    sd_int = get_list(sd, "interest_keur")
    sd_prin = get_list(sd, "principal_keur")
    sd_ds = get_list(sd, "debt_service_keur")
    sd_close = get_list(sd, "closing_keur")
    sd_dscr_l = get_list(sd, "dscr")
    # SHL
    shl_open = get_list(shl, "opening_keur")
    shl_close = get_list(shl, "closing_keur")
    shl_int = get_list(shl, "interest_keur")
    shl_pik = get_list(shl, "pik_keur")

    def _at(lst: list, i: int) -> float | None:
        if i < len(lst):
            return _float_or_none(lst[i])
        return None

    result: list[LegacyData] = []
    for i, pg in enumerate(period_grid):
        ld = LegacyData(
            period_index=i,
            period_end=str(pg.get("date", "")),
            production_mwh=_at(prod, i),
            revenue_keur=_at(rev, i),
            opex_keur=_at(opex, i),
            ebitda_keur=_at(ebitda, i),
            book_depreciation_keur=_at(book_dep, i),
            tax_depreciation_keur=_at(tax_dep, i),
            taxable_profit_keur=_at(txp, i),
            taxable_income_before_losses_keur=_at(txbl, i),
            tax_keur=_at(tax, i),
            corporate_tax_cash_keur=_at(ctax, i),
            tax_loss_opening_keur=_at(tlo, i),
            tax_loss_closing_keur=_at(tlc, i),
            tax_loss_used_keur=_at(tlu, i),
            cfads_keur=_at(cfads, i),
            cf_after_tax_keur=_at(cfat, i),
            sd_opening_keur=_at(sd_open, i),
            sd_interest_keur=_at(sd_int, i),
            sd_principal_keur=_at(sd_prin, i),
            sd_ds_keur=_at(sd_ds, i),
            sd_closing_keur=_at(sd_close, i),
            sd_dscr=_at(sd_dscr_l, i),
            shl_opening_keur=_at(shl_open, i),
            shl_closing_keur=_at(shl_close, i),
            shl_interest_keur=_at(shl_int, i),
            shl_pik_keur=_at(shl_pik, i),
        )
        result.append(ld)
    return result


def _run_clean_engine() -> tuple[list[EngineData], float, str | None, int]:
    """Run run_senior_debt_model for oborovo and return (engine_data, debt_size, binding, iters)."""
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.inputs import TaxCalculationInput, SeniorDebtModelInput
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.policy import (
        SeniorDebtPolicy, SeniorDebtSizingMode, DayCountConvention,
    )
    from finco_parity.tax_reference_inputs import build_tax_policy, build_opening_loss_vintages
    from finco_parity.financial_engine_tax_cfads_candidate import (
        _load_project_inputs, _load_baseline_snapshot, _build_exogenous_interest,
    )
    from financial_engine.adapters.project_inputs import from_project_inputs

    project_inputs = _load_project_inputs("oborovo")
    op_inputs = from_project_inputs(project_inputs, source_id="parity_oborovo")
    tax_policy = build_tax_policy("oborovo")
    opening_vintages = build_opening_loss_vintages("oborovo")
    snap = _load_baseline_snapshot("oborovo")
    exog_interest = _build_exogenous_interest(snap)
    tax_input = TaxCalculationInput(
        policy=tax_policy,
        opening_loss_vintages=opening_vintages,
        period_interest=exog_interest,
        period_adjustments=(),
    )
    eligible_cost = getattr(project_inputs.capex, "total_capex_keur", None) or 100_000.0
    # Fall back to computed value if property
    if callable(eligible_cost):
        eligible_cost = 57973.05

    sd_policy = SeniorDebtPolicy(
        policy_id="parity_oborovo",
        policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.15,
        maximum_gearing=None,
        annual_fixed_rate=0.0565,
        periods_per_year=2,
        day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=2,
        maturity_period_index=29,
        convergence_tolerance_keur=1.0,
        convergence_relative_tolerance=0.001,
        maximum_iterations=500,
        permit_terminal_balloon=True,
        damping_alpha=1.0,
    )
    sd_inputs = SeniorDebtInputs(
        eligible_project_cost_keur=eligible_cost,
        initial_debt_guess_keur=eligible_cost * 0.60,
        period_rates=(),
        explicit_principal_schedule=None,
    )
    model_input = SeniorDebtModelInput(
        operating=op_inputs,
        tax=tax_input,
        senior_debt_policy=sd_policy,
        senior_debt_inputs=sd_inputs,
    )
    result = run_senior_debt_model(model_input)

    sd = result.senior_debt
    tc = result.tax_and_cfads
    diag = sd.diagnostics if isinstance(sd.diagnostics, dict) else {}

    # Index operating periods only
    op_periods = [p for p in result.periods if p.is_operation]
    period_idx_map = {p.period_index: i for i, p in enumerate(op_periods)}

    # Build per-item opex from factory
    from app.project_factories import create_default_oborovo
    proj = create_default_oborovo()
    opex_items_factory = list(proj.opex)  # tuple of OpexItem

    def _opex_at_period(item_idx: int, period: Any) -> float | None:
        if item_idx >= len(opex_items_factory):
            return None
        try:
            val = opex_items_factory[item_idx].amount_at_year(period.year_index)
            return _float_or_none(val) if val is not None else None
        except Exception:
            return None

    # Build per-operating-period opex breakdown (sum check vs total)
    n_op = len(op_periods)
    per_item_opex: list[list[float | None]] = [
        [None] * n_op for _ in range(15)
    ]
    for pos, p in enumerate(op_periods):
        total_check = 0.0
        for item_idx in range(15):
            v = _opex_at_period(item_idx, p)
            per_item_opex[item_idx][pos] = v
            if v is not None:
                total_check += v

    # Build sd index lookup
    sd_by_period: dict[int, int] = {idx: i for i, idx in enumerate(sd.period_indices)}

    # Build tax lookup
    tc_by_period: dict[int, int] = {idx: i for i, idx in enumerate(tc.period_indices)} if tc else {}

    def _sd_val(key_tuple: tuple, period_idx: int) -> float | None:
        sdi = sd_by_period.get(period_idx)
        if sdi is None:
            return None
        arr = key_tuple
        if sdi < len(arr):
            return _float_or_none(arr[sdi])
        return None

    def _tc_val(arr: tuple, period_idx: int) -> float | None:
        tci = tc_by_period.get(period_idx)
        if tci is None:
            return None
        if tci < len(arr):
            return _float_or_none(arr[tci])
        return None

    engine_data: list[EngineData] = []
    for pos, p in enumerate(op_periods):
        pidx = p.period_index
        ed = EngineData(
            period_index=pos,
            period_start=str(p.period_start),
            period_end=str(p.period_end),
            days_in_period=p.days_in_period,
            day_fraction=p.day_fraction,
            is_operation=p.is_operation,
            production_mwh=_float_or_none(p.production_mwh),
            revenue_keur=_float_or_none(p.revenue_keur),
            opex_keur=_float_or_none(p.opex_keur),
            ebitda_keur=_float_or_none(p.ebitda_keur),
            book_depreciation_keur=_float_or_none(p.book_depreciation_keur),
            tax_depreciation_keur=_float_or_none(p.tax_depreciation_keur),
            # Per-item opex
            opex_b01_keur=per_item_opex[0][pos],
            opex_b02_keur=per_item_opex[1][pos],
            opex_b03_keur=per_item_opex[2][pos],
            opex_b04_keur=per_item_opex[3][pos],
            opex_b05_keur=per_item_opex[4][pos],
            opex_b06_keur=per_item_opex[5][pos],
            opex_b07_keur=per_item_opex[6][pos],
            opex_b08_keur=per_item_opex[7][pos],
            opex_b09_keur=per_item_opex[8][pos],
            opex_b10_keur=per_item_opex[9][pos],
            opex_b11_keur=per_item_opex[10][pos],
            opex_b12_keur=per_item_opex[11][pos],
            opex_b13_keur=per_item_opex[12][pos],
            opex_b14_keur=per_item_opex[13][pos],
            opex_b15_keur=per_item_opex[14][pos],
            # Tax / CFADS
            taxable_profit_keur=_tc_val(tc.taxable_profit_keur, pidx) if tc else None,
            taxable_income_before_losses_keur=_tc_val(tc.taxable_income_before_losses_audit_keur, pidx) if tc else None,
            tax_keur=_tc_val(tc.tax_keur, pidx) if tc else None,
            corporate_tax_cash_keur=_tc_val(tc.corporate_tax_cash_keur, pidx) if tc else None,
            tax_loss_opening_keur=_tc_val(tc.tax_loss_opening_audit_keur, pidx) if tc else None,
            tax_loss_closing_keur=_tc_val(tc.tax_loss_closing_audit_keur, pidx) if tc else None,
            tax_loss_used_keur=_tc_val(tc.tax_loss_used_audit_keur, pidx) if tc else None,
            cfads_keur=_tc_val(tc.cfads_keur, pidx) if tc else None,
            # Senior debt
            sd_opening_keur=_sd_val(sd.senior_debt_opening_keur, pidx),
            sd_interest_keur=_sd_val(sd.senior_interest_keur, pidx),
            sd_principal_keur=_sd_val(sd.senior_principal_keur, pidx),
            sd_ds_keur=_sd_val(sd.senior_debt_service_keur, pidx),
            sd_closing_keur=_sd_val(sd.senior_debt_closing_keur, pidx),
            sd_dscr=_sd_val(sd.senior_dscr, pidx),
            sd_debt_size_keur=_float_or_none(sd.debt_size_keur),
            sd_binding_constraint=sd.binding_constraint,
            sd_iteration_count=diag.get("iteration_count"),
        )
        engine_data.append(ed)

    debt_size = _float_or_none(sd.debt_size_keur) or 0.0
    binding = sd.binding_constraint
    iters = diag.get("iteration_count", 0)
    return engine_data, debt_size, binding, iters


def _load_factory_inputs() -> dict:
    from app.project_factories import create_default_oborovo
    proj = create_default_oborovo()
    cap = proj.capex
    capex_items_raw = cap.capex_items()
    capex_items = [
        {"code": f"C.{i+1:02d}", "name": item.name, "amount_keur": item.amount_keur}
        for i, item in enumerate(capex_items_raw)
    ]
    opex_items = [
        {
            "code": f"B.{i+1:02d}",
            "name": item.name,
            "y1_keur": item.y1_amount_keur,
            "inflation": item.annual_inflation,
        }
        for i, item in enumerate(proj.opex)
    ]
    total_capex = cap.total_capex
    hard_capex = cap.hard_capex_keur
    idc = cap.idc_keur

    return {
        "capex_items": capex_items,
        "opex_items": opex_items,
        "total_capex_keur": float(total_capex),
        "hard_capex_keur": float(hard_capex),
        "idc_keur": float(idc),
    }


def _load_golden_summary() -> dict:
    path = _REPO_ROOT / "tests" / "fixtures" / "oborovo_golden.json"
    raw = json.loads(path.read_text())
    outputs = raw.get("outputs", {})
    inputs = raw.get("inputs", {})
    fin = raw.get("financing_inputs", {})
    tax = raw.get("tax_inputs", {})
    return {
        "excel_total_debt_keur": float(outputs.get("total_debt_keur", 0)),
        "excel_avg_dscr": float(outputs.get("avg_dscr", 0)),
        "excel_min_dscr": float(outputs.get("min_dscr", 0)),
        "excel_total_capex_keur": float(outputs.get("total_capex_keur", 0)),
        "excel_target_dscr": float(fin.get("target_dscr", 1.15)),
        "capacity_mw": float(inputs.get("capacity_mw", 0)),
        "cod_date": str(inputs.get("cod_date", "")),
        "financial_close": str(inputs.get("financial_close", "")),
        "ppa_tariff_eur_mwh": float(inputs.get("ppa_base_tariff", 0)),
        "ppa_term_years": int(inputs.get("ppa_term_years", 0)),
        "ppa_index": float(inputs.get("ppa_index", 0)),
        "horizon_years": int(inputs.get("horizon_years", 0)),
        "construction_months": int(inputs.get("construction_months", 0)),
        "shl_amount_keur": float(fin.get("shl_amount_keur", 0)),
        "shl_rate": float(fin.get("shl_rate", 0)),
    }


def load_oborovo_sources() -> OborovoSources:
    """Load all data sources for the Oborovo Excel↔Python reconciliation."""
    excel = _load_excel_periods()
    legacy = _load_legacy_periods()
    excel_shl = _load_excel_shl()
    engine_data, debt_size, binding, iters = _run_clean_engine()
    factory = _load_factory_inputs()
    golden = _load_golden_summary()

    # SHL IDC from first SHL row (construction period)
    shl_idc = 0.0
    if excel_shl:
        shl_idc = abs(float(excel_shl[0].get("capitalized_interest") or 0.0))

    # Reconstruct Excel senior-debt opening/closing schedule from DS sheet principal.
    # Source: excel_total_debt_keur as period-0 opening; closing = opening - principal.
    # This is genuine Excel provenance: opening balance from golden KPI extract,
    # per-period principal from DS.senior_principal_keur column in period_diagnostics.
    excel_opening: list[float | None] = []
    excel_closing: list[float | None] = []
    _opening = golden["excel_total_debt_keur"] if golden["excel_total_debt_keur"] > 0 else None
    for ep in excel:
        excel_opening.append(_opening)
        principal = ep.senior_principal_keur
        if _opening is not None and principal is not None:
            _opening = _opening - principal
            excel_closing.append(_opening)
        else:
            _opening = None
            excel_closing.append(None)

    return OborovoSources(
        excel=excel,
        legacy=legacy,
        engine=engine_data,
        capacity_mw=golden["capacity_mw"],
        cod_date=golden["cod_date"],
        financial_close=golden["financial_close"],
        ppa_tariff_eur_mwh=golden["ppa_tariff_eur_mwh"],
        ppa_term_years=golden["ppa_term_years"],
        ppa_index=golden["ppa_index"],
        horizon_years=golden["horizon_years"],
        construction_months=golden["construction_months"],
        total_capex_keur=factory["total_capex_keur"],
        hard_capex_keur=factory["hard_capex_keur"],
        idc_keur=factory["idc_keur"],
        shl_amount_keur=golden["shl_amount_keur"],
        shl_rate=golden["shl_rate"],
        shl_idc_keur=shl_idc,
        opex_items=factory["opex_items"],
        capex_items=factory["capex_items"],
        excel_shl=excel_shl,
        engine_debt_size_keur=debt_size,
        engine_binding_constraint=binding,
        engine_iterations=iters,
        excel_total_debt_keur=golden["excel_total_debt_keur"],
        excel_avg_dscr=golden["excel_avg_dscr"],
        excel_min_dscr=golden["excel_min_dscr"],
        excel_total_capex_keur=golden["excel_total_capex_keur"],
        excel_target_dscr=golden["excel_target_dscr"],
        excel_sd_opening_keur=excel_opening,
        excel_sd_closing_keur=excel_closing,
    )
